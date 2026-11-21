
"""Training pipeline for CausalEPP."""

from pathlib import Path
import json

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from data.dataset import PairwiseTrainDataset
from models import CausalEPP, LightGCN, total_loss
from evaluate import ranking_metrics, recommendation_examples
from forecasting.moving_average import forecast_all
from data.popularity import(
compute_global_popularity,
compute_expected_local_popularity)

def get_device(config):
    if config.device == "auto":
        return torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
    return torch.device(config.device)


def set_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def bin_indices(timestamps, edges):
    """Map timestamps to valid training time-bin indices."""
    timestamps = np.asarray(timestamps, dtype=np.float64)

    return np.clip(
        np.digitize(timestamps, edges[1:-1]),
        0,
        len(edges) - 2,
    )


def load_training_data(data_dir):
    """Load processed interactions and temporal features."""
    data_dir = Path(data_dir)

    train_df = pd.read_csv(
        data_dir / "train_data.csv", sep="\t"
    )
    val_df = pd.read_csv(
        data_dir / "val_data.csv", sep="\t"
    )
    test_df = pd.read_csv(
        data_dir / "test_data.csv", sep="\t"
    )

    edges = np.load(data_dir / "time_bin_edges.npy")
    popularity_history = np.load(
        data_dir / "item_local_popularity.npy"
    )
    epp_history = np.load(
        data_dir / "user_epp.npy"
    )

    if train_df.empty:
        raise ValueError("Training dataset is empty.")

    num_users = int(
        max(
            train_df["user"].max(),
            val_df["user"].max() if not val_df.empty else 0,
            test_df["user"].max() if not test_df.empty else 0,
        )
    ) + 1

    num_items = int(
        max(
            train_df["item"].max(),
            val_df["item"].max() if not val_df.empty else 0,
            test_df["item"].max() if not test_df.empty else 0,
        )
    ) + 1

    if popularity_history.ndim != 2 or epp_history.ndim != 2:
        raise ValueError("Popularity and EPP histories must be 2D arrays.")

    if popularity_history.shape[0] != epp_history.shape[0]:
        raise ValueError(
            "Popularity and EPP histories must have the same time dimension."
        )

    if popularity_history.shape[0] != len(edges) - 1:
        raise ValueError(
            "Temporal feature dimensions do not match time_bin_edges."
        )

    # Align feature dimensions with model ID dimensions.
    popularity_history = np.pad(
        popularity_history,
        (
            (0, 0),
            (0, max(0, num_items - popularity_history.shape[1])),
        ),
    )[:, :num_items]

    epp_history = np.pad(
        epp_history,
        (
            (0, 0),
            (0, max(0, num_users - epp_history.shape[1])),
        ),
    )[:, :num_users]

    # Find the last time bin that actually contains training interactions.
    active_bins = np.flatnonzero(
        popularity_history.sum(axis=1) > 0
    )

    if active_bins.size == 0:
        raise ValueError(
            "No non-empty training popularity bins were found."
        )

    # Remove only trailing empty bins. Internal empty bins remain because
    # they represent genuine periods without observed interactions.
    history_end = int(active_bins[-1]) + 1

    popularity_history = popularity_history[:history_end]
    epp_history = epp_history[:history_end]
    edges = edges[:history_end + 1]

    return (
        train_df,
        val_df,
        test_df,
        edges,
        popularity_history,
        epp_history,
        num_users,
        num_items,
    )


def train(config):
    set_seed(config.seed)

    device = get_device(config)

    data_dir = Path(config.data_dir)
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    (
        train_df,
        val_df,
        test_df,
        edges,
        popularity_history,
        epp_history,
        num_users,
        num_items,
    )= load_training_data(data_dir)
        # Global item popularity
    global_counts = compute_global_popularity(
        train_df,
        num_items=num_items
    )

    global_counts = torch.tensor(
        global_counts,
        dtype=torch.float32,
        device=device
    )

    # Expected local popularity
    active_bins = popularity_history.sum(axis=1) > 0

    mean_popularity = compute_expected_local_popularity(
        popularity_history[active_bins]
    )

    mean_popularity = torch.tensor(
        mean_popularity,
        dtype=torch.float32,
        device=device
    )

    epp_tensor = torch.tensor(
        epp_history,
        dtype=torch.float32,
        device=device,
    )

    llm_score_cache = None
    negative_candidates = None
    item_names = {}
    if config.use_llm_matching:
        from teammate_v2.llm_baseline import build_llm_matching_scores

        (
            llm_score_cache,
            _llm_candidate_cache,
            negative_candidates,
            item_names,
        ) = build_llm_matching_scores(
            config,
            train_df,
            val_df,
            test_df,
            num_items,
        )
        if device.type == "cuda":
            torch.cuda.empty_cache()

    # Build LightGCN graph from training interactions only.
    norm_adj = LightGCN.normalized_adjacency(
        train_df,
        num_users,
        num_items,
        device,
    )

    model = CausalEPP(
        num_users=num_users,
        num_items=num_items,
        dim=config.embedding_dim,
        n_layers=config.lightgcn_layers,
        mlp_hidden=config.mlp_hidden_dim,
        alpha=config.alpha,
        q_init=0.0,
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    train_dataset = PairwiseTrainDataset(
        train_df,
        num_items,
        seed=config.seed,
        negative_candidates=negative_candidates,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=0,
    )

    # Forecast only from the observed training history.
    item_popularity_star, user_epp_star = forecast_all(
        popularity_history,
        epp_history,
        window=config.moving_average_window,
        item_horizon=config.item_forecast_horizon,
        user_horizon=config.user_forecast_horizon,
        method=config.forecast_method,
        level_alpha=config.forecast_level_alpha,
        trend_beta=config.forecast_trend_beta,
    )

    p_star = torch.tensor(
        item_popularity_star,
        dtype=torch.float32,
        device=device,
    )

    s_star = torch.tensor(
        user_epp_star,
        dtype=torch.float32,
        device=device,
    )

    best_score = -float("inf")
    best_path = output_dir / "causalepp_ciao.pt"

    # -------------------- Training --------------------

    for epoch in range(1, config.epochs + 1):
        model.train()

        epoch_loss = 0.0
        num_samples = 0

        for users, positive_items, negative_items, timestamps in train_loader:

            users = users.to(device).long()
            positive_items = positive_items.to(device).long()
            negative_items = negative_items.to(device).long()

            bins = torch.tensor(
                bin_indices(timestamps.numpy(), edges),
                dtype=torch.long,
                device=device,
            )

            # User EPP at the interaction time.
            user_epp = epp_tensor[bins, users]

            if llm_score_cache is not None:
                batch_users = users.cpu().tolist()
                positive_ids = positive_items.cpu().tolist()
                negative_ids = negative_items.cpu().tolist()
                positive_matching = torch.tensor(
                    [llm_score_cache[int(u)][int(i)] for u, i in zip(batch_users, positive_ids)],
                    dtype=torch.float32,
                    device=device,
                )
                negative_matching = torch.tensor(
                    [llm_score_cache[int(u)][int(i)] for u, i in zip(batch_users, negative_ids)],
                    dtype=torch.float32,
                    device=device,
                )
            else:
                positive_matching = None
                negative_matching = None

            positive_scores = model(
                users,
                positive_items,
                norm_adj,
                user_epp,
                mean_popularity[positive_items],
                matching_scores=positive_matching,
            )

            negative_scores = model(
                users,
                negative_items,
                norm_adj,
                user_epp,
                mean_popularity[negative_items],
                matching_scores=negative_matching,
            )

            # Equation (10): quality supervision.
            q_loss = model.quality_loss(
                positive_items,
                negative_items,
                global_counts,
            )

            # Equation (11): total objective.
            loss = total_loss(
                positive_scores,
                negative_scores,
                quality_loss_value=q_loss,
                quality_loss_weight=config.quality_loss_weight,
            )

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.detach().item() * len(users)
            num_samples += len(users)

        average_loss = epoch_loss / max(num_samples, 1)

        # -------------------- Validation --------------------

        if not val_df.empty:
            model.eval()

            with torch.no_grad():
                val_metrics = ranking_metrics(
                    model,
                    norm_adj,
                    train_df,
                    val_df,
                    num_users,
                    num_items,
                    p_star,
                    s_star,
                    config.eval_k,
                    device,
                    matching_scores_by_user=llm_score_cache,
                )

            validation_score = val_metrics["NDCG@K"]

        else:
            val_metrics = {}
            validation_score = -average_loss

        print(
            f"Epoch {epoch:03d} | "
            f"Loss: {average_loss:.5f} | "
            f"Validation: {val_metrics}"
        )

        if validation_score > best_score:
            best_score = validation_score

            torch.save(
                {
                    "model": model.state_dict(),
                    "num_users": num_users,
                    "num_items": num_items,
                    "config": config.__dict__,
                    "best_validation_score": best_score,
                },
                best_path,
            )

    # -------------------- Testing --------------------

    checkpoint = torch.load(
        best_path,
        map_location=device,
        weights_only=False,
    )

    model.load_state_dict(checkpoint["model"])
    model.eval()

    test_history = pd.concat([train_df, val_df], ignore_index=True)
    if not test_df.empty:
        with torch.no_grad():
            # Include both training and validation interactions
            # when excluding previously seen items during test evaluation.
            test_metrics = ranking_metrics(
                model,
                norm_adj,
                test_history,
                test_df,
                num_users,
                num_items,
                p_star,
                s_star,
                config.eval_k,
                device,
                matching_scores_by_user=llm_score_cache,
            )
    else:
        test_metrics = {}

    if not test_df.empty:
        if not item_names:
            item_mapping_path = data_dir / "item_mapping.csv"
            if item_mapping_path.exists():
                item_mapping = pd.read_csv(item_mapping_path)
                if {"item", "raw_item"}.issubset(item_mapping.columns):
                    item_names = dict(zip(
                        item_mapping["item"].astype(int),
                        item_mapping["raw_item"].astype(str),
                    ))
        examples = recommendation_examples(
            model,
            norm_adj,
            test_history,
            test_df,
            num_users,
            num_items,
            p_star,
            s_star,
            config.eval_k,
            device,
            item_names=item_names,
            max_users=5,
            matching_scores_by_user=llm_score_cache,
        )
        examples["run_settings"] = {
            "forecast_method": config.forecast_method,
            "popularity_calibration_enabled": config.enable_popularity_calibration,
            "checkpoint": "best validation NDCG",
            "recommendation_list": "base CausalEPP ranking before optional calibration",
        }
        if config.use_llm_matching:
            examples["run_settings"].update({
                "matching_score_source": "local Hugging Face model in CausalEPP m_ui term",
                "llm_model_id": config.llm_model_id,
                "llm_candidate_pool": config.llm_candidate_pool,
            })
        examples_path = output_dir / "recommendation_examples.json"
        examples_path.write_text(json.dumps(examples, indent=2))
        print("Example recommendations saved at:", examples_path)

    if config.enable_popularity_calibration and not val_df.empty and not test_df.empty:
        from teammate_v2.calibration import fit_group_lambdas, calibrated_ranking_metrics

        global_counts_array = global_counts.detach().cpu().numpy()
        user_groups = fit_group_lambdas(
            model,
            norm_adj,
            train_df,
            val_df,
            num_users,
            num_items,
            p_star,
            s_star,
            global_counts_array,
            config.eval_k,
            config.calibration_candidate_pool,
            config.calibration_lambda_grid,
            device,
            matching_scores_by_user=llm_score_cache,
        )
        test_history = pd.concat([train_df, val_df], ignore_index=True)
        calibrated_metrics = calibrated_ranking_metrics(
            model,
            norm_adj,
            test_history,
            test_df,
            num_users,
            num_items,
            p_star,
            s_star,
            global_counts_array,
            config.eval_k,
            config.calibration_candidate_pool,
            user_groups["lambdas"],
            user_groups["thresholds"],
            device,
            matching_scores_by_user=llm_score_cache,
            group_assignments=user_groups["user_groups"],
        )
        recommendation_comparison = calibrated_metrics.pop(
            "recommendation_comparison"
        )
        (output_dir / "calibration_lambdas.json").write_text(json.dumps({
            "lambdas": user_groups["lambdas"],
            "thresholds": user_groups["thresholds"],
            "user_groups": user_groups["user_groups"],
        }, indent=2))
        (output_dir / "calibration_lambda_diagnostics.json").write_text(
            json.dumps(user_groups["diagnostics"], indent=2)
        )
        (output_dir / "popularity_calibrated_test_metrics.json").write_text(
            json.dumps(calibrated_metrics, indent=2)
        )
        comparison_path = output_dir / "calibration_recommendation_comparison.json"
        comparison_path.write_text(json.dumps(recommendation_comparison, indent=2))
        print("\nPopularity-calibrated test metrics:", calibrated_metrics)
        print("Calibration lambdas:", user_groups["lambdas"])
        print("\nRecommendation-list comparison:")
        print("CP_H vs Original:", recommendation_comparison[
            "comparison_to_original_CausalEPP"]["CP_H"])
        print("CP_Im vs Original:", recommendation_comparison[
            "comparison_to_original_CausalEPP"]["CP_Im"])
        print("CP_H vs CP_Im:", recommendation_comparison["CP_H_vs_CP_Im"])
        print(
            "CP_H and CP_Im identical lists:",
            recommendation_comparison["CP_H_and_CP_Im_identical"],
        )
        print("Recommendation lists saved at:", comparison_path)

    metrics_path = output_dir / "test_metrics.json"

    metrics_path.write_text(
        json.dumps(test_metrics, indent=2)
    )

    print("\nFinal Test Metrics:", test_metrics)
    print("Best checkpoint saved at:", best_path)
    # Save global popularity and expected local popularity
    np.save(
        output_dir / "global_item_counts.npy",
        global_counts.detach().cpu().numpy()
    )
    np.save(
        output_dir / "expected_item_popularity.npy",
        mean_popularity.detach().cpu().numpy()
    )
    print("Global popularity saved successfully.")
    print("Expected local popularity saved successfully.")
    
    return (
        model,
        test_metrics,
        global_counts.detach().cpu().numpy(),
        mean_popularity.detach().cpu().numpy()
    )


if __name__ == "__main__":
    from config import Config

    config = Config()
    train(config)