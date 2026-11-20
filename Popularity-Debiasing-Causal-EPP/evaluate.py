
"""Full-sort ranking evaluation for CausalEPP."""

import numpy as np
import torch
import torch.nn.functional as F


def ranking_metrics(
    model,
    norm_adj,
    train_df,
    eval_df,
    num_users,
    num_items,
    item_pop,
    user_epp,
    k=20,
    device="cpu",
    matching_scores_by_user=None,
):
    """
    Evaluate recommendations using full-sort ranking.

    Uses forecasted item popularity p_i* and user EPP s_u*.
    Excludes items already interacted with during training.
    """

    if k < 1:
        raise ValueError("k must be positive.")

    model.eval()

    seen = (
        train_df.groupby("user")["item"]
        .apply(set)
        .to_dict()
    )

    truth = (
        eval_df.groupby("user")["item"]
        .apply(set)
        .to_dict()
    )

    item_pop = torch.as_tensor(
        item_pop, dtype=torch.float32, device=device
    )

    user_epp = torch.as_tensor(
        user_epp, dtype=torch.float32, device=device
    )

    if item_pop.numel() != num_items:
        raise ValueError("item_pop must contain one value per item.")

    if user_epp.numel() < num_users:
        raise ValueError("user_epp must contain one value per user.")

    recalls = []
    precisions = []
    ndcgs = []
    recommended_items = set()

    all_items = torch.arange(
        num_items, dtype=torch.long, device=device
    )

    with torch.no_grad():
        user_embeddings, item_embeddings = model.lightgcn.propagate(
            norm_adj
        )

        for user, actual_items in truth.items():

            if not actual_items or user >= num_users:
                continue

            if matching_scores_by_user is None:
                items = all_items
                matching = (user_embeddings[user].unsqueeze(0) * item_embeddings).sum(dim=-1)
            else:
                user_score_map = matching_scores_by_user.get(int(user), {})
                candidate_ids = [
                    int(item) for item in user_score_map
                    if int(item) not in seen.get(user, set())
                ]
                if not candidate_ids:
                    continue
                items = torch.tensor(candidate_ids, dtype=torch.long, device=device)
                matching = torch.tensor(
                    [user_score_map[item] for item in candidate_ids],
                    dtype=torch.float32,
                    device=device,
                )

            # Equation (6): matching score m_ui.
            # Forecasted popularity and EPP: p_i* and s_u*.
            p = item_pop[items].clamp(0.0, 1.0)
            s = user_epp[user].expand_as(p).clamp(0.0, 1.0)

            # Equation (17): forecasted conformity c_ui*.
            item_mapping = model.item_mlp(
                item_embeddings[items]
            ).squeeze(-1)

            conformity = (
                torch.exp(-model.alpha * torch.abs(s - p))
                * p
                * item_mapping
            )

            # Equation (16): final inference recommendation score.
            scores = (
                torch.tanh(model.q[items] + conformity)
                * F.softplus(matching)
            )

            # Exclude previously interacted items.
            previous_items = seen.get(user, set())

            if previous_items and matching_scores_by_user is None:
                previous_indices = torch.tensor(
                    list(previous_items),
                    dtype=torch.long,
                    device=device,
                )
                scores[previous_indices] = -torch.inf

            valid_count = (
                scores.numel() if matching_scores_by_user is not None
                else num_items - len(previous_items)
            )
            top_k = min(k, valid_count)

            if top_k <= 0:
                continue

            top_positions = torch.topk(scores, top_k).indices
            top_items = items[top_positions].cpu().numpy().tolist()

            recommended_items.update(top_items)

            hits = [
                1 if item in actual_items else 0
                for item in top_items
            ]

            hit_count = sum(hits)

            recalls.append(
                hit_count / len(actual_items)
            )

            precisions.append(
                hit_count / k
            )

            dcg = sum(
                hit / np.log2(rank + 2)
                for rank, hit in enumerate(hits)
            )

            ideal_hits = min(len(actual_items), k)

            idcg = sum(
                1.0 / np.log2(rank + 2)
                for rank in range(ideal_hits)
            )

            ndcgs.append(
                dcg / idcg if idcg > 0 else 0.0
            )

    return {
        "Recall@K": float(np.mean(recalls)) if recalls else 0.0,
        "Precision@K": float(np.mean(precisions)) if precisions else 0.0,
        "NDCG@K": float(np.mean(ndcgs)) if ndcgs else 0.0,
        "CatalogCoverage@K": (
            len(recommended_items) / num_items
            if num_items else 0.0
        ),
    }


def recommendation_examples(
    model,
    norm_adj,
    history_df,
    test_df,
    num_users,
    num_items,
    item_pop,
    user_epp,
    k=20,
    device="cpu",
    item_names=None,
    max_users=5,
    matching_scores_by_user=None,
):
    """Build readable top-K recommendation examples for selected test users."""
    model.eval()
    item_names = item_names or {}
    item_pop = torch.as_tensor(item_pop, dtype=torch.float32, device=device)
    user_epp = torch.as_tensor(user_epp, dtype=torch.float32, device=device)
    all_items = torch.arange(num_items, dtype=torch.long, device=device)
    seen = history_df.groupby("user")["item"].apply(set).to_dict()
    truth = test_df.groupby("user")["item"].apply(set).to_dict()
    selected_users = sorted(
        int(user) for user, actual in truth.items()
        if actual and int(user) < num_users
    )[:max_users]
    examples = []

    with torch.no_grad():
        user_embeddings, item_embeddings = model.lightgcn.propagate(norm_adj)
        item_mapping = model.item_mlp(item_embeddings).squeeze(-1)
        for user in selected_users:
            if matching_scores_by_user is None:
                items = all_items
                matching = (user_embeddings[user].unsqueeze(0) * item_embeddings).sum(dim=-1)
            else:
                user_score_map = matching_scores_by_user.get(user, {})
                candidate_ids = [
                    int(item) for item in user_score_map
                    if int(item) not in seen.get(user, set())
                ]
                items = torch.tensor(candidate_ids, dtype=torch.long, device=device)
                matching = torch.tensor(
                    [user_score_map[item] for item in candidate_ids],
                    dtype=torch.float32,
                    device=device,
                )
            p = item_pop[items].clamp(0.0, 1.0)
            s = user_epp[user].expand_as(p).clamp(0.0, 1.0)
            conformity = (
                torch.exp(-model.alpha * torch.abs(s - p))
                * p
                * item_mapping[items]
            )
            scores = torch.tanh(model.q[items] + conformity) * F.softplus(matching)

            previous_items = seen.get(user, set())
            if previous_items and matching_scores_by_user is None:
                previous_indices = torch.tensor(
                    list(previous_items), dtype=torch.long, device=device
                )
                scores[previous_indices] = -torch.inf

            actual_items = sorted(int(item) for item in truth[user])
            top_k = min(k, len(items))
            if top_k:
                top_scores, top_indices = torch.topk(scores, top_k)
                top_item_ids = items[top_indices].cpu().tolist()
                recommendations = []
                for rank, (item_id, score, matching_score) in enumerate(
                    zip(
                        top_item_ids,
                        top_scores.cpu().tolist(),
                        matching[top_indices].cpu().tolist(),
                    ),
                    start=1,
                ):
                    recommendations.append({
                        "rank": rank,
                        "item_id": int(item_id),
                        "item_name": item_names.get(int(item_id)),
                        "score": float(score),
                        "matching_score_m_ui": float(matching_score),
                        "is_test_item": int(item_id) in truth[user],
                    })
            else:
                recommendations = []

            examples.append({
                "user_id": user,
                "test_items": [
                    {"item_id": item_id, "item_name": item_names.get(item_id)}
                    for item_id in actual_items
                ],
                "recommendations": recommendations,
            })

    return {
        "description": "Top-K CausalEPP recommendations for the first test users, ordered by user ID.",
        "score_note": "Scores are ranking scores, not probabilities.",
        "k": int(k),
        "users_shown": len(examples),
        "users": examples,
    }
