"""Shared retrieval scoring from Group 12's PLSA notebooks."""

from .config import VECTORIZER_SETTINGS

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer


def make_tfidf_vectorizer():
    return TfidfVectorizer(**VECTORIZER_SETTINGS)


def fit_baselines(train_processed, *other_processed, seed=42):
    """Fit TF-IDF and 50-component LSI on train; transform other splits."""
    tfidf = make_tfidf_vectorizer()
    train_tfidf = tfidf.fit_transform(train_processed)
    others_tfidf = tuple(tfidf.transform(docs) for docs in other_processed)
    n_components = min(50, train_tfidf.shape[0] - 1, train_tfidf.shape[1] - 1)
    if n_components < 1:
        raise ValueError("Not enough training documents/features for LSI")
    lsi = make_pipeline(
        TruncatedSVD(n_components=n_components, random_state=seed),
        Normalizer(copy=False),
    )
    train_lsi = lsi.fit_transform(train_tfidf)
    others_lsi = tuple(lsi.transform(X) for X in others_tfidf)
    return tfidf, lsi, (train_tfidf, *others_tfidf), (train_lsi, *others_lsi)


def cosine_scores(query_vector, document_vectors):
    """Return a score for each document (larger is better)."""
    return cosine_similarity(query_vector, document_vectors).ravel()


def plsa_cosine_scores(model, query_counts, document_theta, max_iter=100):
    """Fold query into topics and compare with document-topic vectors."""
    query_theta = model.fold_in(query_counts, max_iter=max_iter)
    return cosine_scores(query_theta, document_theta)


def plsa_query_log_likelihood(query_counts, document_theta, phi,
                              smoothing=1e-10, background_probability=None,
                              background_weight=0.0):
    """Log P(query|document) with optional background smoothing.

    With background_weight=0 this matches the scoring-investigation notebook.
    With a nonzero weight it matches the validation notebook's background mixture.
    """
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
    """Unigram background distribution from training counts only."""
    counts = np.asarray(train_counts.sum(axis=0)).ravel().astype(float)
    if counts.sum() == 0:
        raise ValueError("Training counts are empty")
    return counts / counts.sum()


def top_k_indices(scores, k=10):
    return np.argsort(np.asarray(scores))[::-1][:k]
