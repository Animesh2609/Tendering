"""Popularity-calibrated re-ranking inspired by calibrated popularity work."""

import numpy as np
import torch
import torch.nn.functional as F


GROUPS = ("LowPop", "MedPop", "HighPop")


def _tiers(global_counts):
    counts = np.asarray(global_counts, dtype=np.float64).reshape(-1)
    nonzero = counts[counts > 0]
    if nonzero.size == 0:
        return np.zeros(counts.size, dtype=np.int64)
    low, high = np.quantile(nonzero, [0.2, 0.8])
    # 0=tail, 1=mid, 2=head.
    return np.where(counts > high, 2, np.where(counts > low, 1, 0))


def _profile_groups(train_df, num_users, global_counts):
    counts = np.asarray(global_counts, dtype=np.float64)
    log_pop = np.log1p(counts)
    user_means = np.zeros(num_users, dtype=np.float64)
    user_ids = train_df["user"].unique()
    active_mask = np.zeros(num_users, dtype=bool)
    active_mask[user_ids.astype(np.int64)] = True
    for user, history in train_df.groupby("user")["item"]:
        ids = history.to_numpy(dtype=np.int64)
        user_means[int(user)] = float(log_pop[ids].mean()) if ids.size else 0.0
    active = user_means[active_mask]
    if active.size:
        low, high = np.quantile(active, [0.2, 0.8])
    else:
        low = high = 0.0
    return user_means, [float(low), float(high)]


def _group_name(user, user_means, thresholds):
    value = user_means[int(user)]
    if value <= thresholds[0]:
        return "LowPop"
    if value >= thresholds[1]:
        return "HighPop"
    return "MedPop"


def _js_divergence(left, right):
    left = np.asarray(left, dtype=np.float64)
    right = np.asarray(right, dtype=np.float64)
    left = left / max(left.sum(), 1e-12)
    right = right / max(right.sum(), 1e-12)
    middle = 0.5 * (left + right)

    def kl(p, q):
        mask = p > 0
        return float(np.sum(p[mask] * np.log2(p[mask] / q[mask])))

    divergence = 0.5 * kl(left, middle) + 0.5 * kl(right, middle)
    return float(np.clip(divergence, 0.0, 1.0))


def _js_divergence_rows(target, rows):
    target = np.asarray(target, dtype=np.float64)
    target = target / max(target.sum(), 1e-12)
    rows = np.asarray(rows, dtype=np.float64)
    rows = rows / np.maximum(rows.sum(axis=1, keepdims=True), 1e-12)
    middle = 0.5 * (rows + target[None, :])
    left = np.where(target[None, :] > 0, target[None, :] * np.log2(
        np.maximum(target[None, :], 1e-300) / np.maximum(middle, 1e-300)
    ), 0.0).sum(axis=1)
    right = np.where(rows > 0, rows * np.log2(
        np.maximum(rows, 1e-300) / np.maximum(middle, 1e-300)
    ), 0.0).sum(axis=1)
    return np.clip(0.5 * (left + right), 0.0, 1.0)


def balanced_candidates(scores, items, tiers, candidate_pool, minimum_candidates):
    all_scores = scores.cpu().numpy().astype(np.float64)
    all_items = items.cpu().numpy().astype(np.int64)
    finite = np.isfinite(all_scores)
    all_items, all_scores = all_items[finite], all_scores[finite]
    if not all_scores.size:
        return None

    score_order = np.argsort(-all_scores, kind="stable")
    take = min(
        max(int(candidate_pool), int(minimum_candidates), 1),
        len(score_order),
    )
    protected_count = min(max(int(minimum_candidates), 1), take)
    original_top_positions = torch.topk(
        scores,
        protected_count,
    ).indices.cpu().numpy().astype(np.int64)
    original_top_items = items[torch.as_tensor(
        original_top_positions,
        dtype=torch.long,
        device=items.device,
    )].cpu().numpy().astype(np.int64)
    item_positions = {int(item): index for index, item in enumerate(all_items)}
    selected_indices = [
        item_positions[int(item)] for item in original_top_items
        if int(item) in item_positions
    ]
    selected_set = set(selected_indices)
    tier_queues = {
        tier: [
            int(index) for index in score_order
            if tiers[all_items[index]] == tier
        ]
        for tier in range(3)
    }
    queue_positions = {tier: 0 for tier in range(3)}

    while len(selected_indices) < take:
        available_by_tier = {}
        for tier, queue in tier_queues.items():
            position = queue_positions[tier]
            while position < len(queue) and queue[position] in selected_set:
                position += 1
            queue_positions[tier] = position
            if position < len(queue):
                available_by_tier[tier] = queue[position]
        if not available_by_tier:
            break

        selected_tier_counts = np.bincount(
            tiers[all_items[selected_indices]], minlength=3
        )
        chosen_tier = min(
            available_by_tier,
            key=lambda tier: (
                selected_tier_counts[tier],
                -all_scores[available_by_tier[tier]],
                tier,
            ),
        )
        chosen_index = available_by_tier[chosen_tier]
        selected_indices.append(chosen_index)
        selected_set.add(chosen_index)

    selected_indices = sorted(
        selected_indices,
        key=lambda index: -all_scores[index],
    )
    item_ids = all_items[selected_indices]
    rel = all_scores[selected_indices]
    if rel.size:
        span = float(rel.max() - rel.min())
        rel = (rel - rel.min()) / span if span > 1e-12 else np.ones_like(rel)
    return item_ids, rel, original_top_items


def _make_candidate_cache(
    model, norm_adj, train_df, eval_df, num_users, num_items,
    item_pop, user_epp, global_counts, candidate_pool, device,
    group_thresholds=None,
    matching_scores_by_user=None,
    group_assignments=None,
    minimum_candidates=1,
):
    model.eval()
    seen = train_df.groupby("user")["item"].apply(set).to_dict()
    histories = {
        int(user): rows.to_numpy(dtype=np.int64)
        for user, rows in train_df.groupby("user")["item"]
    }
    truth = eval_df.groupby("user")["item"].apply(set).to_dict()
    counts = np.asarray(global_counts, dtype=np.float64).reshape(-1)
    tiers = _tiers(counts)
    popularity = counts
    user_means, computed_thresholds = _profile_groups(train_df, num_users, counts)
    thresholds = (
        computed_thresholds if group_thresholds is None else group_thresholds
    )
    item_pop = torch.as_tensor(item_pop, dtype=torch.float32, device=device)
    user_epp = torch.as_tensor(user_epp, dtype=torch.float32, device=device)
    items = torch.arange(num_items, dtype=torch.long, device=device)
    cache = {}

    with torch.no_grad():
        user_embeddings, item_embeddings = model.lightgcn.propagate(norm_adj)
        for user, actual_items in truth.items():
            user = int(user)
            if not actual_items or user >= num_users:
                continue
            previous = seen.get(user, set())
            if matching_scores_by_user is None:
                items = torch.arange(num_items, dtype=torch.long, device=device)
                matching = (user_embeddings[user].unsqueeze(0) * item_embeddings).sum(dim=-1)
            else:
                user_score_map = matching_scores_by_user.get(user, {})
                candidate_ids = [
                    int(item) for item in user_score_map
                    if int(item) not in previous
                ]
                if not candidate_ids:
                    continue
                items = torch.tensor(candidate_ids, dtype=torch.long, device=device)
                matching = torch.tensor(
                    [user_score_map[item] for item in candidate_ids],
                    dtype=torch.float32,
                    device=device,
                )
            p = item_pop[items].clamp(0.0, 1.0)
            s = user_epp[user].expand_as(p).clamp(0.0, 1.0)
            item_mapping = model.item_mlp(item_embeddings[items]).squeeze(-1)
            conformity = torch.exp(-model.alpha * torch.abs(s - p)) * p * item_mapping
            scores = torch.tanh(model.q[items] + conformity) * F.softplus(matching)
            if previous and matching_scores_by_user is None:
                prev = torch.tensor(list(previous), dtype=torch.long, device=device)
                scores[prev] = -torch.inf
            valid = num_items - len(previous)
            available_count = scores.numel() if matching_scores_by_user is not None else valid
            if available_count <= 0:
                continue
            candidate_result = balanced_candidates(scores, items, tiers, candidate_pool, minimum_candidates)
            if candidate_result is None:
                continue
            item_ids, rel, original_top_items = candidate_result
            history = histories.get(user, np.empty(0, dtype=np.int64))
            target = np.bincount(tiers[history], minlength=3).astype(np.float64)
            if target.sum() == 0:
                target = np.array([1.0, 0.0, 0.0])
            assigned_group = (
                group_assignments.get(user, group_assignments.get(str(user)))
                if group_assignments is not None else None
            )
            cache[user] = {
                "truth": set(int(x) for x in actual_items),
                "items": item_ids,
                "relevance": rel,
                "tier": tiers[item_ids],
                "target": target,
                "profile_items": history,
                "group": assigned_group or _group_name(user, user_means, thresholds),
                "candidate_tier_counts": np.bincount(tiers[item_ids], minlength=3),
                "target_tier_count": int(np.count_nonzero(target)),
                "original_top_items": original_top_items,
            }

    computed_groups = {
        user: _group_name(user, user_means, thresholds)
        for user in range(num_users)
    }
    return cache, thresholds, popularity, computed_groups


def _rerank(entry, k, weight):
    if weight == 0 and "original_top_items" in entry:
        return [int(item) for item in entry["original_top_items"][:k]]
    items = entry["items"]
    relevance = entry["relevance"]
    item_tiers = entry["tier"]
    target = entry["target"]
    selected = []
    remaining = np.ones(len(items), dtype=bool)
    selected_relevance = 0.0
    selected_tiers = np.zeros(3, dtype=np.float64)
    tier_one_hot = np.eye(3, dtype=np.float64)[item_tiers]

    for _ in range(min(k, len(items))):
        available = np.flatnonzero(remaining)
        if available.size == 0:
            break
        trial_counts = selected_tiers[None, :] + tier_one_hot[available]
        divergences = _js_divergence_rows(target, trial_counts)
        mean_relevance = (selected_relevance + relevance[available]) / (len(selected) + 1)
        objectives = (1.0 - weight) * mean_relevance - weight * divergences
        best_idx = int(available[int(np.argmax(objectives))])
        selected.append(best_idx)
        remaining[best_idx] = False
        selected_relevance += float(relevance[best_idx])
        selected_tiers += tier_one_hot[best_idx]

    return [int(items[idx]) for idx in selected]


def _metrics_for(cache, users, k, weight, popularity):
    recalls, precisions, ndcgs, divergences, arps, pop_lifts = [], [], [], [], [], []
    recommended = set()
    for user in users:
        entry = cache[user]
        user_weight = (float(weight.get(entry["group"], 0.0))
                       if isinstance(weight, dict) else float(weight))
        result = _rerank(entry, k, user_weight)
        if not result:
            continue
        hits = [int(item in entry["truth"]) for item in result]
        hit_count = sum(hits)
        recalls.append(hit_count / max(len(entry["truth"]), 1))
        precisions.append(hit_count / k)
        dcg = sum(hit / np.log2(rank + 2) for rank, hit in enumerate(hits))
        ideal = min(len(entry["truth"]), k)
        idcg = sum(1.0 / np.log2(rank + 2) for rank in range(ideal))
        ndcgs.append(dcg / idcg if idcg else 0.0)
        tiers = entry["tier"][[np.where(entry["items"] == item)[0][0] for item in result]]
        recommended_distribution = np.bincount(tiers, minlength=3)
        divergences.append(_js_divergence(entry["target"], recommended_distribution))
        arps.append(float(np.mean(popularity[result])))
        profile_items = entry["profile_items"]
        profile_popularity = (
            float(np.mean(popularity[profile_items])) if profile_items.size else 0.0
        )
        rec_popularity = float(np.mean(popularity[result]))
        pop_lifts.append(
            rec_popularity / profile_popularity - 1.0
            if profile_popularity > 0 else 0.0
        )
        recommended.update(result)

    mean_jsd = float(np.mean(divergences)) if divergences else 0.0
    return {
        "Recall@K": float(np.mean(recalls)) if recalls else 0.0,
        "Precision@K": float(np.mean(precisions)) if precisions else 0.0,
        "NDCG@K": float(np.mean(ndcgs)) if ndcgs else 0.0,
        "PopularityJSD": mean_jsd,
        "CalibrationQuality": float(np.clip(1.0 - mean_jsd, 0.0, 1.0)),
        "AverageRecommendedPopularity": float(np.mean(arps)) if arps else 0.0,
        "PopLift": float(np.mean(pop_lifts)) if pop_lifts else 0.0,
        "CatalogCoverage@K": len(recommended) / max(len(popularity), 1),
    }


def _harmonic_objective(accuracy, calibration_quality):
    denominator = accuracy + calibration_quality
    if denominator <= 0.0:
        return 0.0
    return float(2.0 * accuracy * calibration_quality / denominator)


def _print_lambda_table(group, user_count, rows, support):
    print(
        f"\n{group} lambda validation (users={user_count}, "
        f"avg candidates={support['average_candidate_count']:.1f}, "
        f"avg available tiers={support['average_candidate_tiers']:.2f}/3)"
    )
    headers = (
        "Lambda", "Recall@K", "Precision@K", "NDCG@K", "PopularityJSD",
        "CalQuality", "AvgRecPop", "PopLift", "Coverage@K", "Harmonic",
    )
    print(" | ".join(f"{header:>12}" for header in headers))
    print("-" * (15 * len(headers)))
    for row in rows:
        values = (
            row["Lambda"], row["Recall@K"], row["Precision@K"], row["NDCG@K"],
            row["PopularityJSD"], row["CalibrationQuality"],
            row["AverageRecommendedPopularity"], row["PopLift"],
            row["CatalogCoverage@K"], row["HarmonicObjective"],
        )
        print(" | ".join(
            f"{value:12.6f}" if value is not None else f"{'n/a':>12}"
            for value in values
        ))


def fit_group_lambdas(
    model, norm_adj, train_df, val_df, num_users, num_items,
    item_pop, user_epp, global_counts, k=20, candidate_pool=150,
    lambda_grid=None, device="cpu", matching_scores_by_user=None,
):
    """Select one calibration weight per user popularity group on validation."""
    if k < 1:
        raise ValueError("k must be positive.")
    cache, thresholds, popularity, user_groups = _make_candidate_cache(
        model, norm_adj, train_df, val_df, num_users, num_items,
        item_pop, user_epp, global_counts, candidate_pool, device,
        minimum_candidates=k,
        matching_scores_by_user=matching_scores_by_user,
    )
    grid = (
        np.linspace(0.0, 1.0, 11).tolist()
        if lambda_grid is None else [float(value) for value in lambda_grid]
    )
    if not grid:
        raise ValueError("lambda_grid must contain at least one value.")
    if any(not np.isfinite(value) or value < 0.0 or value > 1.0 for value in grid):
        raise ValueError("Every lambda value must be finite and in [0, 1].")
    grid = sorted(set(grid))
    lambdas = {}
    diagnostics = {
        "objective": "harmonic_mean(NDCG@K, 1 - mean_per_user_PopularityJSD)",
        "aggregation": "macro-average user metrics within each validation group",
        "k": int(k),
        "requested_candidate_pool": int(candidate_pool),
        "effective_candidate_pool": max(int(candidate_pool), int(k), 1),
        "candidate_pool_strategy": (
            "preserve original top-K, then fill by relevance in a balanced "
            "popularity-tier-stratified pool"
        ),
        "lambda_grid": grid,
        "groups": {},
    }
    for group in GROUPS:
        users = [u for u, entry in cache.items() if entry["group"] == group]
        entries = [cache[user] for user in users]
        candidate_support = {
            "average_candidate_count": (
                float(np.mean([len(entry["items"]) for entry in entries]))
                if entries else 0.0
            ),
            "average_candidate_tiers": (
                float(np.mean([
                    np.count_nonzero(entry["candidate_tier_counts"])
                    for entry in entries
                ])) if entries else 0.0
            ),
            "average_candidate_tier_counts": {
                tier: (
                    float(np.mean([
                        entry["candidate_tier_counts"][index]
                        for entry in entries
                    ])) if entries else 0.0
                )
                for index, tier in enumerate(("Tail", "Mid", "Head"))
            },
            "average_target_tiers": (
                float(np.mean([entry["target_tier_count"] for entry in entries]))
                if entries else 0.0
            ),
        }
        rows = []
        for weight in grid:
            if users:
                metrics = _metrics_for(cache, users, k, float(weight), popularity)
                harmonic = _harmonic_objective(
                    metrics["NDCG@K"], metrics["CalibrationQuality"]
                )
                row = {"Lambda": float(weight), **metrics}
                row["HarmonicObjective"] = harmonic
            else:
                row = {
                    "Lambda": float(weight),
                    "Recall@K": None,
                    "Precision@K": None,
                    "NDCG@K": None,
                    "PopularityJSD": None,
                    "CalibrationQuality": None,
                    "AverageRecommendedPopularity": None,
                    "PopLift": None,
                    "CatalogCoverage@K": None,
                    "HarmonicObjective": None,
                }
            rows.append(row)

        if users:
            best_row = max(
                rows,
                key=lambda row: (row["HarmonicObjective"], -row["Lambda"]),
            )
            best_weight = best_row["Lambda"]
            selection_note = (
                "Selected the maximum measured objective; ties resolve to the "
                "smallest lambda."
            )
        else:
            best_weight = 0.0
            selection_note = (
                "No validation users in this group; lambda is unidentifiable "
                "and defaults to 0.0."
            )
        lambdas[group] = best_weight
        _print_lambda_table(group, len(users), rows, candidate_support)
        diagnostics["groups"][group] = {
            "validation_user_count": len(users),
            "selected_lambda": best_weight if users else None,
            "selection_note": selection_note,
            "candidate_support": candidate_support,
            "lambda_results": rows,
        }
        if users:
            print(
                f"Selected {group} lambda={best_weight:.1f}; "
                f"validation harmonic objective="
                f"{best_row['HarmonicObjective']:.6f}"
            )

    return {
        "lambdas": lambdas,
        "thresholds": thresholds,
        "user_groups": user_groups,
        "diagnostics": diagnostics,
    }


def _compare_recommendation_lists(reference, candidate):
    users = sorted(reference)
    changed_users = 0
    changed_positions = []
    unique_replacements = []
    for user in users:
        original = reference[user]
        calibrated = candidate[user]
        changed_users += original != calibrated
        width = max(len(original), len(calibrated))
        changed_positions.append(sum(
            (original[index] if index < len(original) else None)
            != (calibrated[index] if index < len(calibrated) else None)
            for index in range(width)
        ))
        unique_replacements.append(
            len(set(original).symmetric_difference(calibrated)) / 2.0
        )
    user_count = len(users)
    return {
        "users_compared": user_count,
        "changed_user_count": int(changed_users),
        "changed_user_percentage": (
            100.0 * changed_users / user_count if user_count else 0.0
        ),
        "average_changed_items_per_user": (
            float(np.mean(changed_positions)) if changed_positions else 0.0
        ),
        "average_unique_items_replaced_per_user": (
            float(np.mean(unique_replacements)) if unique_replacements else 0.0
        ),
    }


def calibrated_ranking_metrics(
    model, norm_adj, train_df, eval_df, num_users, num_items,
    item_pop, user_epp, global_counts, k=20, candidate_pool=150,
    lambdas=None, thresholds=None, device="cpu",
    matching_scores_by_user=None,
    group_assignments=None,
):
    """Evaluate calibrated top-K lists using the selected group weights."""
    cache, computed_thresholds, popularity, _computed_groups = _make_candidate_cache(
        model, norm_adj, train_df, eval_df, num_users, num_items,
        item_pop, user_epp, global_counts, candidate_pool, device,
        group_thresholds=thresholds,
        matching_scores_by_user=matching_scores_by_user,
        group_assignments=group_assignments,
        minimum_candidates=k,
    )
    thresholds = computed_thresholds if thresholds is None else thresholds
    lambdas = {group: 0.0 for group in GROUPS} if lambdas is None else lambdas
    results = {}
    method_weights = (
        ("Original_CausalEPP", {group: 0.0 for group in GROUPS}),
        ("CP_H", lambdas),
        ("CP_Im", {group: 1.0 for group in GROUPS}),
    )
    recommendation_lists = {}
    for method, weights in method_weights:
        grouped = {}
        method_lists = {
            user: (
                [int(item) for item in entry["original_top_items"]]
                if method == "Original_CausalEPP"
                else _rerank(
                    entry,
                    k,
                    float(weights.get(entry["group"], 0.0)),
                )
            )
            for user, entry in cache.items()
        }
        recommendation_lists[method] = method_lists
        for group in GROUPS:
            users = [u for u, entry in cache.items() if entry["group"] == group]
            grouped[group] = _metrics_for(
                cache, users, k, float(weights.get(group, 0.0)), popularity
            )
        grouped["All"] = _metrics_for(cache, list(cache), k, weights, popularity)
        results[method] = grouped

    original_lists = recommendation_lists["Original_CausalEPP"]
    cp_h_lists = recommendation_lists["CP_H"]
    cp_im_lists = recommendation_lists["CP_Im"]
    comparison = {
        "evaluation_user_count": len(cache),
        "k": int(k),
        "candidate_pool": max(int(candidate_pool), int(k), 1),
        "users_without_candidate_cache": len(eval_df.groupby("user")["item"])
        - len(cache),
        "comparison_to_original_CausalEPP": {
            "CP_H": _compare_recommendation_lists(original_lists, cp_h_lists),
            "CP_Im": _compare_recommendation_lists(original_lists, cp_im_lists),
        },
        "CP_H_vs_CP_Im": _compare_recommendation_lists(cp_h_lists, cp_im_lists),
        "CP_H_and_CP_Im_identical": all(
            cp_h_lists[user] == cp_im_lists[user] for user in cp_h_lists
        ),
        "recommendation_lists": {
            str(user): {
                method: lists[user]
                for method, lists in recommendation_lists.items()
            }
            for user in sorted(cache)
        },
    }
    results["recommendation_comparison"] = comparison
    results["evaluation_metadata"] = {
        "k": int(k),
        "candidate_pool": max(int(candidate_pool), int(k), 1),
        "test_users_evaluated": len(cache),
        "global_popularity_counts": "training interactions only",
        "historical_target_distribution": "interaction-weighted prior history",
        "popularity_jsd_aggregation": "macro-average per-user JSD",
        "group_assignments": (
            "frozen from validation-time training-history classification"
            if group_assignments is not None
            else "computed from supplied history and thresholds"
        ),
    }
    return results