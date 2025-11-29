from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import json
import math
from datetime import datetime

@dataclass
class ValidationHit:
    ts: datetime
    pair: str
    rule: str
    level: str      # 'info' | 'warn' | 'error'
    message: str
    context: Dict[str, Any]

    def to_row(self):
        return (
            self.ts,
            self.pair,
            self.rule,
            self.level,
            self.message,
            json.dumps(self.context, separators=(",", ":")),
        )

# ---- Checks ----

def check_nan(row: Dict[str, Any]) -> List[ValidationHit]:
    hits: List[ValidationHit] = []
    ts = row["ts"]
    pair = row["pair"]
    for k in ("bid", "ask", "mid", "spread"):
        v = row.get(k)
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            hits.append(
                ValidationHit(
                    ts=ts,
                    pair=pair,
                    rule="nan_check",
                    level="error",
                    message=f"{k} is null/NaN/inf",
                    context={"field": k, "value": v},
                )
            )
    return hits

def check_spread_sanity(row: Dict[str, Any], max_spread: float = 0.75) -> List[ValidationHit]:
    """
    Basic spread sanity for USDINR-style pairs (spread in INR, typical < 0.10).
    """
    hits: List[ValidationHit] = []
    ts = row["ts"]
    pair = row["pair"]
    spread = float(row["spread"])
    if spread <= 0:
        hits.append(
            ValidationHit(
                ts=ts, pair=pair, rule="spread_sanity", level="error",
                message="non-positive spread", context={"spread": spread}
            )
        )
    elif spread > max_spread:
        hits.append(
            ValidationHit(
                ts=ts, pair=pair, rule="spread_sanity", level="warn",
                message="spread unusually large", context={"spread": spread, "max": max_spread}
            )
        )
    return hits

def check_monotonic_ts(row: Dict[str, Any], prev_ts: Optional[datetime]) -> List[ValidationHit]:
    hits: List[ValidationHit] = []
    if prev_ts and row["ts"] < prev_ts:
        hits.append(
            ValidationHit(
                ts=row["ts"],
                pair=row["pair"],
                rule="non_monotonic_ts",
                level="warn",
                message="timestamp moved backwards",
                context={"prev_ts": prev_ts.isoformat(), "ts": row["ts"].isoformat()},
            )
        )
    return hits

def run_all(row: Dict[str, Any], prev_ts: Optional[datetime]) -> List[ValidationHit]:
    hits: List[ValidationHit] = []
    hits += check_nan(row)
    hits += check_spread_sanity(row)
    hits += check_monotonic_ts(row, prev_ts)
    return hits