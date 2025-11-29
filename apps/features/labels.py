from __future__ import annotations
import pandas as pd
from apps.common.clickhouse_client import query_df


def fetch_bars(pair: str, lookback_minutes: int = 7 * 24 * 60) -> pd.DataFrame:
    """Load 1m bars for a pair from ClickHouse."""
    sql = f"""
        SELECT ts, close
        FROM fxai.bars_1m
        WHERE pair = '{pair}'
          AND ts >= now() - INTERVAL {lookback_minutes} MINUTE
        ORDER BY ts
    """
    return query_df(sql)


def label_future_ret_from_bars(df_bars: pd.DataFrame, horizon_minutes: int) -> pd.DataFrame:
    """Given 1m bars (ts, close), compute future return over `horizon_minutes`.
    Output columns: ts, y_ret (float), y_up (0/1).
    """
    if df_bars is None or df_bars.empty:
        return pd.DataFrame(columns=["ts", "y_ret", "y_up"])

    df = df_bars.copy().sort_values("ts").reset_index(drop=True)

    # For each ts, find the first bar at/after ts + horizon
    future_ts = df["ts"] + pd.to_timedelta(horizon_minutes, unit="m")
    idx = df["ts"].searchsorted(future_ts, side="left")

    y = []
    for i, j in enumerate(idx):
        if j >= len(df):
            y.append(None)
        else:
            p0 = float(df["close"].iloc[i])
            pH = float(df["close"].iloc[j])
            ret = (pH / p0) - 1.0
            y.append(ret)

    out = pd.DataFrame({"ts": df["ts"], "y_ret": y})
    out = out.dropna().reset_index(drop=True)
    out["y_up"] = (out["y_ret"] > 0).astype(int)
    return out