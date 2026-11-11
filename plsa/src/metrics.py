"""Binary category relevance metrics, shared by every retrieval experiment."""
import numpy as np


def metrics_at_k(scores, labels, target, k=10, suffix=None):
    """Return per-query metrics; averaging AP across queries produces MAP.

    Precision divides by the available top-k candidate count, recall by all
    relevant candidates, AP by min(k, total relevant), and NDCG by ideal DCG.
    MRR is truncated at k (the legacy output column is named MRR).
    Preserve the notebooks' descending argsort tie ordering.
    """
    scores, labels = np.asarray(scores), np.asarray(labels)
    if scores.ndim != 1 or labels.ndim != 1 or len(scores) != len(labels):
        raise ValueError("scores and labels must be aligned one-dimensional arrays")
    if not isinstance(k, (int, np.integer)) or k < 1:
        raise ValueError("k must be a positive integer")
    if not np.isfinite(scores).all():
        raise ValueError("scores must be finite")
    relevant = labels == target
    total = int(relevant.sum())
    selected = relevant[np.argsort(scores)[::-1][:k]].astype(float)
    hits = selected.sum()
    precision = float(hits / len(selected)) if len(selected) else 0.0
    recall = float(hits / total) if total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    ranks = np.arange(1, len(selected) + 1)
    ap = float(np.sum(np.cumsum(selected) / ranks * selected) / min(total, k)) if total else 0.0
    dcg = float(np.sum(selected / np.log2(ranks + 1)))
    ideal = float(np.sum(1 / np.log2(np.arange(2, min(total, k) + 2))))
    hit_ranks = np.flatnonzero(selected) + 1
    suffix = str(k) if suffix is None else str(suffix)
    return {f"Precision@{suffix}": precision, f"Recall@{suffix}": recall,
            f"F1@{suffix}": f1, f"AP@{suffix}": ap,
            f"NDCG@{suffix}": dcg / ideal if ideal else 0.0,
            "MRR": float(1 / hit_ranks[0]) if len(hit_ranks) else 0.0}
