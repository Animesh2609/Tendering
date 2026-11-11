"""One loader and label mapping for all six notebooks.

The official sklearn loader removes headers, footers and quotes consistently.
The original train/test partitions are pooled, then each experiment applies its
predeclared stratified split. Labels never enter PLSA.fit().
"""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from sklearn.datasets import fetch_20newsgroups
from .config import SEED, SIX_CATEGORIES, SUPERGROUPS

@dataclass
class Corpus:
    documents: np.ndarray
    labels: np.ndarray
    target_names: list
    original_labels: np.ndarray
    source_category_names: list


def map_supergroups(original_labels, source_category_names):
    members = [name for names in SUPERGROUPS.values() for name in names]
    if len(members) != len(set(members)) or set(members) != set(source_category_names):
        raise ValueError("Supergroups must cover every source category exactly once")
    lookup = {category: i for i, names in enumerate(SUPERGROUPS.values()) for category in names}
    return np.asarray([lookup[source_category_names[i]] for i in original_labels])


def load_corpus(corpus="all20", seed=SEED, data_home=None):
    if corpus not in {"all20", "six_categories", "supergroups"}:
        raise ValueError(f"Unknown corpus: {corpus}")
    # Keep downloaded/cache data inside the checkout instead of a user's home.
    if data_home is None:
        data_home = Path(__file__).resolve().parents[1] / ".cache" / "sklearn"
    dataset = fetch_20newsgroups(
        subset="all", categories=SIX_CATEGORIES if corpus == "six_categories" else None,
        remove=("headers", "footers", "quotes"), shuffle=True,
        random_state=seed, data_home=str(data_home),
    )
    original = np.asarray(dataset.target)
    names = list(dataset.target_names)
    labels = map_supergroups(original, names) if corpus == "supergroups" else original.copy()
    return Corpus(np.asarray(dataset.data, dtype=object), labels,
                  list(SUPERGROUPS) if corpus == "supergroups" else names,
                  original, names)
