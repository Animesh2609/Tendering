"""Synthetic mixed-document generation used by the baseline study."""

import numpy as np
from scipy.sparse import csr_matrix


def sample_token_ids(row):
    """Expand one sparse count row into token IDs, repeating by count."""
    row = csr_matrix(row)
    return np.repeat(row.indices, row.data.astype(int))


def make_mixed_document(
    X_source,
    y_source,
    class_a,
    class_b,
    ratio_a,
    rng,
    n_tokens=300,
):
    """Sample tokens from two labeled classes to construct one mixed document."""
    y_source = np.asarray(y_source)
    nonempty_rows = np.asarray(X_source.sum(axis=1)).ravel() > 0
    a_candidates = np.where((y_source == class_a) & nonempty_rows)[0]
    b_candidates = np.where((y_source == class_b) & nonempty_rows)[0]
    if len(a_candidates) == 0 or len(b_candidates) == 0:
        raise ValueError("Both source classes need at least one nonempty document.")
    if not 0 <= ratio_a <= 1:
        raise ValueError("ratio_a must be between 0 and 1")

    doc_a = X_source[a_candidates[rng.integers(len(a_candidates))]]
    doc_b = X_source[b_candidates[rng.integers(len(b_candidates))]]
    tokens_a = sample_token_ids(doc_a)
    tokens_b = sample_token_ids(doc_b)
    if len(tokens_a) == 0 or len(tokens_b) == 0:
        raise ValueError("A sampled source document had no in-vocabulary tokens.")
    n_a = int(round(n_tokens * ratio_a))
    n_b = n_tokens - n_a
    tokens = np.concatenate([
        rng.choice(tokens_a, size=n_a, replace=True),
        rng.choice(tokens_b, size=n_b, replace=True),
    ])
    counts = np.bincount(tokens, minlength=X_source.shape[1]).astype(float)
    return csr_matrix(counts.reshape(1, -1))
