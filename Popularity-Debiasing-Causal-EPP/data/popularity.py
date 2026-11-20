
"""Temporal popularity and evolving personal popularity features for CausalEPP."""

from pathlib import Path

import numpy as np
import pandas as pd


def compute_local_popularity(
    interactions,
    num_time_bins=100,
    num_items=None,
    time_bin_col="time_bin",
):
    """
    Compute local item popularity for each time bin.

    Equation 1:
        p_i^t = count(i in temporal window t) / total interactions in t

    Returns:
        popularity: float32 array of shape (num_time_bins, num_items).
    """
    if num_time_bins < 1:
        raise ValueError("num_time_bins must be positive.")

    required = {"item", time_bin_col}
    missing = required - set(interactions.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    if num_items is None:
        num_items = int(interactions["item"].max()) + 1

    popularity = np.zeros(
        (num_time_bins, num_items), dtype=np.float32
    )

    for t in range(num_time_bins):
        block = interactions[interactions[time_bin_col] == t]

        if block.empty:
            continue

        counts = block["item"].value_counts()
        valid_items = counts.index.to_numpy(dtype=np.int64)
        valid_counts = counts.to_numpy(dtype=np.float32)

        popularity[t, valid_items] = valid_counts / len(block)

    return popularity


def compute_evolving_personal_popularity(
    interactions,
    item_popularity,
    num_users=None,
    popularity_quantile=0.80,
    num_time_bins=None,
    time_bin_col="time_bin",
):
    """
    Compute evolving personal popularity for each user and time bin.

    Equation 3:
        s_u^t = fraction of user u's interactions in bin t
                involving items above the local-popularity threshold.

    The threshold is the configured quantile of positive local-popularity
    values in each time bin.
    """
    if not 0.0 < popularity_quantile < 1.0:
        raise ValueError("popularity_quantile must be between 0 and 1.")

    required = {"user", "item", time_bin_col}
    missing = required - set(interactions.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    if num_users is None:
        num_users = int(interactions["user"].max()) + 1

    if num_time_bins is None:
        num_time_bins = item_popularity.shape[0]

    if item_popularity.shape[0] < num_time_bins:
        raise ValueError("item_popularity has fewer time bins than requested.")

    epp = np.zeros((num_time_bins, num_users), dtype=np.float32)

    for t in range(num_time_bins):
        block = interactions[interactions[time_bin_col] == t]

        if block.empty:
            continue

        positive_popularity = item_popularity[t][
            item_popularity[t] > 0
        ]

        if positive_popularity.size == 0:
            continue

        threshold = np.quantile(
            positive_popularity, popularity_quantile
        )

        # Strict comparison follows the paper's p_i^t > threshold condition.
        high_popular_items = np.flatnonzero(
            item_popularity[t] > threshold
        )

        user_counts = block.groupby("user").size()

        high_counts = (
            block[block["item"].isin(high_popular_items)]
            .groupby("user")
            .size()
        )

        high_counts = high_counts.reindex(
            user_counts.index, fill_value=0
        )

        users = user_counts.index.to_numpy(dtype=np.int64)
        epp[ t, users] = (
            high_counts.to_numpy(dtype=np.float32)
            / user_counts.to_numpy(dtype=np.float32)
        )

    return epp


def compute_global_popularity(interactions, num_items=None):
    """
    Compute global item interaction counts d_i.

    Used by the quality loss (Equation 10) as the item-quality proxy.
    Ratings are deliberately not used.
    """
    if "item" not in interactions.columns:
        raise ValueError("Interactions must contain an 'item' column.")

    if num_items is None:
        num_items = int(interactions["item"].max()) + 1

    counts = np.zeros(num_items, dtype=np.float32)
    item_counts = interactions["item"].value_counts()

    item_ids = item_counts.index.to_numpy(dtype=np.int64)
    counts[item_ids] = item_counts.to_numpy(dtype=np.float32)

    return counts


def compute_expected_local_popularity(item_popularity):
    """
    Estimate each item's expected local popularity across observed bins.

    Returns:
        Array of shape (num_items,).
    """
    if item_popularity.ndim != 2:
        raise ValueError(
            "item_popularity must have shape (num_time_bins, num_items)."
        )

    return item_popularity.mean(axis=0).astype(np.float32)


def save_popularity_features(
    output_dir,
    item_popularity,
    user_epp,
    global_popularity=None,
    expected_popularity=None,
):
    """Save computed popularity features as NumPy arrays."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    np.save(output_dir / "item_local_popularity.npy", item_popularity)
    np.save(output_dir / "user_epp.npy", user_epp)

    if global_popularity is not None:
        np.save(output_dir / "global_item_counts.npy", global_popularity)

    if expected_popularity is not None:
        np.save(
            output_dir / "expected_item_popularity.npy",
            expected_popularity,
        )


def load_popularity_features(data_dir):
    """Load popularity features saved during preprocessing."""
    data_dir = Path(data_dir)

    popularity_path = data_dir / "item_local_popularity.npy"
    epp_path = data_dir / "user_epp.npy"

    if not popularity_path.exists():
        raise FileNotFoundError(f"Missing feature file: {popularity_path}")

    if not epp_path.exists():
        raise FileNotFoundError(f"Missing feature file: {epp_path}")

    return np.load(popularity_path), np.load(epp_path)
