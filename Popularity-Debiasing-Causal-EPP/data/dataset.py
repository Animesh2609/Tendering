
"""Training dataset and split loader for CausalEPP."""

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset


class PairwiseTrainDataset(Dataset):
    """Generate positive-negative interaction pairs for BPR training."""

    def __init__(self, interactions, num_items, seed=42, negative_candidates=None):
        self.df = interactions.reset_index(drop=True).copy()
        self.num_items = int(num_items)

        if self.num_items <= 0:
            raise ValueError("num_items must be positive.")

        if self.df.empty:
            raise ValueError("Training interactions cannot be empty.")

        required = {"user", "item", "timestamp"}
        missing = required - set(self.df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        if not self.df["item"].between(0, self.num_items - 1).all():
            raise ValueError("Item IDs must be in [0, num_items - 1].")

        self.rng = np.random.default_rng(seed)

        # All training positives are excluded from negative sampling.
        self.user_pos = (
            self.df.groupby("user")["item"]
            .apply(lambda items: set(items.astype(int)))
            .to_dict()
        )

        self.user_neg_candidates = {
            int(user): np.setdiff1d(
                np.arange(self.num_items, dtype=np.int64),
                np.fromiter(positives, dtype=np.int64),
                assume_unique=False,
            )
            for user, positives in self.user_pos.items()
        }

        if negative_candidates is not None:
            for user, candidates in negative_candidates.items():
                user = int(user)
                positives = self.user_pos.get(user, set())
                valid_candidates = np.setdiff1d(
                    np.asarray(list(candidates), dtype=np.int64),
                    np.fromiter(positives, dtype=np.int64),
                    assume_unique=False,
                )
                if valid_candidates.size:
                    self.user_neg_candidates[user] = valid_candidates

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]

        user = int(row["user"])
        positive_item = int(row["item"])

        candidates = self.user_neg_candidates[user]

        # Users who interacted with every item have no valid negative.
        # Fail explicitly rather than silently generating a false negative.
        if candidates.size == 0:
            raise ValueError(
                f"User {user} has interacted with every item; "
                "cannot sample a valid negative."
            )

        negative_item = int(self.rng.choice(candidates))

        return (
            torch.tensor(user, dtype=torch.long),
            torch.tensor(positive_item, dtype=torch.long),
            torch.tensor(negative_item, dtype=torch.long),
            torch.tensor(float(row["timestamp"]), dtype=torch.float32),
        )


def load_splits(data_dir):
    """Load the preprocessed training, validation, and test splits."""
    data_dir = Path(data_dir)

    splits = []
    for name in ("train", "val", "test"):
        path = data_dir / f"{name}_data.csv"

        if not path.exists():
            raise FileNotFoundError(f"Dataset split not found: {path}")

        split = pd.read_csv(path, sep="\t")

        required = {"user", "item", "timestamp"}
        missing = required - set(split.columns)
        if missing:
            raise ValueError(
                f"{path} is missing required columns: {sorted(missing)}"
            )

        splits.append(split)

    return tuple(splits)
