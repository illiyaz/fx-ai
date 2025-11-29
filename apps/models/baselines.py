from __future__ import annotations
import math
import pandas as pd
import numpy as np
from apps.common.clickhouse_client import query_df





def _sigmoid(x: float, k: float = 50.0) -> float:
    # squashes small bps moves into ~0.5; k controls steepness
    return 1.0 / (1.0 + math.exp(-k * x))

def latest_features(pair: str, n: int = 60) -> pd.DataFrame:
    sql = f"""
        SELECT *
        FROM fxai.features_1m
        WHERE pair = '{pair}'
        ORDER BY ts DESC
        LIMIT {n}
    """
    df = query_df(sql)
    return df.sort_values("ts")

def forecast_rolling_mean(pair: str, horizon: str = "4h") -> dict:
    """
    Simple baseline:
    - use mean of 1m returns over last 20 mins as drift
    - scale to expected delta in bps for the next hour (or chosen horizon)
    - CI from recent vol
    """
    df = latest_features(pair, 120)
    if df.empty or len(df) < 25:
        # fallback neutral
        return {
            "pair": pair, "horizon": horizon, "prob_up": 0.5,
            "expected_delta_bps": 0.0, "range": {"p10": -5.0, "p90": 5.0},
            "confidence": 0.0, "recommendation": "PARTIAL",
            "explanation": ["insufficient features; neutral"],
            "model_id": "rollmean_v0"
        }

    # mean drift of 1m returns (last 20)
    drift_1m = float(df["ret_1m"].tail(20).mean())
    vol_1m = float(df["ret_1m"].tail(20).std() or 0.0)

    # map horizon -> minutes
    H = {"1h":60, "2h":120, "4h":240, "30m":30}.get(horizon, 240)

    exp_ret = drift_1m * H  # linear scaling (rough)
    exp_bps = exp_ret * 10_000.0

    # crude CI from vol * sqrt(H)
    ci = 1.2816 * vol_1m * (H ** 0.5) * 10_000.0  # ~90% one-sided

    prob_up = _sigmoid(exp_ret)
    recommendation = "WAIT" if exp_bps > 4 else ("NOW" if exp_bps < -4 else "PARTIAL")

    return {
        "pair": pair,
        "horizon": horizon,
        "prob_up": round(prob_up, 3),
        "expected_delta_bps": round(exp_bps, 2),
        "range": {"p10": round(-ci, 2), "p90": round(ci, 2)},
        "confidence": float(min(1.0, max(0.0, abs(exp_ret) / (vol_1m + 1e-6)))),
        "recommendation": recommendation,
        "explanation": [f"drift_1m={drift_1m:.6f}", f"vol_1m={vol_1m:.6f}", f"H={H}m"],
        "model_id": "rollmean_v0",
    }



def predict_drift(features: pd.DataFrame):
    last_ret = float(features["ret_1m"].iloc[-1])
    return {"prob_up": float(last_ret > 0), "exp_delta_bps": float(last_ret * 10000)}



def _finite(x: float, default: float = 0.0) -> float:
    try:
        xf = float(x)
        return xf if math.isfinite(xf) else default
    except Exception:
        return default

def predict_rolling_mean(features: pd.DataFrame, window: int = 20):
    """
    Robust rolling-mean baseline:
    - uses mean of last `window` 1m returns
    - guards against NaN/inf and empty windows
    - returns plain Python floats (JSON-safe)
    """
    if features is None or features.empty or "ret_1m" not in features.columns:
        return {"prob_up": 0.5, "exp_delta_bps": 0.0}

    tail = features["ret_1m"].astype(float).tail(window).replace([np.inf, -np.inf], np.nan).dropna()
    if tail.empty:
        mean_ret = 0.0
    else:
        mean_ret = float(tail.mean())

    mean_ret = _finite(mean_ret, 0.0)
    exp_bps = _finite(mean_ret * 10000.0, 0.0)

    # a soft probability from the expected return (kept simple & JSON-safe)
    k = 50.0  # slope
    prob_up = 1.0 / (1.0 + math.exp(-k * mean_ret))  # in (0,1)
    prob_up = _finite(prob_up, 0.5)

    return {"prob_up": float(prob_up), "exp_delta_bps": float(exp_bps)}