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
    for user, history in train_df.groupby("user")["item"]:
        ids = history.to_numpy(dtype=np.int64)
        user_means[int(user)] = float(log_pop[ids].mean()) if ids.size else 0.0
    active = user_means[np.array(
        [u in set(train_df["user"].unique()) for u in range(num_users)],
        dtype=bool,
    )]
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

    return 0.5 * kl(left, middle) + 0.5 * kl(right, middle)


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
    return 0.5 * (left + right)


def _make_candidate_cache(
    model, norm_adj, train_df, eval_df, num_users, num_items,
    item_pop, user_epp, global_counts, candidate_pool, device,
    group_thresholds=None,
    matching_scores_by_user=None,
):
    model.eval()
    seen = train_df.groupby("user")["item"].apply(set).to_dict()
    truth = eval_df.groupby("user")["item"].apply(set).to_dict()
    counts = np.asarray(global_counts, dtype=np.float64).reshape(-1)
    tiers = _tiers(counts)
    popularity = counts
    user_means, computed_thresholds = _profile_groups(train_df, num_users, counts)
    thresholds = group_thresholds or computed_thresholds
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
            take = min(max(int(candidate_pool), 1), available_count)
            if take <= 0:
                continue
            values, indices = torch.topk(scores, take)
            item_ids = items[indices].cpu().numpy().astype(np.int64)
            rel = values.cpu().numpy().astype(np.float64)
            finite = np.isfinite(rel)
            item_ids, rel = item_ids[finite], rel[finite]
            if rel.size:
                span = float(rel.max() - rel.min())
                rel = (rel - rel.min()) / span if span > 1e-12 else np.ones_like(rel)
            history = np.fromiter(previous, dtype=np.int64)
            target = np.bincount(tiers[history], minlength=3).astype(np.float64)
            if target.sum() == 0:
                target = np.array([1.0, 0.0, 0.0])
            cache[user] = {
                "truth": set(int(x) for x in actual_items),
                "items": item_ids,
                "relevance": rel,
                "tier": tiers[item_ids],
                "target": target,
                "profile_items": np.fromiter(previous, dtype=np.int64),
                "group": _group_name(user, user_means, thresholds),
            }

    return cache, thresholds, popularity


def _rerank(entry, k, weight):
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

    return {
        "Recall@K": float(np.mean(recalls)) if recalls else 0.0,
        "Precision@K": float(np.mean(precisions)) if precisions else 0.0,
        "NDCG@K": float(np.mean(ndcgs)) if ndcgs else 0.0,
        "PopularityJSD": float(np.mean(divergences)) if divergences else 0.0,
        "AverageRecommendedPopularity": float(np.mean(arps)) if arps else 0.0,
        "PopLift": float(np.mean(pop_lifts)) if pop_lifts else 0.0,
        "CatalogCoverage@K": len(recommended) / max(len(popularity), 1),
    }


def fit_group_lambdas(
    model, norm_adj, train_df, val_df, num_users, num_items,
    item_pop, user_epp, global_counts, k=20, candidate_pool=150,
    lambda_grid=None, device="cpu", matching_scores_by_user=None,
):
    """Select one calibration weight per user popularity group on validation."""
    cache, thresholds, popularity = _make_candidate_cache(
        model, norm_adj, train_df, val_df, num_users, num_items,
        item_pop, user_epp, global_counts, candidate_pool, device,
        matching_scores_by_user=matching_scores_by_user,
    )
    grid = list(lambda_grid or np.linspace(0.0, 1.0, 11))
    lambdas = {}
    for group in GROUPS:
        users = [u for u, entry in cache.items() if entry["group"] == group]
        best_weight, best_score = 0.0, -float("inf")
        for weight in grid:
            metrics = _metrics_for(cache, users, k, float(weight), popularity)
            accuracy = metrics["NDCG@K"]
            calibration = max(0.0, 1.0 - metrics["PopularityJSD"])
            harmonic = (2.0 * accuracy * calibration / (accuracy + calibration)
                        if accuracy + calibration else 0.0)
            if harmonic > best_score:
                best_weight, best_score = float(weight), harmonic
        lambdas[group] = best_weight
    return {"lambdas": lambdas, "thresholds": thresholds}


def calibrated_ranking_metrics(
    model, norm_adj, train_df, eval_df, num_users, num_items,
    item_pop, user_epp, global_counts, k=20, candidate_pool=150,
    lambdas=None, thresholds=None, device="cpu",
    matching_scores_by_user=None,
):
    """Evaluate calibrated top-K lists using the selected group weights."""
    cache, computed_thresholds, popularity = _make_candidate_cache(
        model, norm_adj, train_df, eval_df, num_users, num_items,
        item_pop, user_epp, global_counts, candidate_pool, device,
        group_thresholds=thresholds,
        matching_scores_by_user=matching_scores_by_user,
    )
    thresholds = thresholds or computed_thresholds
    lambdas = lambdas or {group: 0.0 for group in GROUPS}
    results = {}
    for method, weights in (
        ("CP_H", lambdas),
        ("CP_Im", {group: 1.0 for group in GROUPS}),
    ):
        grouped = {}
        for group in GROUPS:
            users = [u for u, entry in cache.items() if entry["group"] == group]
            grouped[group] = _metrics_for(
                cache, users, k, float(weights.get(group, 0.0)), popularity
            )
        grouped["All"] = _metrics_for(cache, list(cache), k, weights, popularity)
        results[method] = grouped
    return results
