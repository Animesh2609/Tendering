"""Shared synthetic-mixture and ensemble helpers; study loops stay in notebooks."""
import numpy as np
from scipy.sparse import csr_matrix

def sample_token_ids(row):
    row = csr_matrix(row)
    return np.repeat(row.indices, row.data.astype(int))

def make_mixed_document(X_source, y_source, class_a, class_b,
                        ratio_a, rng, n_tokens=300):

    a_candidates = np.where((y_source == class_a) & (np.asarray(X_source.sum(axis=1)).ravel() > 0))[0]
    b_candidates = np.where((y_source == class_b) & (np.asarray(X_source.sum(axis=1)).ravel() > 0))[0]

    da = X_source[a_candidates[rng.integers(len(a_candidates))]]
    db = X_source[b_candidates[rng.integers(len(b_candidates))]]
    tokens_a = sample_token_ids(da)
    tokens_b = sample_token_ids(db)
    if len(tokens_a) == 0 or len(tokens_b) == 0:
        raise ValueError("A sampled source document had no in-vocabulary tokens.")
    n_a = int(round(n_tokens * ratio_a))
    n_b = n_tokens - n_a
    tokens = np.concatenate([
        rng.choice(tokens_a, size=n_a, replace=True),
        rng.choice(tokens_b, size=n_b, replace=True)
    ])
    counts = np.bincount(tokens, minlength=X_source.shape[1]).astype(float)
    return csr_matrix(counts.reshape(1, -1))

def average_rank_score(member_score_vectors):
    member_ranks = [np.argsort(np.argsort(-scores)) for scores in member_score_vectors]
    return -np.mean(member_ranks, axis=0)
