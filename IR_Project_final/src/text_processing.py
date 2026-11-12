"""Reusable spaCy cleanup for query text not included in the saved corpus."""

import spacy


def load_nlp(model="en_core_web_sm"):
    """Load the same spaCy English model used for corpus preparation."""
    return spacy.load(model, disable=["ner", "parser"])


def preprocess_texts(texts, nlp=None, batch_size=256):
    """Apply the corpus notebook's token filtering and lemmatization to text."""
    if nlp is None:
        nlp = load_nlp()
    processed_docs = []
    for doc in nlp.pipe(texts, batch_size=batch_size):
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
