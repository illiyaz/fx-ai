from __future__ import annotations
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import argparse
import math
import random
import time
from datetime import datetime, timedelta, timezone
import pandas as pd

from apps.common.validators import run_all, ValidationHit
from apps.common.clickhouse_client import insert_rows

COLUMNS = ["ts", "pair", "bid", "ask", "mid", "spread", "src"]

def gen_bar(ts: datetime, pair: str, last_mid: float) -> tuple:
    # Simple synthetic walk: sinusoid + noise
    base = last_mid + random.gauss(0, 0.002)  # ~0.2 paisa noise
    wave = 0.03 * math.sin(ts.minute / 60 * 2 * math.pi)  # daylight wiggle (~3 paisa)
    mid = max(10.0, base + wave)

    # spread ~ 2-5 paisa; add rare spikes
    spread = 0.02 + random.random() * 0.03
    if random.random() < 0.01:
        spread *= 3

    bid = mid - spread / 2
    ask = mid + spread / 2
    return (ts, pair, round(bid, 4), round(ask, 4), round(mid, 4), round(spread, 4), "demo")

def backfill(minutes: int, pair: str, start_mid: float) -> float:
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    ts0 = now - timedelta(minutes=minutes)
    mid = start_mid
    rows = []
    for i in range(minutes):
        ts = ts0 + timedelta(minutes=i)
        row = gen_bar(ts, pair, mid)
        
        # inside backfill() loop, after `row = gen_bar(...)`:
        row_dict = {
            "ts": row[0], "pair": row[1], "bid": row[2],
            "ask": row[3], "mid": row[4], "spread": row[5]
        }
        prev_ts = rows[-1][0] if rows else None
        hits = run_all(row_dict, prev_ts)
        if hits:
            insert_rows(
                "fxai.validations",
                [h.to_row() for h in hits],
                ["ts", "pair", "rule", "level", "message", "context_json"]
            )

        rows.append(row)
        mid = row[4]
    insert_rows("fxai.bars_raw", rows, COLUMNS)
    return mid

def stream(pair: str, mid: float, interval_seconds: int):
    while True:
        ts = datetime.now(timezone.utc)
        row = gen_bar(ts, pair, mid)

        row_dict = {
            "ts": row[0], "pair": row[1], "bid": row[2],
            "ask": row[3], "mid": row[4], "spread": row[5]
        }
        # we don't track prev_ts across restarts here; using None is fine for stream
        hits = run_all(row_dict, None)
        if hits:
            insert_rows(
                "fxai.validations",
                [h.to_row() for h in hits],
                ["ts", "pair", "rule", "level", "message", "context_json"]
            )  

        insert_rows("fxai.bars_raw", [row], COLUMNS)
        mid = row[4]
        time.sleep(interval_seconds)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="USDINR")
    ap.add_argument("--minutes", type=int, default=120, help="Backfill N minutes before streaming")
    ap.add_argument("--interval-seconds", type=int, default=5, help="Streaming insert cadence")
    ap.add_argument("--start-mid", type=float, default=83.20)
    args = ap.parse_args()

    mid = backfill(args.minutes, args.pair, args.start_mid)
    stream(args.pair, mid, args.interval_seconds)

if __name__ == "__main__":
    main()