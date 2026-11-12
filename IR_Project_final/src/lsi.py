"""Latent Semantic Indexing fitted from training-only TF-IDF features."""

from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer


def fit_lsi(train_tfidf, *other_tfidf, n_components=50, seed=42):
    """Fit SVD and row normalization on training TF-IDF, then transform others.

    As in the original baseline, the requested dimension is capped by the
    training matrix dimensions. Validation/test/query rows never participate
    in fitting the SVD.
    """
    actual_components = min(
        n_components,
        train_tfidf.shape[0] - 1,
        train_tfidf.shape[1] - 1,
    )
    if actual_components < 1:
        raise ValueError("Not enough training documents/features for LSI")
    model = make_pipeline(
        TruncatedSVD(n_components=actual_components, random_state=seed),
        Normalizer(copy=False),
    )
    train_lsi = model.fit_transform(train_tfidf)
    other_lsi = tuple(model.transform(matrix) for matrix in other_tfidf)
    return model, (train_lsi, *other_lsi)
