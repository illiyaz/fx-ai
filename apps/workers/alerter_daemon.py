from __future__ import annotations
import os
import time
import structlog
import pandas as pd

try:
    import httpx  # optional (for webhook)
except Exception:  # pragma: no cover
    httpx = None

from apps.common.clickhouse_client import query_df, insert_rows

log = structlog.get_logger()

ALERT_POLL_SEC = int(os.getenv("ALERT_POLL_SEC", "30"))
ALERT_LOOKBACK_MIN = int(os.getenv("ALERT_LOOKBACK_MIN", "120"))
ALERT_WEBHOOK_URL = "https://webhook.site/2ce2c74a-8012-4fd7-bf6f-e728b529b886" # os.getenv("ALERT_WEBHOOK_URL")  # optional


def _split_pair(p: str) -> tuple[str, str]:
    p = (p or "").upper()
    return p[:3], p[3:6]


def infer_direction_and_hint(pair: str, prob_up: float, exp_bps: float) -> tuple[str, str]:
    base, quote = _split_pair(pair)
    sign = exp_bps if abs(exp_bps) > 1e-9 else (2.0 * float(prob_up) - 1.0)
    direction = "UP" if sign >= 0 else "DOWN"
    if direction == "UP":
        hint = (
            f"{base} likely to strengthen vs {quote}. If you need to BUY {base}, "
            f"consider acting sooner; if you plan to SELL {base}, delaying may help."
        )
    else:
        hint = (
            f"{base} likely to weaken vs {quote}. If you need to SELL {base}, "
            f"consider acting sooner; if you plan to BUY {base}, waiting may help."
        )
    return direction, hint


def fetch_new_now_decisions(lookback_min: int) -> pd.DataFrame:
    sql = f"""
        SELECT d.ts AS decision_ts, d.pair, d.horizon,
               d.posterior_prob_up AS prob_up,
               coalesce(d.expected_delta_bps, 0.0) AS expected_delta_bps,
               d.recommendation,
               d.explanation,
               d.policy_version AS model_id
        FROM fxai.decisions AS d
        LEFT JOIN fxai.alerts AS a
          ON a.decision_ts = toDateTime(d.ts)
         AND a.pair = d.pair
         AND a.horizon = d.horizon
        WHERE d.ts >= now() - INTERVAL {lookback_min} MINUTE
          AND d.recommendation = 'NOW'
          AND a.decision_ts IS NULL
        ORDER BY d.ts
    """
    return query_df(sql)


def post_webhook(payload: dict) -> bool:
    if not ALERT_WEBHOOK_URL or httpx is None:
        return False
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.post(ALERT_WEBHOOK_URL, json=payload)
            return r.status_code // 100 == 2
    except Exception:
        log.exception("webhook_post_error")
        return False


def insert_alert_rows(rows: list[tuple]):
    insert_rows(
        "fxai.alerts",
        rows,
        [
            
            "decision_ts",
            "pair",
            "horizon",
            "prob_up",
            "expected_delta_bps",
            "recommendation",
            "direction",
            "action_hint",
            "model_id",
            "explanation",
            "embargo_applied",
            "sent",
            "dest",
        ],
    )


def loop():
    log.info("alerter_start", poll_sec=ALERT_POLL_SEC, lookback_min=ALERT_LOOKBACK_MIN)
    while True:
        try:
            df = fetch_new_now_decisions(ALERT_LOOKBACK_MIN)
            log.info("alerter_poll", fetched=len(df))
            if not df.empty:
                log.info("alerter_preview", head=df.head(3).to_dict(orient="records"))
                out_rows: list[tuple] = []
                for _, r in df.iterrows():
                    direction, hint = infer_direction_and_hint(
                        r["pair"], float(r["prob_up"]), float(r["expected_delta_bps"]))
                    payload = {
                        "pair": r["pair"],
                        "h": r["horizon"],
                        "prob_up": float(r["prob_up"]),
                        "expected_delta_bps": float(r["expected_delta_bps"]),
                        "direction": direction,
                        "action_hint": hint,
                        "model_id": r.get("model_id", "unknown"),
                        "decision_ts": str(r["decision_ts"]),
                        "explanation": r.get("explanation", ""),
                    }
                    sent = 1 if post_webhook(payload) else 0
                    dest = "webhook" if sent else "stdout"
                    if not sent:
                        log.info("alert", **payload)

                    out_rows.append((
                       
                        r["decision_ts"], r["pair"], r["horizon"],
                        float(r["prob_up"]), float(r["expected_delta_bps"]),
                        "NOW", direction, hint, r.get("model_id", "unknown"),
                        r.get("explanation", ""),
                        0,  # embargo_applied (not evaluated here)
                        sent, dest,
                    ))
                if out_rows:
                    try:
                        log.info("alerter_inserting", rows=len(out_rows))
                        insert_alert_rows(out_rows)
                        log.info("alerter_insert_ok", rows=len(out_rows))
                    except Exception:
                        log.exception("alerter_insert_error", rows=len(out_rows), sample=out_rows[0] if out_rows else None)
            else:
                log.debug("alerter_no_new")
        except Exception:
            log.exception("alerter_loop_error")
        time.sleep(ALERT_POLL_SEC)


def run_once():
    try:
        df = fetch_new_now_decisions(ALERT_LOOKBACK_MIN)
        log.info("alerter_poll_once", fetched=len(df))
        if df.empty:
            return
        out_rows: list[tuple] = []
        for _, r in df.iterrows():
            direction, hint = infer_direction_and_hint(
                r["pair"], float(r["prob_up"]), float(r["expected_delta_bps"]))
            payload = {
                "pair": r["pair"],
                "h": r["horizon"],
                "prob_up": float(r["prob_up"]),
                "expected_delta_bps": float(r["expected_delta_bps"]),
                "direction": direction,
                "action_hint": hint,
                "model_id": r.get("model_id", "unknown"),
                "decision_ts": str(r["decision_ts"]),
                "explanation": r.get("explanation", ""),
            }
            sent = 1 if post_webhook(payload) else 0
            dest = "webhook" if sent else "stdout"
            if not sent:
                log.info("alert", **payload)
            out_rows.append((
                r["decision_ts"], r["pair"], r["horizon"],
                float(r["prob_up"]), float(r["expected_delta_bps"]),
                "NOW", direction, hint, r.get("model_id", "unknown"),
                r.get("explanation", ""), 0, sent, dest,
            ))
        try:
            log.info("alerter_inserting_once", rows=len(out_rows))
            insert_alert_rows(out_rows)
            log.info("alerter_insert_ok_once", rows=len(out_rows))
        except Exception:
            log.exception("alerter_insert_error_once", rows=len(out_rows), sample=out_rows[0] if out_rows else None)
    except Exception:
        log.exception("alerter_once_error")


def main():
    if os.getenv("ALERT_ONCE") == "1":
        run_once()
    else:
        loop()


if __name__ == "__main__":
    main()