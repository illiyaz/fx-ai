from __future__ import annotations
import os
from typing import Any, Dict
import joblib
import pandas as pd
from apps.common.clickhouse_client import query_df

MODELS_DIR = os.getenv("MODELS_DIR", "models")


def latest_model_row(horizon: str) -> Dict[str, Any] | None:
    df = query_df(
        f"""
        SELECT model_id, created_at, algo, horizon, features, train_start, train_end, metrics_json
        FROM fxai.models
        WHERE horizon = '{horizon}'
        ORDER BY created_at DESC
        LIMIT 1
        """
    )
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def load_model_by_id(model_id: str):
    path = os.path.join(MODELS_DIR, f"{model_id}.pkl")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return joblib.load(path)


class SkPredictor:
    """Wrap a sklearn-style classifier with a stable predict() interface.

    Expects the saved bundle to be a dict with keys:
      - "model": the fitted estimator (supports predict_proba)
      - "features": list of feature names expected in the input
    """

    def __init__(self, model, feature_names):
        self.model = model
        self.feature_names = list(feature_names)

    def predict(self, feats: pd.DataFrame) -> dict:
        if feats is None or feats.empty:
            return {"prob_up": 0.5, "expected_delta_bps": 0.0}
        X = feats[self.feature_names].tail(1).values
        prob_up = float(self.model.predict_proba(X)[0, 1])
        # Use the recent mean return magnitude, but sign it by model confidence
        # signal = (2*prob_up - 1) in [-1, 1]
        base_ret = float(feats["ret_1m"].tail(20).mean() or 0.0)
        exp_bps = (2.0 * prob_up - 1.0) * base_ret * 10_000.0

        return {"prob_up": prob_up, "expected_delta_bps": exp_bps}