from __future__ import annotations
from datetime import timezone
import re
import pandas as pd

from apps.common.clickhouse_client import query_df, insert_df
from datetime import timedelta

# Columns must match fxai.features_1m schema
FEATURE_COLS = [
    "ts",
    "pair",
    "ret_1m",
    "ret_5m",
    "ret_15m", "vol_5m",
    "vol_15m",
    "sma_5",
    "sma_15",
    "momentum_15m",
    "minutes_to_event",
    "is_high_importance",
]


def split_pair(pair: str) -> tuple[str, str]:
    m = re.match(r"([A-Z]{3})([A-Z]{3})$", pair.upper())
    if not m:
        return pair[:3].upper(), pair[3:6].upper()
    return m.group(1), m.group(2)


def fetch_bars(pair: str, lookback_minutes: int = 360) -> pd.DataFrame:
    sql = f"""
        SELECT ts, pair, close AS mid
        FROM fxai.bars_1m
        WHERE pair = '{pair}'
          AND ts >= now() - INTERVAL {lookback_minutes} MINUTE
        ORDER BY ts
    """
    return query_df(sql)


def fetch_next_high_event_minutes(c1: str, c2: str) -> int:
    """Return minutes to next *high-importance* event for either currency.
    If none found in future, return -1.
    """
    sql = f"""
        SELECT dateDiff('minute', now(), ts) AS mins
        FROM fxai.macro_events
        WHERE currency IN ('{c1}', '{c2}')
          AND ts >= now()
          AND importance = 'high'
        ORDER BY ts
        LIMIT 1
    """
    df = query_df(sql)
    if df.empty:
        return -1
    try:
        return int(df.iloc[0, 0])
    except Exception:
        return -1


def compute_features(df_bars: pd.DataFrame, pair: str) -> pd.DataFrame:
    if df_bars.empty:
        return pd.DataFrame(columns=FEATURE_COLS)

    df = df_bars.copy()

    # Returns & rolling stats
    df["ret_1m"] = df["mid"].pct_change(1)
    df["ret_5m"] = df["mid"].pct_change(5)
    df["ret_15m"] = df["mid"].pct_change(15)
    df["vol_5m"] = df["ret_1m"].rolling(5).std()
    df["vol_15m"] = df["ret_1m"].rolling(15).std()

    # SMAs & simple momentum
    df["sma_5"] = df["mid"].rolling(5).mean()
    df["sma_15"] = df["mid"].rolling(15).mean()
    df["momentum_15m"] = df["mid"] - df["sma_15"]

    # Macro proximity
    # Macro proximity per-row (minutes to NEXT high-importance event)
    c1, c2 = split_pair(pair)
    ev = fetch_future_high_events(c1, c2)
    if not ev.empty:
        ev = ev.sort_values("ts").rename(columns={"ts": "event_ts"}).reset_index(drop=True)
        # As-of join: for each bar ts, find the next event (event_ts >= ts)
        # Trick: we can compute minutes by merging twice: once on forward shift
        # Simpler: use a forward mapping by reindexing with searchsorted
        bar_ts = df["ts"].values
        event_ts = ev["event_ts"].values
        idx = event_ts.searchsorted(bar_ts, side="left")
        minutes = []
        for i, j in enumerate(idx):
            if j >= len(event_ts):
                minutes.append(-1)
            else:
                delta = (pd.Timestamp(event_ts[j]) - pd.Timestamp(bar_ts[i]))
                minutes.append(int(delta.total_seconds() // 60))
        df["minutes_to_event"] = minutes
        # mark as high importance window if within 90 minutes to the next event
        df["is_high_importance"] = df["minutes_to_event"].apply(lambda m: 1 if (m >= 0 and m <= 90) else 0)
    else:
        df["minutes_to_event"] = -1
        df["is_high_importance"] = 0

    # Finalize
    df["pair"] = pair
    out = df.dropna().loc[:, FEATURE_COLS]
    return out.reset_index(drop=True)

# Convenience wrapper used by the API
def build_features(pair: str, lookback_minutes: int = 360):
    """Fetch recent bars and compute features for the given pair.
    Returns a pandas DataFrame matching FEATURE_COLS.
    """
    bars = fetch_bars(pair, lookback_minutes)
    return compute_features(bars, pair)

def fetch_future_high_events(c1: str, c2: str, horizon_hours: int = 48) -> pd.DataFrame:
    sql = f"""
        SELECT ts
        FROM fxai.macro_events
        WHERE currency IN ('{c1}', '{c2}')
          AND importance = 'high'
          AND ts >= now()
          AND ts <= now() + INTERVAL {horizon_hours} HOUR
        ORDER BY ts
    """
    return query_df(sql)

def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="USDINR")
    ap.add_argument("--lookback-minutes", type=int, default=360)
    args = ap.parse_args()

    bars = fetch_bars(args.pair, args.lookback_minutes)
    feats = compute_features(bars, args.pair)
    if feats.empty:
        print("No features computed (not enough bars).")
        return
    insert_df("fxai.features_1m", feats)
    print(f"Inserted {len(feats)} rows into fxai.features_1m")


if __name__ == "__main__":
    main()