"""Shared preprocessing and count-vectorization from the Group 12 notebooks."""

from functools import lru_cache
from .config import VECTORIZER_SETTINGS

import numpy as np
import spacy
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split


@lru_cache(maxsize=1)
def load_nlp():
    """Requires: python -m spacy download en_core_web_sm"""
    return spacy.load("en_core_web_sm", disable=["ner", "parser"])


def preprocess_texts(texts, nlp=None):
    """Lemmatize, remove stop words, punctuation, numbers and short tokens."""
    if nlp is None:
        nlp = load_nlp()
    processed_docs = []
    for doc in nlp.pipe(texts, batch_size=256):
        tokens = []
        for token in doc:
            if token.is_space or token.is_punct or token.like_num or not token.is_alpha:
                continue
            if token.is_stop:
                continue
            lemma = token.lemma_.lower().strip()
            if len(lemma) < 2:
                continue
            tokens.append(lemma)
        processed_docs.append(" ".join(tokens))
    return processed_docs


def make_count_vectorizer():
    """Use the same settings as the original notebooks."""
    return CountVectorizer(**VECTORIZER_SETTINGS, dtype=np.float64)


def split_train_test(documents, labels, *aligned_arrays, test_size=0.25, seed=42):
    """Stratified split; preserve alignment of optional original category labels."""
    return train_test_split(
        documents, labels, *aligned_arrays, test_size=test_size, random_state=seed, stratify=labels
    )


def split_train_val_test(documents, labels, seed=42):
    """60/20/20 stratified split used in validation and K studies."""
    train_docs, temp_docs, y_train, y_temp = train_test_split(
        documents, labels, test_size=0.40, random_state=seed, stratify=labels
    )
    val_docs, test_docs, y_val, y_test = train_test_split(
        temp_docs, y_temp, test_size=0.50, random_state=seed, stratify=y_temp
    )
    return train_docs, val_docs, test_docs, y_train, y_val, y_test


def vectorize_counts(train_processed, *other_processed):
    """Fit on training data only; transform validation/test with same vocabulary."""
    vectorizer = make_count_vectorizer()
    train_counts = vectorizer.fit_transform(train_processed)
    other_counts = tuple(vectorizer.transform(docs) for docs in other_processed)
    return (vectorizer, train_counts, *other_counts)
