from __future__ import annotations
import os
import json
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, brier_score_loss
from lightgbm import LGBMClassifier
import joblib

from apps.common.clickhouse_client import query_df, insert_rows
from apps.features.labels import fetch_bars, label_future_ret_from_bars

MODELS_DIR = os.getenv("MODELS_DIR", "models")

FEATURE_SET = [
    "ret_1m", "ret_5m", "ret_15m", "vol_5m", "vol_15m",
    "sma_5", "sma_15", "momentum_15m", "minutes_to_event", "is_high_importance"
]


def load_features(pair: str, lookback_hours: int) -> pd.DataFrame:
    sql = f"""
        SELECT ts, pair, {', '.join(FEATURE_SET)}
        FROM fxai.features_1m
        WHERE pair = '{pair}'
          AND ts >= now() - INTERVAL {lookback_hours} HOUR
        ORDER BY ts
    """
    return query_df(sql)


def train_classifier(df_feats: pd.DataFrame, df_labels: pd.DataFrame):
    # First, try exact ts alignment
    df = df_feats.merge(df_labels, on="ts", how="inner")

    if df.empty:
        # Fallback: allow up to 1 minute tolerance using merge_asof on sorted ts
        f = df_feats.sort_values("ts").reset_index(drop=True)
        l = df_labels.sort_values("ts").reset_index(drop=True)
        df = pd.merge_asof(f, l, on="ts", direction="nearest", tolerance=pd.Timedelta("1min"))

    df = df.dropna().reset_index(drop=True)
    if df.empty:
        # Helpful diagnostics
        def _span(x):
            if x is None or x.empty: return "<empty>"
            return f"{pd.to_datetime(x['ts'].min())} .. {pd.to_datetime(x['ts'].max())} (n={len(x)})"
        feats_span = _span(df_feats)
        labels_span = _span(df_labels)
        raise RuntimeError(f"No aligned feature-label rows; feats_span={feats_span}; labels_span={labels_span}")

    X = df[FEATURE_SET].values
    y = df["y_up"].values

    # Time-ordered split: last 20% as validation
    X_train, X_valid, y_train, y_valid = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    clf = LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=-1,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    clf.fit(X_train, y_train)

    # Metrics
    prob_valid = clf.predict_proba(X_valid)[:, 1]
    auc = float(roc_auc_score(y_valid, prob_valid)) if len(np.unique(y_valid)) > 1 else float("nan")
    brier = float(brier_score_loss(y_valid, prob_valid))

    metrics = {"auc": auc, "brier": brier, "n_valid": int(len(y_valid))}

    # Training window (for registry)
    t_start = pd.to_datetime(df["ts"].min())
    t_end = pd.to_datetime(df["ts"].max())

    return clf, metrics, t_start, t_end


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Train LightGBM classifier for FX-AI")
    ap.add_argument("--pair", default="USDINR")
    ap.add_argument("--horizon", default="4h", choices=["30m", "1h", "2h", "4h"])  # label horizon
    ap.add_argument("--lookback-hours", type=int, default=24 * 14)
    args = ap.parse_args()

    horizon_map = {"30m": 30, "1h": 60, "2h": 120, "4h": 240}
    H = horizon_map[args.horizon]

    # Load features & labels
    feats = load_features(args.pair, args.lookback_hours)
    bars = fetch_bars(args.pair, lookback_minutes=(args.lookback_hours + 24) * 60)
    labels = label_future_ret_from_bars(bars, H)

    clf, metrics, t_start, t_end = train_classifier(feats, labels)

    os.makedirs(MODELS_DIR, exist_ok=True)
    ts_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    model_id = f"lgbm_{args.pair}_{args.horizon}_{ts_id}"
    path = os.path.join(MODELS_DIR, f"{model_id}.pkl")
    joblib.dump({"model": clf, "features": FEATURE_SET}, path)

    # Registry row (created_at has default now())
    insert_rows(
        "fxai.models",
        [(
            model_id,
            "LightGBM",
            args.horizon,
            FEATURE_SET,
            t_start,
            t_end,
            json.dumps(metrics),
        )],
        [
            "model_id",
            "algo",
            "horizon",
            "features",
            "train_start",
            "train_end",
            "metrics_json",
        ],
    )

    print(f"Saved model: {path}")
    print(f"Registry -> fxai.models: id={model_id} horizon={args.horizon} metrics={metrics}")


if __name__ == "__main__":
    main()