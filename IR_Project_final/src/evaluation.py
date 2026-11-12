"""Binary relevance metrics matching the original baseline notebook."""

import numpy as np


def evaluate_ranked_retrieval(scores, labels, target_label, k=10):
    """Compute P@k, recall@k, AP@k and NDCG@k for a category query.

    Relevance is category membership. The precision denominator remains k,
    matching the original baseline. AP and ideal DCG use at most the number of
    relevant candidates in the evaluated set. If there are no relevant items,
    all metrics are returned as zero.
    """
    if k < 1:
        raise ValueError("k must be at least 1")
    scores = np.asarray(scores)
    labels = np.asarray(labels)
    if scores.ndim != 1 or labels.ndim != 1 or len(scores) != len(labels):
        raise ValueError("scores and labels must be one-dimensional and equal length")

    total_relevant = int(np.count_nonzero(labels == target_label))
    if total_relevant == 0:
        return {
            "Precision@k": 0.0,
            "Recall@k": 0.0,
            "AP@k": 0.0,
            "NDCG@k": 0.0,
        }

    ranked_indices = np.argsort(scores)[::-1][:k]
    relevance = (labels[ranked_indices] == target_label).astype(float)
    true_positives = int(relevance.sum())

    precision = true_positives / k
    recall = true_positives / total_relevant
    precisions_at_ranks = np.cumsum(relevance) / np.arange(1, len(relevance) + 1)
    ap_at_k = float(
        np.sum(precisions_at_ranks * relevance) / min(total_relevant, k)
    ) if len(relevance) else 0.0
    discounts = np.log2(np.arange(2, len(relevance) + 2))
    dcg = float(np.sum(relevance / discounts))
    ideal_count = min(k, total_relevant, len(relevance))
    idcg = float(np.sum(1.0 / np.log2(np.arange(2, ideal_count + 2))))
    ndcg = dcg / idcg if idcg > 0 else 0.0

    return {
        "Precision@k": float(precision),
        "Recall@k": float(recall),
        "AP@k": float(ap_at_k),
        "NDCG@k": float(ndcg),
    }
