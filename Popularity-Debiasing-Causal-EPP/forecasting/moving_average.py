
"""Moving-average forecasting for CausalEPP (Equations 2, 14 and 15)."""

import numpy as np


def moving_average(series, window=10):
    """
    Calculate the trailing moving average.

    Equation (2): Moving average over the most recent window.
    """
    x = np.asarray(series, dtype=np.float64).reshape(-1)

    if x.size == 0:
        return np.array([], dtype=np.float64)

    window = max(1, min(int(window), len(x)))

    kernel = np.ones(window, dtype=np.float64) / window

    return np.convolve(x, kernel, mode="valid")


def estimate_trend(series, window=10):
    """
    Estimate the latest trend using the final two moving-average values.

    Returns the change in moving average per time step.
    """
    ma = moving_average(series, window)

    if ma.size < 2:
        return 0.0

    return float(ma[-1] - ma[-2])


def moving_average_forecast(series, window=10, horizon=1.0):
    """
    Forecast the next value using the latest moving-average trend.

    p_i* = p_i^T + (d MA_T(p_i) / dt) * Delta_T^i

    s_u* = s_u^T + (d MA_T(s_u) / dt) * Delta_T^u
    """
    x = np.asarray(series, dtype=np.float64).reshape(-1)

    if x.size == 0:
        return 0.0

    if horizon < 0:
        raise ValueError("Forecast horizon cannot be negative.")

    if not np.all(np.isfinite(x)):
        raise ValueError("Series contains NaN or infinite values.")

    trend = estimate_trend(x, window)

    forecast = float(x[-1]) + trend * float(horizon)

    # Popularity and EPP are proportions.
    return float(np.clip(forecast, 0.0, 1.0))


def holt_forecast(series, horizon=1.0, level_alpha=0.3, trend_beta=0.1):
    """Forecast with Holt's double exponential smoothing.

    The level and trend are updated with exponentially decaying weights, so
    recent observations affect the forecast more than older observations.
    """
    x = np.asarray(series, dtype=np.float64).reshape(-1)

    if x.size == 0:
        return 0.0
    if horizon < 0:
        raise ValueError("Forecast horizon cannot be negative.")
    if not 0.0 < level_alpha <= 1.0:
        raise ValueError("level_alpha must be in (0, 1].")
    if not 0.0 < trend_beta <= 1.0:
        raise ValueError("trend_beta must be in (0, 1].")
    if not np.all(np.isfinite(x)):
        raise ValueError("Series contains NaN or infinite values.")

    level = float(x[0])
    trend = float(x[1] - x[0]) if x.size > 1 else 0.0

    for value in x[1:]:
        previous_level = level
        level = level_alpha * float(value) + (1.0 - level_alpha) * (level + trend)
        trend = trend_beta * (level - previous_level) + (1.0 - trend_beta) * trend

    return float(np.clip(level + float(horizon) * trend, 0.0, 1.0))


def forecast_all(
    popularity_history,
    epp_history,
    window=10,
    item_horizon=1.0,
    user_horizon=1.0,
    method="moving_average",
    level_alpha=0.3,
    trend_beta=0.1,
):
    """
    Forecast item popularity and user EPP independently.

    Args:
        popularity_history: (time_steps, num_items)
        epp_history: (time_steps, num_users)

    Returns:
        item_popularity_star: (num_items,)
        user_epp_star: (num_users,)
    """
    popularity = np.asarray(popularity_history, dtype=np.float64)
    epp = np.asarray(epp_history, dtype=np.float64)

    if popularity.ndim != 2 or epp.ndim != 2:
        raise ValueError(
            "Both histories must be 2D arrays: (time_steps, entities)."
        )

    if popularity.shape[0] != epp.shape[0]:
        raise ValueError(
            "Popularity and EPP histories must have the same number of time steps."
        )

    if window < 1:
        raise ValueError("Moving-average window must be positive.")

    if method == "moving_average":
        forecast = lambda series, horizon: moving_average_forecast(
            series, window=window, horizon=horizon
        )
    elif method == "holt":
        forecast = lambda series, horizon: holt_forecast(
            series,
            horizon=horizon,
            level_alpha=level_alpha,
            trend_beta=trend_beta,
        )
    else:
        raise ValueError("method must be 'moving_average' or 'holt'.")

    item_popularity_star = np.array(
        [
            forecast(popularity[:, item], item_horizon)
            for item in range(popularity.shape[1])
        ],
        dtype=np.float32,
    )

    user_epp_star = np.array(
        [
            forecast(epp[:, user], user_horizon)
            for user in range(epp.shape[1])
        ],
        dtype=np.float32,
    )

    return item_popularity_star, user_epp_star
