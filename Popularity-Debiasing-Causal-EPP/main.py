
import argparse
from datetime import datetime
from pathlib import Path
import re

from config import Config
from data.preprocess import prepare_ciao
from train import train


def main():
    parser = argparse.ArgumentParser(
        description="CausalEPP on Ciao + LightGCN"
    )

    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Preprocess data/Ciao/ratings.csv"
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--forecast-method",
        choices=("moving_average", "holt"),
        default=None,
        help="Forecasting method for item popularity and user EPP",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Evaluate popularity-calibrated re-ranking in addition to CausalEPP",
    )
    parser.add_argument(
        "--llm-baseline",
        action="store_true",
        help="Train CausalEPP with a local Hugging Face LLM score as m_ui",
    )

    args = parser.parse_args()
    config = Config()

    # Step 1: Update epochs if provided
    if args.epochs is not None:
        config.epochs = args.epochs
    if args.forecast_method is not None:
        config.forecast_method = args.forecast_method
    config.enable_popularity_calibration = args.calibrate
    config.use_llm_matching = args.llm_baseline

    run_time = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if args.llm_baseline:
        model_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", config.llm_model_id)
        run_label = f"causalepp_llm_{model_label}"
    else:
        run_label = f"causalepp_{config.forecast_method}"
        if config.enable_popularity_calibration:
            run_label += "_calibrated"
    config.output_dir = str(Path(config.output_dir) / f"{run_label}_{run_time}")

    # Step 2: Preprocess data if requested
    if args.preprocess:
        print("Starting preprocessing...")

        prepare_ciao(
            raw_file=config.raw_file,
            out_dir=config.data_dir,
            min_user=config.min_user_interactions,
            min_item=config.min_item_interactions,
            num_time_bins=config.num_time_bins,
            seed=config.seed,
            popularity_quantile=config.high_popularity_quantile
        )

        print("Preprocessing completed.")

    # Step 3: Train the model
    print("Starting CausalEPP training...")

    (
        model,
        test_metrics,
        global_popularity,
        expected_popularity
    ) = train(config)

    # Step 4: Display returned results
    print("\nTraining completed successfully!")

    print("\nTest metrics:")
    for metric, value in test_metrics.items():
        print(f"{metric}: {value}")

    print("\nGlobal item popularity:")
    print("Shape:", global_popularity.shape)
    print("First 10 values:", global_popularity[:10])

    print("\nExpected local popularity:")
    print("Shape:", expected_popularity.shape)
    print("First 10 values:", expected_popularity[:10])

    print("\nOutput directory:", config.output_dir)


if __name__ == "__main__":
    main()

