"""TF-IDF vectorization fitted on experiment training documents."""

from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer


def make_tfidf_vectorizer(
    max_features: Optional[int] = 3000,
    min_df: int | float = 3,
    max_df: int | float = 0.90,
) -> TfidfVectorizer:
    """Create a TF-IDF vectorizer using the original project defaults."""
    return TfidfVectorizer(
        lowercase=False,
        tokenizer=str.split,
        token_pattern=None,
        max_features=max_features,
        min_df=min_df,
        max_df=max_df,
    )


def fit_tfidf(train_documents, *other_documents, **vectorizer_options):
    """Fit TF-IDF on training text and transform all additional text splits."""
    vectorizer = make_tfidf_vectorizer(**vectorizer_options)
    train_vectors = vectorizer.fit_transform(train_documents)
    other_vectors = tuple(
        vectorizer.transform(documents) for documents in other_documents
    )
    return vectorizer, (train_vectors, *other_vectors)
