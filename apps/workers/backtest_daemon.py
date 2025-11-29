from __future__ import annotations
import os, time
from apps.backtest.quick_check import run_backtest
from apps.common.clickhouse_client import insert_rows

def main():
    pair = os.getenv("BT_PAIR", "USDINR")
    horizon = os.getenv("BT_HORIZON", "4h")
    lookback = int(os.getenv("BT_LOOKBACK_HOURS", "24"))
    prob_th = float(os.getenv("BT_PROB_TH", "0.6"))
    spread = float(os.getenv("BT_SPREAD_BPS", "2.0"))
    gate_expected = os.getenv("BT_GATE_EXPECTED", "false").lower() in ("1","true","yes")
    interval_sec = int(os.getenv("BT_INTERVAL_SEC", "900"))  # 15 min default

    print(f"[backtester] start pair={pair} horizon={horizon} every {interval_sec}s")
    while True:
        try:
            summary, df = run_backtest(pair, horizon, lookback, prob_th, spread, gate_expected)
            if summary.get("trades", 0) > 0:
                insert_rows(
                    "fxai.backtest_metrics",
                    [(
                        summary["pair"], summary["horizon"], summary["lookback_hours"],
                        summary["prob_th"], summary["spread_bps"], summary["trades"],
                        summary["win_rate"], summary["avg_pnl_bps"], summary["med_pnl_bps"]
                    )],
                    [
                        "pair","horizon","lookback_hours","prob_th","spread_bps",
                        "trades","win_rate","avg_pnl_bps","med_pnl_bps"
                    ]
                )
                print("[backtester] wrote metrics")
            else:
                print("[backtester] no evaluable trades")
        except Exception as e:
            print(f"[backtester][error] {type(e).__name__}: {e}")
        time.sleep(max(60, interval_sec))

if __name__ == "__main__":
    main()