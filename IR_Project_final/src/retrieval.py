"""Shared similarity and PLSA query-likelihood scoring functions."""

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity


def cosine_scores(query_vector, document_vectors):
    """Return a score per document; larger cosine scores rank higher."""
    return cosine_similarity(query_vector, document_vectors).ravel()


def plsa_cosine_scores(model, query_counts, document_theta, max_iter=100):
    """Fold a query into topic space and compare it with document mixtures."""
    query_theta = model.fold_in(query_counts, max_iter=max_iter)
    return cosine_scores(query_theta, document_theta)


def plsa_query_log_likelihood(
    query_counts,
    document_theta,
    phi,
    smoothing=1e-10,
    background_probability=None,
    background_weight=0.0,
):
    """Score documents by log P(query|document), optionally with background mix."""
    if not 0 <= background_weight <= 1:
        raise ValueError("background_weight must be between 0 and 1")
    if background_weight and background_probability is None:
        raise ValueError("background_probability is required when smoothing with background")
    query_counts = csr_matrix(query_counts, dtype=np.float64)
    if query_counts.shape[0] != 1:
        raise ValueError("Pass one query row at a time")
    scores = np.zeros(document_theta.shape[0], dtype=np.float64)
    for word_id, count in zip(query_counts.indices, query_counts.data):
        p_word_given_doc = document_theta @ phi[:, word_id]
        if background_weight:
            p_word_given_doc = (
                (1 - background_weight) * p_word_given_doc
                + background_weight * background_probability[word_id]
            )
        scores += count * np.log(np.maximum(p_word_given_doc, smoothing))
    return scores


def background_word_probabilities(train_counts):
    """Return the unigram background distribution from training counts."""
    counts = np.asarray(train_counts.sum(axis=0)).ravel().astype(float)
    if counts.sum() == 0:
        raise ValueError("Training counts are empty")
    return counts / counts.sum()


def top_k_indices(scores, k=10):
    """Return indices sorted from highest to lowest score, limited to k."""
    return np.argsort(np.asarray(scores))[::-1][:k]
