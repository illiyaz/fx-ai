from __future__ import annotations
import argparse
from datetime import timedelta
import pandas as pd
from apps.common.clickhouse_client import query_df, insert_rows

HORIZON_MINUTES = {"30m": 30, "1h": 60, "2h": 120, "4h": 240}

def load_decisions(pair: str, horizon: str, lookback_hours: int) -> pd.DataFrame:
    sql = f"""
        SELECT ts, pair, horizon, posterior_prob_up AS prob_up, expected_delta_bps
        FROM fxai.decisions
        WHERE pair = '{pair}'
          AND horizon = '{horizon}'
          AND ts >= now() - INTERVAL {lookback_hours} HOUR
        ORDER BY ts
    """
    return query_df(sql)

def load_bars(pair: str, min_back_minutes: int) -> pd.DataFrame:
    sql = f"""
        SELECT ts, close
        FROM fxai.bars_1m
        WHERE pair = '{pair}'
          AND ts >= now() - INTERVAL {min_back_minutes} MINUTE
        ORDER BY ts
    """
    return query_df(sql)

def realized_bps(bars: pd.DataFrame, t0, horizon_min: int) -> float | None:
    row0 = bars[bars["ts"] >= t0].head(1)
    rowH = bars[bars["ts"] >= (t0 + timedelta(minutes=horizon_min))].head(1)
    if row0.empty or rowH.empty:
        return None
    p0 = float(row0["close"].iloc[0])
    pH = float(rowH["close"].iloc[0])
    return ((pH / p0) - 1.0) * 10_000.0

def run_backtest(pair: str, horizon: str, lookback_hours: int,
                 prob_th: float, spread_bps: float, gate_by_expected: bool) -> tuple[dict, pd.DataFrame]:
    H = HORIZON_MINUTES[horizon]
    dec = load_decisions(pair, horizon, lookback_hours)
    if dec.empty:
        return {"trades": 0}, pd.DataFrame()

    bars = load_bars(pair, min_back_minutes=(lookback_hours * 60 + H + 5))
    if bars.empty:
        return {"trades": 0}, pd.DataFrame()

    rows = []
    for _, d in dec.iterrows():
        bps = realized_bps(bars, d["ts"], H)
        if bps is None:
            continue
        prob_up = float(d["prob_up"])
        exp_bps = float(d.get("expected_delta_bps") or 0.0)

        # Trade decision
        if gate_by_expected:
            # Only trade if expected absolute move clears spread
            if abs(exp_bps) <= spread_bps:
                signal = 0
            else:
                signal = 1 if exp_bps > 0 else -1
        else:
            if prob_up >= prob_th:
                signal = 1
            elif prob_up <= (1.0 - prob_th):
                signal = -1
            else:
                signal = 0

        if signal == 0:
            continue

        pnl_bps = signal * bps - spread_bps
        correct = (signal * bps) > 0
        rows.append({
            "ts": d["ts"],
            "prob_up": prob_up,
            "expected_delta_bps": exp_bps,
            "signal": signal,
            "bps_realized": bps,
            "pnl_bps": pnl_bps,
            "correct": correct
        })

    if not rows:
        return {"trades": 0}, pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("ts")
    n = len(df)
    win_rate = df["correct"].mean()
    avg_pnl = df["pnl_bps"].mean()
    med_pnl = df["pnl_bps"].median()

    summary = {
        "pair": pair,
        "horizon": horizon,
        "lookback_hours": lookback_hours,
        "prob_th": prob_th,
        "spread_bps": spread_bps,
        "trades": int(n),
        "win_rate": float(win_rate),
        "avg_pnl_bps": float(avg_pnl),
        "med_pnl_bps": float(med_pnl),
    }
    return summary, df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="USDINR")
    ap.add_argument("--horizon", default="4h", choices=list(HORIZON_MINUTES))
    ap.add_argument("--lookback-hours", type=int, default=24)
    ap.add_argument("--prob-th", type=float, default=0.6)
    ap.add_argument("--spread-bps", type=float, default=2.0)
    ap.add_argument("--gate-by-expected", action="store_true", help="Gate trading by expected move > spread")
    ap.add_argument("--write-metrics", action="store_true", help="Write summary metrics to fxai.backtest_metrics")
    args = ap.parse_args()

    summary, df = run_backtest(args.pair, args.horizon, args.lookback_hours,
                               args.prob_th, args.spread_bps, args.gate_by_expected)

    if summary.get("trades", 0) == 0:
        print("No evaluable trades.")
        return

    print(f"Backtest: pair={summary['pair']} horizon={summary['horizon']} window={summary['lookback_hours']}h")
    print(f"Trades: {summary['trades']} | Win rate: {summary['win_rate']:.3f} "
          f"| Avg PnL (bps): {summary['avg_pnl_bps']:.2f} | Median: {summary['med_pnl_bps']:.2f}")

    if args.write_metrics:
        insert_rows(
            "fxai.backtest_metrics",
            [(
                # ts defaults to now() in ClickHouse
                summary["pair"], summary["horizon"], summary["lookback_hours"],
                summary["prob_th"], summary["spread_bps"], summary["trades"],
                summary["win_rate"], summary["avg_pnl_bps"], summary["med_pnl_bps"]
            )],
            [
                "pair","horizon","lookback_hours","prob_th","spread_bps",
                "trades","win_rate","avg_pnl_bps","med_pnl_bps"
            ]
        )
        print("Wrote summary to fxai.backtest_metrics")

if __name__ == "__main__":
    main()