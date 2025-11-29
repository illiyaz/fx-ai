from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
from typing import List, Tuple
from apps.common.clickhouse_client import insert_rows

COLUMNS = ["ts","currency","country","event","importance","actual","forecast","previous","source","tags"]

def parse_row(r: dict) -> Tuple:
    """
    Expecting CSV headers:
    ts_iso,currency,country,event,importance,actual,forecast,previous,tags
    - ts_iso in ISO 8601 (assumed UTC if no timezone)
    - importance in {low, medium, high} (case-insensitive)
    - tags: pipe- or comma-separated
    """
    ts_raw = r["ts_iso"].strip()
    ts = datetime.fromisoformat(ts_raw.replace("Z","")).replace(tzinfo=timezone.utc) if "Z" in ts_raw or "+" in ts_raw else datetime.fromisoformat(ts_raw).replace(tzinfo=timezone.utc)
    imp = r.get("importance","medium").strip().lower()
    if imp not in ("low","medium","high"):
        imp = "medium"
    tags_raw = r.get("tags","").strip()
    tags = [t.strip() for t in tags_raw.replace("|",",").split(",") if t.strip()]
    return (
        ts.replace(tzinfo=None),                 # ClickHouse DateTime (naive) assumed UTC
        r["currency"].strip().upper(),
        r.get("country","").strip().upper(),
        r["event"].strip(),
        imp,
        r.get("actual","").strip(),
        r.get("forecast","").strip(),
        r.get("previous","").strip(),
        "csv",
        tags,
    )

def load_csv(path: str, batch: int = 1000) -> int:
    rows: List[Tuple] = []
    total = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(parse_row(r))
            if len(rows) >= batch:
                insert_rows("fxai.macro_events", rows, COLUMNS)
                total += len(rows)
                rows.clear()
        if rows:
            insert_rows("fxai.macro_events", rows, COLUMNS)
            total += len(rows)
    return total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to macro events CSV")
    args = ap.parse_args()
    count = load_csv(args.csv)
    print(f"Inserted {count} macro events.")

if __name__ == "__main__":
    main()