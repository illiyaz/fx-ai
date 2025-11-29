-- =====================================================
-- FX-AI News & LLM Integration Schema
-- =====================================================
-- This schema extends the base system with news ingestion,
-- LLM sentiment analysis, and hybrid ML+LLM features.
-- =====================================================

-- News Items: Raw news articles and social media posts
CREATE TABLE IF NOT EXISTS fxai.news_items (
  id String,                              -- Unique news item ID (hash of url + ts)
  ts DateTime64(3),                       -- Publication timestamp
  source LowCardinality(String),          -- reuters, bloomberg, twitter, rbi, fed, etc.
  headline String,                        -- Article headline
  content String,                         -- Full article text (or tweet)
  url String,                             -- Source URL
  author String DEFAULT '',               -- Author/publisher
  language LowCardinality(String) DEFAULT 'en',
  raw_json String DEFAULT ''              -- Original JSON for debugging
) ENGINE=MergeTree
ORDER BY (ts, source)
TTL toDateTime(ts) + INTERVAL 90 DAY
COMMENT 'Raw news articles and social media posts';

-- Sentiment Scores: LLM-generated sentiment analysis
CREATE TABLE IF NOT EXISTS fxai.sentiment_scores (
  news_id String,                         -- Reference to news_items.id
  ts DateTime64(3),                       -- Analysis timestamp
  model_version String,                   -- LLM model used (gpt-4-turbo, claude-3-opus, etc.)
  
  -- Sentiment scores (-1 to +1)
  sentiment_overall Float32,              -- Overall market sentiment
  sentiment_usd Float32,                  -- USD-specific sentiment
  sentiment_inr Float32,                  -- INR-specific sentiment
  sentiment_eur Float32 DEFAULT 0.0,      -- EUR-specific sentiment
  sentiment_gbp Float32 DEFAULT 0.0,      -- GBP-specific sentiment
  sentiment_jpy Float32 DEFAULT 0.0,      -- JPY-specific sentiment
  
  -- Confidence and impact
  confidence Float32,                     -- Model confidence (0-1)
  impact_score Float32,                   -- Predicted impact magnitude (0-10)
  urgency Enum8('low'=0,'medium'=1,'high'=2,'critical'=3),
  
  -- Entity extraction
  currencies Array(String),               -- Mentioned currencies
  countries Array(String),                -- Mentioned countries
  institutions Array(String),             -- Central banks, governments, etc.
  topics Array(String),                   -- inflation, rates, trade, geopolitics, etc.
  
  -- Reasoning
  explanation String,                     -- LLM's reasoning
  key_phrases Array(String),              -- Important extracted phrases
  
  -- Performance tracking
  processing_time_ms UInt32,              -- LLM API latency
  tokens_used UInt32 DEFAULT 0,           -- Token consumption for cost tracking
  api_cost_usd Float32 DEFAULT 0.0        -- Estimated API cost
) ENGINE=MergeTree
ORDER BY (ts, news_id)
COMMENT 'LLM-generated sentiment analysis of news items';

-- News Events: Structured events extracted from news clusters
CREATE TABLE IF NOT EXISTS fxai.news_events (
  event_id String,                        -- Unique event ID
  ts DateTime64(3),                       -- Event timestamp
  event_type LowCardinality(String),      -- rate_decision, inflation_data, geopolitical, trade, etc.
  
  -- Event details
  title String,                           -- Event title (LLM-generated)
  summary String,                         -- Brief summary (2-3 sentences)
  severity Enum8('low'=0,'medium'=1,'high'=2,'critical'=3),
  
  -- Market impact prediction
  affected_pairs Array(String),           -- Currency pairs likely affected
  direction LowCardinality(String),       -- bullish_usd, bearish_usd, mixed, unknown
  expected_volatility Float32,            -- Expected vol increase (0-1)
  time_horizon_minutes UInt32,            -- How long impact expected to last
  
  -- Source tracking
  source_news_ids Array(String),          -- Contributing news items
  confidence Float32,                     -- Aggregated confidence
  
  -- Metadata
  created_at DateTime DEFAULT now(),
  model_version String
) ENGINE=MergeTree
ORDER BY (ts, event_type)
TTL toDateTime(ts) + INTERVAL 90 DAY
COMMENT 'Structured events extracted from news clusters';

-- News Features: Time-series features derived from news for ML models
CREATE TABLE IF NOT EXISTS fxai.news_features (
  ts DateTime,                            -- Minute-aligned timestamp
  pair LowCardinality(String),            -- Currency pair (USDINR, EURUSD, etc.)
  
  -- Sentiment aggregates (rolling windows)
  sentiment_1h Float32,                   -- Avg sentiment last 1 hour
  sentiment_4h Float32,                   -- Avg sentiment last 4 hours
  sentiment_24h Float32,                  -- Avg sentiment last 24 hours
  
  -- Volume metrics
  news_count_1h UInt16,                   -- News items last 1 hour
  news_count_4h UInt16,                   -- News items last 4 hours
  high_impact_count_1h UInt16,            -- High-impact news (score>7) last 1 hour
  
  -- Volatility indicators
  sentiment_volatility_1h Float32,        -- Std dev of sentiment last 1 hour
  sentiment_range_1h Float32,             -- Max - min sentiment last 1 hour
  topic_diversity Float32,                -- Entropy of topics discussed
  
  -- Event proximity
  minutes_to_critical_event Int32,        -- Time to next critical news event (-1 if none)
  ongoing_event_severity UInt8,           -- Current event severity (0-3)
  
  -- Confidence tracking
  avg_confidence_1h Float32               -- Average LLM confidence last 1 hour
) ENGINE=MergeTree
ORDER BY (pair, ts)
COMMENT 'Time-series features derived from news for ML models';

-- LLM API Usage Tracking: Monitor costs and performance
CREATE TABLE IF NOT EXISTS fxai.llm_usage (
  ts DateTime DEFAULT now(),
  model_version String,                   -- gpt-4-turbo, claude-3-opus, etc.
  operation LowCardinality(String),       -- sentiment_analysis, event_extraction, etc.
  
  -- Usage metrics
  requests UInt32,                        -- Number of API calls
  tokens_input UInt32,                    -- Input tokens consumed
  tokens_output UInt32,                   -- Output tokens generated
  total_cost_usd Float32,                 -- Total API cost
  
  -- Performance metrics
  avg_latency_ms Float32,                 -- Average response time
  error_count UInt32,                     -- Number of errors
  
  -- Aggregation window
  window_start DateTime,
  window_end DateTime
) ENGINE=MergeTree
ORDER BY (ts, model_version)
COMMENT 'LLM API usage and cost tracking';

-- Hybrid Predictions: Store combined ML + LLM predictions
CREATE TABLE IF NOT EXISTS fxai.hybrid_predictions (
  ts DateTime64(3),
  pair LowCardinality(String),
  horizon LowCardinality(String),
  
  -- ML component
  prob_up_ml Float32,                     -- Pure ML probability
  expected_delta_ml Float32,              -- Pure ML expected delta
  ml_model_id String,                     -- ML model used
  
  -- LLM component
  sentiment_score Float32,                -- News sentiment (-1 to +1)
  sentiment_confidence Float32,           -- LLM confidence
  news_impact Float32,                    -- Impact score (0-10)
  news_summary String,                    -- Brief news context
  
  -- Hybrid fusion
  prob_up_hybrid Float32,                 -- Final fused probability
  expected_delta_hybrid Float32,          -- Final fused expected delta
  fusion_weight_ml Float32,               -- Weight given to ML (0-1)
  fusion_weight_llm Float32,              -- Weight given to LLM (0-1)
  
  -- Decision
  recommendation LowCardinality(String),  -- NOW, WAIT, PARTIAL
  explanation String,                     -- Full explanation
  
  -- Metadata
  processing_time_ms UInt32,              -- Total processing time
  llm_cost_usd Float32                    -- LLM API cost for this prediction
) ENGINE=MergeTree
ORDER BY (pair, horizon, ts)
COMMENT 'Combined ML + LLM predictions with fusion details';

-- Create indexes for common queries
-- (ClickHouse uses ORDER BY for primary indexing, but we can add projections for optimization)

-- Materialized view: Aggregate sentiment by pair and hour
CREATE MATERIALIZED VIEW IF NOT EXISTS fxai.mv_sentiment_hourly
ENGINE = SummingMergeTree
ORDER BY (pair, hour_ts)
AS
SELECT
  toStartOfHour(s.ts) AS hour_ts,
  n.pair AS pair,  -- Derived from news content analysis
  avg(s.sentiment_overall) AS avg_sentiment,
  count() AS news_count,
  sum(if(s.impact_score > 7, 1, 0)) AS high_impact_count,
  avg(s.confidence) AS avg_confidence
FROM fxai.sentiment_scores s
JOIN (
  SELECT id, 
         arrayElement(splitByChar('/', url), -1) AS pair_hint
  FROM fxai.news_items
) n ON s.news_id = n.id
WHERE n.pair_hint != ''
GROUP BY hour_ts, pair;

-- Helper function to extract pair from news content (simplified)
-- In production, this would be done by LLM entity extraction
