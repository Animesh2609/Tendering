
"""Prepare Ciao interactions and temporal features for CausalEPP."""

from pathlib import Path

import numpy as np
import pandas as pd

from data.popularity import (
    compute_local_popularity,
    compute_evolving_personal_popularity,
)

COLUMNS = ["user", "item", "rating", "timestamp"]


def _k_core(df, min_user=5, min_item=5):
    """Iteratively apply user/item k-core filtering until convergence."""
    df = df.copy()

    while True:
        previous_size = len(df)

        user_counts = df["user"].value_counts()
        item_counts = df["item"].value_counts()

        df = df[
            df["user"].isin(user_counts[user_counts >= min_user].index)
            & df["item"].isin(item_counts[item_counts >= min_item].index)
        ]

        if len(df) == previous_size:
            return df.reset_index(drop=True)


def _chronological_split(df):
    """
    Chronologically split interactions.

    First 90% of the timeline: training.
    Remaining 10%: validation and test, split chronologically.
    """
    df = df.sort_values(
        ["timestamp", "user", "item"]
    ).reset_index(drop=True)

    timestamps = df["timestamp"].to_numpy(dtype=np.float64)

    train_cutoff = np.quantile(timestamps, 0.90)

    train = df[df["timestamp"] < train_cutoff].copy()
    holdout = df[df["timestamp"] >= train_cutoff].copy()

    if train.empty or holdout.empty:
        raise ValueError("Unable to create chronological split.")

    validation_cutoff = np.quantile(
        holdout["timestamp"].to_numpy(dtype=np.float64),
        0.50,
    )

    val = holdout[
        holdout["timestamp"] <= validation_cutoff
    ].copy()

    test = holdout[
        holdout["timestamp"] > validation_cutoff
    ].copy()

    # Handle tied timestamps at the split boundary.
    if val.empty or test.empty:
        holdout = holdout.sort_values(
            ["timestamp", "user", "item"]
        ).reset_index(drop=True)

        midpoint = len(holdout) // 2

        val = holdout.iloc[:midpoint].copy()
        test = holdout.iloc[midpoint:].copy()

    return train, val, test


def _assign_training_time_bins(train, all_data, num_time_bins):
    """Create time bins using only the training timeline."""
    train = train.copy()
    all_data = all_data.copy()

    t_min = float(train["timestamp"].min())
    t_max = float(train["timestamp"].max())

    if t_min == t_max:
        edges = np.linspace(
            t_min - 0.5,
            t_max + 0.5,
            num_time_bins + 1,
        )
    else:
        edges = np.linspace(
            t_min,
            t_max,
            num_time_bins + 1,
        )

    def assign_bins(frame):
        result = frame.copy()

        result["time_bin"] = np.searchsorted(
            edges[1:-1],
            result["timestamp"].to_numpy(dtype=np.float64),
            side="right",
        )

        result["time_bin"] = result["time_bin"].clip(
            0,
            num_time_bins - 1,
        )

        return result

    return assign_bins(train), assign_bins(all_data), edges


def prepare_ciao(
    raw_file="data/Ciao/ratings.csv",
    out_dir="data/Ciao",
    min_user=5,
    min_item=5,
    num_time_bins=100,
    seed=42,
    popularity_quantile=0.80,
):
    """Prepare Ciao data, chronological splits and temporal features."""

    raw_file = Path(raw_file)
    out_dir = Path(out_dir)

    if not raw_file.exists():
        raise FileNotFoundError(
            f"Ciao raw ratings file not found: {raw_file}"
        )

    if num_time_bins < 1:
        raise ValueError("num_time_bins must be positive.")

    if not 0.0 < popularity_quantile < 1.0:
        raise ValueError(
            "popularity_quantile must be between 0 and 1."
        )

    df = pd.read_csv(
        raw_file,
        header=None,
        names=COLUMNS,
    )

    df = df.dropna(
        subset=["user", "item", "rating", "timestamp"]
    ).copy()

    df["timestamp"] = (
        pd.to_datetime(
            df["timestamp"],
            format="%d.%m.%Y",
            errors="coerce",
            utc=True,
        )
        .astype("int64")
        .floordiv(10**9)
    )

    df.loc[df["timestamp"] < 0, "timestamp"] = np.nan

    df.loc[df["timestamp"] < 0, "timestamp"] = np.nan
    df["rating"] = pd.to_numeric(
        df["rating"], errors="coerce"
    )

    df = df.dropna(
        subset=["timestamp", "rating"]
    ).copy()

    if df.empty:
        raise ValueError("No valid interactions found.")

    # Apply iterative k-core filtering.
    df = _k_core(
        df,
        min_user=min_user,
        min_item=min_item,
    )

    if df.empty:
        raise ValueError(
            "No interactions remain after k-core filtering."
        )

    # Create stable integer user/item IDs.
    raw_users = sorted(df["user"].astype(str).unique())
    raw_items = sorted(df["item"].astype(str).unique())

    user_mapping = {
        raw_id: idx for idx, raw_id in enumerate(raw_users)
    }

    item_mapping = {
        raw_id: idx for idx, raw_id in enumerate(raw_items)
    }

    df["user"] = (
        df["user"].astype(str)
        .map(user_mapping)
        .astype(np.int64)
    )

    df["item"] = (
        df["item"].astype(str)
        .map(item_mapping)
        .astype(np.int64)
    )

    df = df.sort_values(
        ["timestamp", "user", "item"]
    ).reset_index(drop=True)

    # Chronological split.
    train, val, test = _chronological_split(df)

    # Retain only users and items represented in training.
    train_users = set(train["user"].unique())
    train_items = set(train["item"].unique())

    val = val[
        val["user"].isin(train_users)
        & val["item"].isin(train_items)
    ].copy()

    test = test[
        test["user"].isin(train_users)
        & test["item"].isin(train_items)
    ].copy()

    if train.empty:
        raise ValueError("Training split is empty.")

    # Construct temporal bins over the training period.
    train, df, time_bin_edges = _assign_training_time_bins(
        train,
        df,
        num_time_bins,
    )

    # Assign validation/test interactions to the same bin boundaries.
    def assign_holdout_bins(frame):
        frame = frame.copy()

        frame["time_bin"] = np.searchsorted(
            time_bin_edges[1:-1],
            frame["timestamp"].to_numpy(dtype=np.float64),
            side="right",
        )

        frame["time_bin"] = frame["time_bin"].clip(
            0,
            num_time_bins - 1,
        )

        return frame

    val = assign_holdout_bins(val)
    test = assign_holdout_bins(test)

    num_users = len(user_mapping)
    num_items = len(item_mapping)

    # Compute popularity and EPP exclusively from training interactions.
    popularity = compute_local_popularity(
        train,
        num_time_bins=num_time_bins,
        num_items=num_items,
    )

    epp = compute_evolving_personal_popularity(
        train,
        item_popularity=popularity,
        num_users=num_users,
        popularity_quantile=popularity_quantile,
        num_time_bins=num_time_bins,
    )

    # Save processed data.
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, part in [
        ("all_data", df),
        ("train_data", train),
        ("val_data", val),
        ("test_data", test),
    ]:
        part.to_csv(
            out_dir / f"{name}.csv",
            sep="\t",
            index=False,
        )

    pd.DataFrame(
        {
            "raw_user": list(user_mapping.keys()),
            "user": list(user_mapping.values()),
        }
    ).to_csv(
        out_dir / "user_mapping.csv",
        index=False,
    )

    pd.DataFrame(
        {
            "raw_item": list(item_mapping.keys()),
            "item": list(item_mapping.values()),
        }
    ).to_csv(
        out_dir / "item_mapping.csv",
        index=False,
    )

    np.save(
        out_dir / "item_local_popularity.npy",
        popularity,
    )

    np.save(
        out_dir / "user_epp.npy",
        epp,
    )

    np.save(
        out_dir / "time_bin_edges.npy",
        time_bin_edges,
    )

    print(
        f"Prepared Ciao: users={num_users}, "
        f"items={num_items}, interactions={len(df)}"
    )

    print(
        f"Splits: train={len(train)}, "
        f"validation={len(val)}, test={len(test)}"
    )

    print(
        f"Training timeline: {train['timestamp'].min()} "
        f"to {train['timestamp'].max()}"
    )

    return train, val, test


if __name__ == "__main__":
    from config import Config

    config = Config()

    prepare_ciao(
        raw_file=config.raw_file,
        out_dir=config.data_dir,
        min_user=config.min_user_interactions,
        min_item=config.min_item_interactions,
        num_time_bins=config.num_time_bins,
        seed=config.seed,
        popularity_quantile=config.high_popularity_quantile,
    )
