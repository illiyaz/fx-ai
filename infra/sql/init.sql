CREATE DATABASE IF NOT EXISTS fxai;

CREATE TABLE IF NOT EXISTS fxai.events_news (
  ts DateTime64(3), src String, headline String, country LowCardinality(String),
  event_type LowCardinality(String), region LowCardinality(String),
  severity UInt8, direction LowCardinality(String), pairs Array(String),
  impact_score Float32, confidence Float32
) ENGINE=MergeTree ORDER BY ts;

CREATE TABLE IF NOT EXISTS fxai.shocks (
  ts DateTime64(3), pair LowCardinality(String),
  r5m Float32, volp Float32, spreadp Float32,
  jump_sigma Float32, level Enum8('none'=0,'caution'=1,'high'=2,'critical'=3),
  reason String
) ENGINE=MergeTree ORDER BY (pair, ts);

CREATE TABLE IF NOT EXISTS fxai.predictions (
  ts DateTime64(3), pair LowCardinality(String), horizon LowCardinality(String),
  prob_up Float32, exp_delta_bps Float32,
  p10 Float32, p90 Float32, confidence Float32,
  model_id String, features_json String
) ENGINE=MergeTree ORDER BY (pair, horizon, ts);

CREATE TABLE IF NOT EXISTS fxai.decisions (
  ts DateTime64(3), pair LowCardinality(String), horizon LowCardinality(String),
  prior_prob_up Float32, posterior_prob_up Float32, expected_delta_bps Float64,
  range_p10 Float32, range_p90 Float32,
  shock_level Enum8('none'=0,'caution'=1,'high'=2,'critical'=3),
  event_impact Float32, recommendation LowCardinality(String),
  explanation String, policy_version String
) ENGINE=MergeTree ORDER BY (pair, horizon, ts);

-- Sprint 1: FX bars schema

-- Staging/raw events (ticks or microbars) — append-only
CREATE TABLE IF NOT EXISTS fxai.bars_raw (
  ts DateTime64(3) CODEC(DoubleDelta, LZ4),
  pair LowCardinality(String),
  bid Float64,
  ask Float64,
  mid Float64,
  spread Float32,
  src LowCardinality(String)
) ENGINE=MergeTree
ORDER BY (pair, ts)
TTL toDateTime(ts) + INTERVAL 30 DAY;

-- Canonical 1-minute bars (mid, with spread snapshot)
CREATE TABLE IF NOT EXISTS fxai.bars_1m (
  ts DateTime CODEC(DoubleDelta, LZ4),
  pair LowCardinality(String),
  open Float64,
  high Float64,
  low Float64,
  close Float64,
  spread_avg Float32,
  src LowCardinality(String)
) ENGINE=MergeTree
ORDER BY (pair, ts)
TTL toDateTime(ts) + INTERVAL 180 DAY;

-- Optional: if you ingest into bars_raw, this view builds 1m bars automatically
CREATE MATERIALIZED VIEW IF NOT EXISTS fxai.mv_bars_raw_to_1m
TO fxai.bars_1m AS
SELECT
  toStartOfMinute(ts) AS ts,
  pair,
  anyHeavy(mid)              AS open,   -- approximation for first
  max(mid)                   AS high,
  min(mid)                   AS low,
  anyLast(mid)               AS close,  -- last in the minute
  avg(spread)                AS spread_avg,
  anyLast(src)               AS src
FROM fxai.bars_raw
GROUP BY ts, pair;

-- Sprint 1: validations table

CREATE TABLE IF NOT EXISTS fxai.validations (
  ts DateTime64(3),
  pair LowCardinality(String),
  rule LowCardinality(String),         -- e.g., 'spread_sanity', 'nan_check', 'non_monotonic_ts'
  level Enum8('info' = 0, 'warn' = 1, 'error' = 2),
  message String,
  context_json String                  -- small JSON for debugging (values, prev_ts, etc.)
) ENGINE = MergeTree
ORDER BY (pair, ts)
TTL toDateTime(ts) + INTERVAL 30 DAY;

-- Sprint 1: macro/economic events
CREATE TABLE IF NOT EXISTS fxai.macro_events (
  ts           DateTime,
  currency     LowCardinality(String),     -- e.g., USD, INR, EUR
  country      LowCardinality(String),     -- e.g., US, IN, EU
  event        String,                     -- e.g., CPI YoY, RBI rate decision
  importance   Enum8('low'=0,'medium'=1,'high'=2),
  actual       String DEFAULT '',
  forecast     String DEFAULT '',
  previous     String DEFAULT '',
  source       LowCardinality(String) DEFAULT 'csv',  -- csv|ics|api
  tags         Array(String) DEFAULT []
) ENGINE=MergeTree
ORDER BY (ts, currency)
TTL toDateTime(ts) + INTERVAL 365 DAY;

-- Feature store: rolling indicators & event proximity
CREATE TABLE IF NOT EXISTS fxai.features_1m (
  ts DateTime64(3),
  pair LowCardinality(String),
  ret_1m Float32,
  ret_5m Float32,
  ret_15m Float32,
  vol_5m Float32,
  vol_15m Float32,
  sma_5 Float32,
  sma_15 Float32,
  momentum_15m Float32,
  minutes_to_event Int32,
  is_high_importance UInt8
) ENGINE=MergeTree
ORDER BY (pair, ts);

-- Model registry (baseline + ML)
CREATE TABLE IF NOT EXISTS fxai.models (
  model_id String,
  ts DateTime DEFAULT now(),
  algo String,
  horizon LowCardinality(String),
  train_window String,
  metrics_json String,
  params_json String
) ENGINE=MergeTree
ORDER BY (model_id, ts);

CREATE TABLE IF NOT EXISTS fxai.backtest_metrics (
  ts DateTime DEFAULT now(),
  pair LowCardinality(String),
  horizon LowCardinality(String),
  lookback_hours UInt32,
  prob_th Float64,
  spread_bps Float64,
  trades UInt32,
  win_rate Float64,
  avg_pnl_bps Float64,
  med_pnl_bps Float64
) ENGINE=MergeTree
ORDER BY (pair, horizon, ts);

CREATE TABLE IF NOT EXISTS fxai.backtest_summary (
  ts DateTime DEFAULT now(),
  pair LowCardinality(String),
  horizon LowCardinality(String),
  policy String,
  spread_bps Float64,
  lookback_hours UInt32,
  model_id String,
  n_trades UInt32,
  hit_rate Float64,                  -- fraction profitable after spread
  avg_pnl_bps Float64,               -- mean PnL per trade
  sharpe Float64,                    -- avg/sd * sqrt(252*24*60/horizon_min)
  max_drawdown_bps Float64
) ENGINE=MergeTree
ORDER BY (pair, horizon, ts);

-- Alerts sink (dedup on decision_ts + pair + horizon)
CREATE TABLE IF NOT EXISTS fxai.alerts (
  ts DateTime DEFAULT now(),                -- insert time
  decision_ts DateTime,                     -- ts from fxai.decisions
  pair LowCardinality(String),
  horizon LowCardinality(String),
  prob_up Float64,
  expected_delta_bps Float64,
  recommendation String,
  direction LowCardinality(String),         -- "UP" | "DOWN"
  action_hint String,                       -- human hint
  model_id String,
  explanation String,
  embargo_applied UInt8 DEFAULT 0,
  sent UInt8 DEFAULT 0,                     -- 1 if webhook delivery attempted
  dest LowCardinality(String) DEFAULT 'stdout'  -- stdout|webhook|...
) ENGINE=MergeTree
ORDER BY (pair, horizon, decision_ts)
TTL toDateTime(ts) + INTERVAL 90 DAY;