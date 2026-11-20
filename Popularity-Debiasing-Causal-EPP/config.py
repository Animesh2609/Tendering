"""Configuration for a paper-faithful CausalEPP implementation."""
from dataclasses import dataclass

@dataclass
class Config:
    dataset: str = "Ciao"
    data_dir: str = "data/Ciao"
    raw_file: str = "data/Ciao/ratings.csv"
    seed: int = 42
    min_user_interactions: int = 5
    min_item_interactions: int = 5
    num_time_bins: int = 100
    high_popularity_quantile: float = 0.80
    embedding_dim: int = 64
    lightgcn_layers: int = 3
    mlp_hidden_dim: int = 32
    alpha: float = 0.5
    quality_loss_weight: float = 0.2
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    batch_size: int = 2048
    epochs: int = 100
    eval_k: int = 20
    moving_average_window: int = 10
    forecast_method: str = "moving_average"
    forecast_level_alpha: float = 0.3
    forecast_trend_beta: float = 0.1
    item_forecast_horizon: float = 5.0
    user_forecast_horizon: float = 10.0
    enable_popularity_calibration: bool = False
    calibration_candidate_pool: int = 150
    calibration_lambda_grid: tuple = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
    use_llm_matching: bool = False
    llm_model_id: str = "Qwen/Qwen3-0.6B"
    llm_device: str = "auto"
    llm_candidate_pool: int = 50
    llm_history_length: int = 20
    device: str = "auto"
    output_dir: str = "outputs/Ciao"
