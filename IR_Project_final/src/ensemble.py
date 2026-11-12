"""Ranking aggregation helpers for retrieval ensembles."""

import numpy as np


def average_rank_score(member_score_vectors):
    """Aggregate member rankings by the negative mean zero-based rank.

    Each score vector must cover the same documents in the same order, and
    larger scores must indicate better ranks. Ties follow NumPy's default
    ``argsort`` ordering, matching the original bagging notebook.
    """
    scores = np.asarray(member_score_vectors, dtype=np.float64)
    if scores.ndim != 2:
        raise ValueError("Expected a 2D array shaped (members, documents)")
    if scores.shape[0] == 0 or scores.shape[1] == 0:
        raise ValueError("At least one member and one document are required")
    if not np.isfinite(scores).all():
        raise ValueError("Member scores must all be finite")

    member_ranks = np.argsort(np.argsort(-scores, axis=1), axis=1)
    return -member_ranks.mean(axis=0)
