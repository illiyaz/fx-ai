from __future__ import annotations
import os
import time
import signal
import argparse
from typing import List

from apps.features.featurize import build_features
from apps.common.clickhouse_client import insert_df

RUNNING = True

def _handle_signal(signum, frame):
    global RUNNING
    RUNNING = False

for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, _handle_signal)


def parse_args():
    ap = argparse.ArgumentParser(description="Featurizer daemon")
    ap.add_argument("--pairs", default=os.getenv("FEAT_PAIRS", "USDINR"),
                    help="Comma-separated list of pairs, e.g., 'USDINR,EURUSD'")
    ap.add_argument("--interval", type=int, default=int(os.getenv("FEAT_INTERVAL_SEC", "60")),
                    help="Seconds between featurization runs")
    ap.add_argument("--lookback-minutes", type=int, default=int(os.getenv("FEAT_LOOKBACK_MIN", "360")),
                    help="Bars lookback window (minutes)")
    return ap.parse_args()


def run_once(pairs: List[str], lookback_minutes: int) -> int:
    total_inserted = 0
    for pair in pairs:
        try:
            feats = build_features(pair.strip().upper(), lookback_minutes)
            if feats is not None and not feats.empty:
                insert_df("fxai.features_1m", feats)
                total_inserted += len(feats)
                print(f"[featurizer] pair={pair} inserted={len(feats)} rows")
            else:
                print(f"[featurizer] pair={pair} no features (insufficient bars)")
        except Exception as e:
            print(f"[featurizer][error] pair={pair} {type(e).__name__}: {e}")
    return total_inserted


def main():
    args = parse_args()
    pairs = [p.strip().upper() for p in args.pairs.split(",") if p.strip()]
    interval = max(5, int(args.interval))  # guard against too-frequent loops

    print(f"[featurizer] starting; pairs={pairs} interval={interval}s lookback={args.lookback_minutes}m")

    # slight initial delay to avoid aligning exactly on the minute boundary
    time.sleep(2)

    while RUNNING:
        inserted = run_once(pairs, args.lookback_minutes)
        # sleep regardless of success/failure; allow graceful shutdown
        for _ in range(interval):
            if not RUNNING:
                break
            time.sleep(1)

    print("[featurizer] shutting down")


if __name__ == "__main__":
    main()