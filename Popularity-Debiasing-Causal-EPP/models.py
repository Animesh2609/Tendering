
"""LightGCN, CausalEPP, and loss functions."""

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F


class LightGCN(nn.Module):
    def __init__(self, num_users, num_items, dim=64, n_layers=3):
        super().__init__()

        self.num_users = num_users
        self.num_items = num_items
        self.n_layers = n_layers

        self.user_embedding = nn.Embedding(num_users, dim)
        self.item_embedding = nn.Embedding(num_items, dim)

        nn.init.normal_(self.user_embedding.weight, std=0.1)
        nn.init.normal_(self.item_embedding.weight, std=0.1)

    def propagate(self, norm_adj):
        embeddings = torch.cat(
            [self.user_embedding.weight, self.item_embedding.weight],
            dim=0,
        )

        all_embeddings = [embeddings]

        for _ in range(self.n_layers):
            embeddings = torch.sparse.mm(norm_adj, embeddings)
            all_embeddings.append(embeddings)

        final_embeddings = torch.stack(all_embeddings, dim=0).mean(dim=0)

        return (
            final_embeddings[:self.num_users],
            final_embeddings[self.num_users:],
        )

    @staticmethod
    def normalized_adjacency(train_df, num_users, num_items, device):
        """Create symmetric normalized bipartite adjacency."""
        users = train_df["user"].to_numpy(dtype=np.int64)
        items = train_df["item"].to_numpy(dtype=np.int64) + num_users

        edges = np.unique(
            np.concatenate(
                [
                    np.column_stack([users, items]),
                    np.column_stack([items, users]),
                ],
                axis=0,
            ),
            axis=0,
        )

        rows, cols = edges[:, 0], edges[:, 1]
        num_nodes = num_users + num_items

        degrees = np.bincount(rows, minlength=num_nodes).astype(np.float32)
        values = 1.0 / np.sqrt(
            np.maximum(degrees[rows], 1.0)
            * np.maximum(degrees[cols], 1.0)
        )

        indices = torch.tensor(
            np.stack([rows, cols]),
            dtype=torch.long,
            device=device,
        )
        values = torch.tensor(values, dtype=torch.float32, device=device)

        return torch.sparse_coo_tensor(
            indices,
            values,
            (num_nodes, num_nodes),
            device=device,
        ).coalesce()


class CausalEPP(nn.Module):
    def __init__(
        self,
        num_users,
        num_items,
        dim=64,
        n_layers=3,
        mlp_hidden=32,
        alpha=5.0,
        q_init=0.0,
    ):
        super().__init__()

        self.num_users = num_users
        self.num_items = num_items
        self.alpha = alpha

        self.lightgcn = LightGCN(
            num_users, num_items, dim, n_layers
        )

        # Equation (6): learnable item-quality scalar q_i.
        self.q = nn.Parameter(
            torch.full((num_items,), float(q_init))
        )

        # Equation (7): item-specific mapping MLP(i).
        self.item_mlp = nn.Sequential(
            nn.Linear(dim, mlp_hidden),
            nn.ReLU(),
            nn.Linear(mlp_hidden, 1),
        )

    def forward(
        self,
        users,
        items,
        norm_adj,
        user_epp_values,
        item_pop_values,
        matching_scores=None,
    ):
        """Compute recommendation scores using Equations (6)-(9)."""
        user_embeddings, item_embeddings = self.lightgcn.propagate(norm_adj)

        user_vectors = user_embeddings[users]
        item_vectors = item_embeddings[items]

        # Matching score m_ui.
        if matching_scores is None:
            matching = (user_vectors * item_vectors).sum(dim=-1)
        else:
            matching = matching_scores.to(
                device=item_vectors.device, dtype=item_vectors.dtype
            ).reshape(-1)

        s = user_epp_values.to(
            device=matching.device, dtype=matching.dtype
        ).clamp(0.0, 1.0)

        p = item_pop_values.to(
            device=matching.device, dtype=matching.dtype
        ).clamp(0.0, 1.0)

        # Conformity c_ui.
        item_mapping = self.item_mlp(item_vectors).squeeze(-1)
        conformity = (
            torch.exp(-self.alpha * torch.abs(s - p))
            * p
            * item_mapping
        )

        # Equation (6): tanh(q_i + c_ui) * Softplus(m_ui).
        return torch.tanh(self.q[items] + conformity) * F.softplus(matching)

    def quality_loss(self, item_i, item_j, global_counts):
        """Equation (10): pairwise quality ranking loss."""
        count_i = global_counts[item_i]
        count_j = global_counts[item_j]

        sign = torch.sign(count_i - count_j)
        quality_difference = self.q[item_i] - self.q[item_j]

        return F.softplus(-sign * quality_difference).mean()


# -------------------- Loss functions --------------------

def bpr_loss(pos_scores, neg_scores):
    """Equation (12): pairwise ranking loss."""
    return F.softplus(neg_scores - pos_scores).mean()


def quality_loss(model, item_i, item_j, global_counts):
    """Equation (10): wrapper for the model's quality loss."""
    return model.quality_loss(item_i, item_j, global_counts)


def total_loss(
    pos_scores,
    neg_scores,
    quality_loss_value=None,
    quality_loss_weight=0.1,
):
    """Equation (11): L = L_BPR + lambda * L_Q."""
    ranking_loss = bpr_loss(pos_scores, neg_scores)

    if quality_loss_value is None:
        return ranking_loss

    return ranking_loss + quality_loss_weight * quality_loss_value
