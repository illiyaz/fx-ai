# Product Requirements Document (PRD)
## FX-AI Advisor — AI-Powered Trading Advisory System

**Version:** 1.0  
**Last Updated:** November 28, 2025  
**Status:** MVP Complete  
**Document Owner:** Product Team  

---

## 📋 Executive Summary

### Product Vision
FX-AI Advisor is an AI-powered foreign exchange trading advisory platform that provides real-time, data-driven recommendations to help traders make informed decisions in the FX markets. The system combines machine learning, technical analysis, and macroeconomic event awareness to deliver actionable trading signals with clear explanations.

### Business Objectives
1. **Reduce Decision Latency**: Provide sub-second forecast generation for time-sensitive trading decisions
2. **Improve Trading Outcomes**: Achieve >60% win rate on backtested strategies after spread costs
3. **Risk Mitigation**: Prevent trades during high-volatility macro events through intelligent embargo logic
4. **Transparency**: Deliver explainable recommendations with plain-English action hints
5. **Scalability**: Support multiple currency pairs and time horizons with minimal infrastructure overhead

### Success Metrics
- **API Response Time**: <500ms for forecast generation (p95)
- **Model Performance**: AUC >0.55, Brier Score <0.25
- **Backtest Win Rate**: >60% after 2 bps spread costs
- **System Uptime**: 99.5% availability
- **Data Quality**: <1% validation errors in ingested data

---

## 🎯 Problem Statement

### Current Challenges in FX Trading

**1. Information Overload**
- Traders face overwhelming amounts of price data, news, and economic indicators
- Difficulty synthesizing multiple data sources into actionable decisions
- Time-sensitive nature of FX markets requires rapid analysis

**2. Emotional Decision-Making**
- Fear and greed drive suboptimal trading decisions
- Lack of systematic approach leads to inconsistent results
- Difficulty maintaining discipline during volatile market conditions

**3. Event Risk**
- Macro events (central bank decisions, economic releases) cause unpredictable volatility
- Traders often caught off-guard by scheduled high-impact events
- Need for event-aware trading strategies

**4. Lack of Backtesting Infrastructure**
- Difficult to validate trading strategies historically
- No systematic way to measure strategy performance
- Inability to optimize decision thresholds

### Target Users

**Primary Users**
- **Retail FX Traders**: Individual traders seeking data-driven decision support
- **Corporate Treasury Teams**: Companies managing FX exposure for international operations
- **Small Trading Firms**: Boutique firms lacking sophisticated ML infrastructure

**Secondary Users**
- **Financial Advisors**: Professionals advising clients on FX positions
- **Research Analysts**: Teams studying FX market dynamics

---

## 🏗️ Product Architecture

### System Components

#### 1. Data Ingestion Layer
**Purpose**: Collect and normalize price data and macro events

**Components**:
- **Tick Data Ingestion**: Real-time bid/ask/spread capture
- **Macro Event Loader**: Economic calendar integration (CSV/API/ICS)
- **Data Validation**: Quality checks on ingested data

**Data Sources**:
- FX price feeds (demo generator for MVP)
- Economic calendars (ForexFactory, Investing.com, etc.)
- Central bank announcements

**Tables**:
- `fxai.bars_raw` - Raw tick data (30-day retention)
- `fxai.bars_1m` - 1-minute OHLC bars (180-day retention)
- `fxai.macro_events` - Economic calendar (365-day retention)

#### 2. Feature Engineering Layer
**Purpose**: Transform raw data into ML-ready features

**Feature Categories**:

| Category | Features | Description |
|----------|----------|-------------|
| **Returns** | `ret_1m`, `ret_5m`, `ret_15m` | Price changes over multiple timeframes |
| **Volatility** | `vol_5m`, `vol_15m` | Rolling standard deviation of returns |
| **Trend** | `sma_5`, `sma_15` | Simple moving averages |
| **Momentum** | `momentum_15m` | Price deviation from moving average |
| **Event Proximity** | `minutes_to_event`, `is_high_importance` | Time to next macro event |

**Processing**:
- Continuous computation via featurizer daemon
- Materialized view for 1-minute bar aggregation
- Event proximity calculated via as-of join with macro calendar

**Storage**:
- `fxai.features_1m` - Feature store with sub-second query performance

#### 3. Machine Learning Layer
**Purpose**: Generate probabilistic forecasts

**Model Types**:

**A. LightGBM Classifier** (Primary)
- Binary classification: price up vs. down over horizon
- Horizons: 30m, 1h, 2h, 4h
- Training: Time-ordered 80/20 split
- Metrics: AUC, Brier score
- Output: Calibrated probabilities

**B. Baseline Predictor** (Fallback)
- Rolling mean prediction
- Used when no trained model available
- Conservative: prob_up=0.5, expected_delta=0

**Model Registry**:
- `fxai.models` table tracks all trained models
- Metadata: algorithm, horizon, training window, metrics
- File storage: `models/lgbm_{pair}_{horizon}_{timestamp}.pkl`

**Model Selection Logic**:
1. Explicit `model_id` query parameter
2. Environment variable `DEFAULT_MODEL_ID`
3. Latest model for requested horizon
4. Fallback to baseline

#### 4. Decision Engine
**Purpose**: Convert predictions into actionable recommendations

**Decision Policies**:

**Policy: "expected"** (Default)
```
IF |expected_delta_bps| > spread_bps:
    recommendation = NOW
ELSE:
    recommendation = WAIT
```

**Policy: "prob"**
```
IF prob_up >= prob_th OR prob_up <= (1 - prob_th):
    recommendation = NOW
ELSE:
    recommendation = WAIT
```

**Embargo Logic**:
```
IF minutes_to_event <= embargo_min AND importance = 'high':
    recommendation = WAIT (override)
    explanation += "embargo: event proximity"
```

**Direction & Action Hints**:
- **UP**: Base currency strengthens → "If buying base, act sooner; if selling, delay"
- **DOWN**: Base currency weakens → "If selling base, act sooner; if buying, wait"

**Output Storage**:
- `fxai.decisions` - All forecast decisions logged for backtesting

#### 5. API Layer
**Purpose**: Expose forecasts via REST API

**Endpoints**:

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/health` | GET | Health check | No |
| `/v1/forecast` | GET | Get trading forecast | Yes |
| `/v1/bars/recent` | GET | Recent OHLC data | Yes |
| `/v1/validations/recent` | GET | Data quality issues | Yes |

**Authentication**: API key via `X-API-Key` header

**Response Format**:
```json
{
  "pair": "USDINR",
  "horizon": "4h",
  "prob_up": 0.62,
  "expected_delta_bps": 3.5,
  "recommendation": "NOW",
  "direction": "UP",
  "action_hint": "USD likely to strengthen vs INR...",
  "model_id": "lgbm_USDINR_4h_20250830084022",
  "explanation": [...]
}
```

#### 6. Backtesting Framework
**Purpose**: Validate strategies on historical data

**Metrics**:
- **Win Rate**: Fraction of profitable trades after spread
- **Average PnL**: Mean profit/loss per trade (bps)
- **Median PnL**: Robust measure of central tendency
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough decline

**Storage**:
- `fxai.backtest_metrics` - Individual backtest runs
- `fxai.backtest_summary` - Aggregated performance metrics

**Execution**:
- CLI tool for ad-hoc backtests
- Daemon for continuous evaluation

#### 7. Alerting System
**Purpose**: Notify users of high-conviction signals

**Alert Triggers**:
- `recommendation = NOW` with high confidence
- Significant expected move (>5 bps)
- Direction change from previous forecast

**Delivery Channels**:
- Stdout (MVP)
- Webhook (future)
- Email/SMS (future)

**Deduplication**:
- Unique on (decision_ts, pair, horizon)
- Prevents alert spam

**Storage**:
- `fxai.alerts` - Alert delivery log (90-day retention)

---

## 🔄 User Workflows

### Workflow 1: Get Trading Recommendation

**Actor**: Retail Trader  
**Goal**: Decide whether to buy/sell USDINR now or wait

**Steps**:
1. Trader calls `/v1/forecast?pair=USDINR&h=4h`
2. System fetches latest features for USDINR
3. System loads best available model for 4h horizon
4. Model generates probability and expected move
5. Decision engine applies policy and embargo checks
6. System returns recommendation with explanation
7. Trader reviews action hint and makes decision
8. Decision logged to `fxai.decisions` for backtesting

**Success Criteria**:
- Response time <500ms
- Clear recommendation (NOW/WAIT)
- Explainable reasoning
- Plain-English action guidance

### Workflow 2: Train New Model

**Actor**: Data Scientist  
**Goal**: Improve forecast accuracy with updated model

**Steps**:
1. Ensure sufficient historical data (>14 days of bars and features)
2. Run `make train-lgbm PAIR=USDINR H=4h LB=336`
3. System loads features and labels from ClickHouse
4. LightGBM trains on time-ordered 80/20 split
5. Model evaluated on validation set (AUC, Brier)
6. Model serialized to `models/` directory
7. Metadata written to `fxai.models` registry
8. System automatically uses new model for future forecasts

**Success Criteria**:
- AUC >0.55 on validation set
- Brier score <0.25
- Model registered with complete metadata
- No degradation in API performance

### Workflow 3: Backtest Strategy

**Actor**: Quant Analyst  
**Goal**: Validate strategy performance over past 24 hours

**Steps**:
1. Run `make backtest PAIR=USDINR H=4h LB=24`
2. System loads historical decisions from `fxai.decisions`
3. System loads realized price moves from `fxai.bars_1m`
4. For each decision, calculate PnL after spread costs
5. Aggregate metrics: win rate, avg PnL, median PnL
6. Display results and optionally write to `fxai.backtest_metrics`
7. Analyst reviews performance and adjusts thresholds

**Success Criteria**:
- Win rate >60% after spread
- Positive average PnL
- Sufficient trade count (>10) for statistical significance

### Workflow 4: Monitor Data Quality

**Actor**: Operations Engineer  
**Goal**: Ensure data pipeline health

**Steps**:
1. Check validation table: `make tail-valid`
2. Review recent errors (spread anomalies, NaN values, timestamp issues)
3. Investigate root cause (data source, ingestion bug, etc.)
4. Fix issue and verify data quality restored
5. Monitor ongoing via validation count: `make count-valid`

**Success Criteria**:
- <1% validation error rate
- No critical errors (level='error')
- Quick detection and resolution of issues

---

## 📊 Functional Requirements

### FR-1: Data Ingestion

**FR-1.1**: System SHALL ingest FX tick data (bid, ask, spread) in real-time  
**FR-1.2**: System SHALL aggregate ticks into 1-minute OHLC bars via materialized view  
**FR-1.3**: System SHALL load macro events from CSV/API/ICS sources  
**FR-1.4**: System SHALL validate all ingested data for quality issues  
**FR-1.5**: System SHALL log validation errors to `fxai.validations` table  

**Priority**: P0 (Critical)

### FR-2: Feature Engineering

**FR-2.1**: System SHALL compute returns over 1m, 5m, 15m windows  
**FR-2.2**: System SHALL compute rolling volatility over 5m, 15m windows  
**FR-2.3**: System SHALL compute simple moving averages (5, 15 periods)  
**FR-2.4**: System SHALL compute momentum as price deviation from SMA  
**FR-2.5**: System SHALL compute minutes to next high-importance macro event  
**FR-2.6**: System SHALL flag bars within 90 minutes of high-importance events  
**FR-2.7**: System SHALL store features in `fxai.features_1m` table  
**FR-2.8**: System SHALL support continuous feature computation via daemon  

**Priority**: P0 (Critical)

### FR-3: Model Training

**FR-3.1**: System SHALL support training LightGBM binary classifiers  
**FR-3.2**: System SHALL support horizons: 30m, 1h, 2h, 4h  
**FR-3.3**: System SHALL use time-ordered train/validation split (80/20)  
**FR-3.4**: System SHALL compute AUC and Brier score on validation set  
**FR-3.5**: System SHALL serialize trained models to disk  
**FR-3.6**: System SHALL register model metadata in `fxai.models` table  
**FR-3.7**: System SHALL support model versioning via timestamp-based IDs  

**Priority**: P0 (Critical)

### FR-4: Forecasting

**FR-4.1**: System SHALL generate probabilistic forecasts (prob_up)  
**FR-4.2**: System SHALL compute expected price change in basis points  
**FR-4.3**: System SHALL support model selection via query param, env var, or auto-selection  
**FR-4.4**: System SHALL fall back to baseline predictor if no model available  
**FR-4.5**: System SHALL return forecasts within 500ms (p95)  

**Priority**: P0 (Critical)

### FR-5: Decision Engine

**FR-5.1**: System SHALL support "expected" and "prob" decision policies  
**FR-5.2**: System SHALL generate NOW/WAIT/PARTIAL recommendations  
**FR-5.3**: System SHALL apply embargo logic for high-importance events  
**FR-5.4**: System SHALL compute direction (UP/DOWN) from model signal  
**FR-5.5**: System SHALL generate plain-English action hints  
**FR-5.6**: System SHALL log all decisions to `fxai.decisions` table  
**FR-5.7**: System SHALL support configurable thresholds (spread_bps, prob_th, embargo_min)  

**Priority**: P0 (Critical)

### FR-6: API

**FR-6.1**: System SHALL expose REST API on configurable port (default 8080)  
**FR-6.2**: System SHALL require API key authentication (except /health)  
**FR-6.3**: System SHALL return JSON responses with proper HTTP status codes  
**FR-6.4**: System SHALL support CORS for web client integration  
**FR-6.5**: System SHALL provide health check endpoint  
**FR-6.6**: System SHALL expose Prometheus metrics  

**Priority**: P0 (Critical)

### FR-7: Backtesting

**FR-7.1**: System SHALL support historical strategy evaluation  
**FR-7.2**: System SHALL compute win rate, avg PnL, median PnL  
**FR-7.3**: System SHALL account for spread costs in PnL calculation  
**FR-7.4**: System SHALL support probability and expected-move gating strategies  
**FR-7.5**: System SHALL write backtest results to `fxai.backtest_metrics`  
**FR-7.6**: System SHALL support continuous backtesting via daemon  

**Priority**: P1 (High)

### FR-8: Alerting

**FR-8.1**: System SHALL detect high-conviction trading signals  
**FR-8.2**: System SHALL deduplicate alerts on (decision_ts, pair, horizon)  
**FR-8.3**: System SHALL support stdout and webhook delivery  
**FR-8.4**: System SHALL log all alerts to `fxai.alerts` table  
**FR-8.5**: System SHALL support configurable alert criteria  

**Priority**: P2 (Medium)

### FR-9: Monitoring

**FR-9.1**: System SHALL track data quality via validation rules  
**FR-9.2**: System SHALL expose structured logs via structlog  
**FR-9.3**: System SHALL track API request/response metrics  
**FR-9.4**: System SHALL track model performance metrics  
**FR-9.5**: System SHALL support health checks for all services  

**Priority**: P1 (High)

---

## 🎨 Non-Functional Requirements

### NFR-1: Performance

**NFR-1.1**: API forecast endpoint SHALL respond in <500ms (p95)  
**NFR-1.2**: Feature computation SHALL complete in <10s for 360-minute lookback  
**NFR-1.3**: Model training SHALL complete in <5 minutes for 14-day dataset  
**NFR-1.4**: ClickHouse queries SHALL return in <100ms for typical workloads  
**NFR-1.5**: System SHALL support 100 concurrent API requests  

**Priority**: P0 (Critical)

### NFR-2: Scalability

**NFR-2.1**: System SHALL support multiple currency pairs (10+)  
**NFR-2.2**: System SHALL support multiple time horizons (4)  
**NFR-2.3**: System SHALL handle 1M+ bars per pair  
**NFR-2.4**: System SHALL support horizontal scaling of API servers  
**NFR-2.5**: System SHALL support distributed featurizer workers  

**Priority**: P1 (High)

### NFR-3: Reliability

**NFR-3.1**: System SHALL achieve 99.5% uptime  
**NFR-3.2**: System SHALL gracefully handle database connection failures  
**NFR-3.3**: System SHALL retry failed operations with exponential backoff  
**NFR-3.4**: System SHALL validate all inputs and handle errors gracefully  
**NFR-3.5**: System SHALL support zero-downtime deployments  

**Priority**: P0 (Critical)

### NFR-4: Security

**NFR-4.1**: System SHALL require API key authentication  
**NFR-4.2**: System SHALL support TLS encryption for external connections  
**NFR-4.3**: System SHALL sanitize all SQL inputs to prevent injection  
**NFR-4.4**: System SHALL not expose sensitive credentials in logs  
**NFR-4.5**: System SHALL support role-based access control (future)  

**Priority**: P0 (Critical)

### NFR-5: Maintainability

**NFR-5.1**: Code SHALL pass linting (ruff, mypy) with zero errors  
**NFR-5.2**: Code SHALL maintain >80% test coverage (future)  
**NFR-5.3**: System SHALL use structured logging for observability  
**NFR-5.4**: System SHALL document all configuration parameters  
**NFR-5.5**: System SHALL provide comprehensive README and PRD  

**Priority**: P1 (High)

### NFR-6: Data Quality

**NFR-6.1**: System SHALL achieve <1% validation error rate  
**NFR-6.2**: System SHALL detect and log spread anomalies  
**NFR-6.3**: System SHALL detect and log NaN/null values  
**NFR-6.4**: System SHALL detect and log non-monotonic timestamps  
**NFR-6.5**: System SHALL support data retention policies (TTL)  

**Priority**: P0 (Critical)

---

## 🗄️ Data Model

### Core Tables

#### bars_raw
**Purpose**: Staging table for raw tick data

| Column | Type | Description |
|--------|------|-------------|
| ts | DateTime64(3) | Timestamp (millisecond precision) |
| pair | LowCardinality(String) | Currency pair (e.g., USDINR) |
| bid | Float64 | Bid price |
| ask | Float64 | Ask price |
| mid | Float64 | Mid price (bid+ask)/2 |
| spread | Float32 | Spread (ask-bid) |
| src | LowCardinality(String) | Data source |

**Retention**: 30 days (TTL)  
**Order**: (pair, ts)

#### bars_1m
**Purpose**: Canonical 1-minute OHLC bars

| Column | Type | Description |
|--------|------|-------------|
| ts | DateTime | Timestamp (minute-aligned) |
| pair | LowCardinality(String) | Currency pair |
| open | Float64 | Open price |
| high | Float64 | High price |
| low | Float64 | Low price |
| close | Float64 | Close price |
| spread_avg | Float32 | Average spread |
| src | LowCardinality(String) | Data source |

**Retention**: 180 days (TTL)  
**Order**: (pair, ts)

#### features_1m
**Purpose**: Feature store for ML models

| Column | Type | Description |
|--------|------|-------------|
| ts | DateTime64(3) | Timestamp |
| pair | LowCardinality(String) | Currency pair |
| ret_1m | Float32 | 1-minute return |
| ret_5m | Float32 | 5-minute return |
| ret_15m | Float32 | 15-minute return |
| vol_5m | Float32 | 5-minute volatility |
| vol_15m | Float32 | 15-minute volatility |
| sma_5 | Float32 | 5-period SMA |
| sma_15 | Float32 | 15-period SMA |
| momentum_15m | Float32 | Momentum indicator |
| minutes_to_event | Int32 | Minutes to next high-impact event |
| is_high_importance | UInt8 | Flag: within 90min of event |

**Order**: (pair, ts)

#### macro_events
**Purpose**: Economic calendar data

| Column | Type | Description |
|--------|------|-------------|
| ts | DateTime | Event timestamp |
| currency | LowCardinality(String) | Currency (USD, INR, EUR, etc.) |
| country | LowCardinality(String) | Country code |
| event | String | Event name (e.g., "CPI YoY") |
| importance | Enum8 | low, medium, high |
| actual | String | Actual value (if released) |
| forecast | String | Forecast value |
| previous | String | Previous value |
| source | LowCardinality(String) | Data source |
| tags | Array(String) | Event tags |

**Retention**: 365 days (TTL)  
**Order**: (ts, currency)

#### decisions
**Purpose**: Forecast decision log

| Column | Type | Description |
|--------|------|-------------|
| ts | DateTime64(3) | Decision timestamp |
| pair | LowCardinality(String) | Currency pair |
| horizon | LowCardinality(String) | Forecast horizon |
| prior_prob_up | Float32 | Prior probability (before Bayes) |
| posterior_prob_up | Float32 | Posterior probability |
| expected_delta_bps | Float64 | Expected price change (bps) |
| range_p10 | Float32 | 10th percentile |
| range_p90 | Float32 | 90th percentile |
| shock_level | Enum8 | none, caution, high, critical |
| event_impact | Float32 | Event impact score |
| recommendation | LowCardinality(String) | NOW, WAIT, PARTIAL |
| explanation | String | Decision reasoning |
| policy_version | String | Model ID or policy version |

**Order**: (pair, horizon, ts)

#### models
**Purpose**: Model registry

| Column | Type | Description |
|--------|------|-------------|
| model_id | String | Unique model identifier |
| ts | DateTime | Registration timestamp |
| algo | String | Algorithm (LightGBM, etc.) |
| horizon | LowCardinality(String) | Forecast horizon |
| train_window | String | Training data window |
| metrics_json | String | Performance metrics (JSON) |
| params_json | String | Hyperparameters (JSON) |

**Order**: (model_id, ts)

#### backtest_metrics
**Purpose**: Backtest results

| Column | Type | Description |
|--------|------|-------------|
| ts | DateTime | Backtest timestamp |
| pair | LowCardinality(String) | Currency pair |
| horizon | LowCardinality(String) | Forecast horizon |
| lookback_hours | UInt32 | Evaluation window |
| prob_th | Float64 | Probability threshold |
| spread_bps | Float64 | Spread cost |
| trades | UInt32 | Number of trades |
| win_rate | Float64 | Win rate (0-1) |
| avg_pnl_bps | Float64 | Average PnL (bps) |
| med_pnl_bps | Float64 | Median PnL (bps) |

**Order**: (pair, horizon, ts)

#### alerts
**Purpose**: Alert delivery log

| Column | Type | Description |
|--------|------|-------------|
| ts | DateTime | Alert timestamp |
| decision_ts | DateTime | Source decision timestamp |
| pair | LowCardinality(String) | Currency pair |
| horizon | LowCardinality(String) | Forecast horizon |
| prob_up | Float64 | Probability up |
| expected_delta_bps | Float64 | Expected move (bps) |
| recommendation | String | NOW/WAIT |
| direction | LowCardinality(String) | UP/DOWN |
| action_hint | String | Plain-English guidance |
| model_id | String | Model used |
| explanation | String | Full explanation |
| embargo_applied | UInt8 | Embargo flag |
| sent | UInt8 | Delivery status |
| dest | LowCardinality(String) | Destination (stdout, webhook) |

**Retention**: 90 days (TTL)  
**Order**: (pair, horizon, decision_ts)

#### validations
**Purpose**: Data quality issues

| Column | Type | Description |
|--------|------|-------------|
| ts | DateTime64(3) | Issue timestamp |
| pair | LowCardinality(String) | Currency pair |
| rule | LowCardinality(String) | Validation rule name |
| level | Enum8 | info, warn, error |
| message | String | Error message |
| context_json | String | Debug context (JSON) |

**Retention**: 30 days (TTL)  
**Order**: (pair, ts)

---

## 🔌 API Specification

### Authentication

**Method**: API Key  
**Header**: `X-API-Key: {api_key}`  
**Configuration**: `.env` file, `API_KEY` variable  
**Default**: `changeme-dev-key` (development only)

### Endpoints

#### GET /health

**Description**: Health check endpoint  
**Authentication**: Not required  
**Rate Limit**: None

**Response** (200 OK):
```json
{
  "status": "ok",
  "env": "local"
}
```

#### GET /v1/forecast

**Description**: Get trading forecast and recommendation  
**Authentication**: Required  
**Rate Limit**: 100 requests/minute per API key

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| pair | string | Yes | - | Currency pair (USDINR, EURUSD, etc.) |
| h | string | No | 4h | Horizon (30m, 1h, 2h, 4h) |
| policy | string | No | expected | Decision policy (expected, prob) |
| spread_bps | float | No | 2.0 | Spread cost in basis points |
| prob_th | float | No | 0.6 | Probability threshold (prob policy) |
| model_id | string | No | null | Specific model to use |
| embargo_min | int | No | 0 | Embargo window in minutes |

**Response** (200 OK):
```json
{
  "pair": "USDINR",
  "horizon": "4h",
  "prob_up": 0.62,
  "expected_delta_bps": 3.5,
  "range": {
    "p10": -5.0,
    "p90": 5.0
  },
  "confidence": 0.2,
  "recommendation": "NOW",
  "explanation": [
    "model=lgbm_USDINR_4h_20250830084022",
    "policy=expected; spread_bps=2.0; prob_th=0.6",
    "dir=UP",
    "USD likely to strengthen vs INR. If you need to BUY USD, consider acting sooner; if you plan to SELL USD, delaying may help."
  ],
  "model_id": "lgbm_USDINR_4h_20250830084022",
  "direction": "UP",
  "action_hint": "USD likely to strengthen vs INR. If you need to BUY USD, consider acting sooner; if you plan to SELL USD, delaying may help."
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or missing API key
- `500 Internal Server Error`: Forecast generation failed

#### GET /v1/bars/recent

**Description**: Get recent OHLC bars  
**Authentication**: Required  
**Rate Limit**: 100 requests/minute per API key

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| pair | string | Yes | - | Currency pair |
| limit | int | No | 50 | Number of bars (1-1000) |

**Response** (200 OK):
```json
[
  {
    "ts": "2025-11-28T14:30:00",
    "pair": "USDINR",
    "open": 83.45,
    "high": 83.52,
    "low": 83.43,
    "close": 83.50,
    "spread_avg": 0.02
  },
  ...
]
```

#### GET /v1/validations/recent

**Description**: Get recent data quality issues  
**Authentication**: Required  
**Rate Limit**: 100 requests/minute per API key

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| pair | string | No | null | Filter by currency pair |
| limit | int | No | 50 | Number of records (1-1000) |

**Response** (200 OK):
```json
[
  {
    "ts": "2025-11-28T14:30:00",
    "pair": "USDINR",
    "rule": "spread_sanity",
    "level": "warn",
    "message": "Spread exceeds 5 bps: 6.2 bps"
  },
  ...
]
```

---

## 🧪 Testing Strategy

### Unit Tests

**Coverage Target**: 80%

**Test Categories**:
- Feature computation logic
- Model prediction interface
- Decision policy logic
- API request/response validation
- Data validation rules

**Framework**: pytest

**Example**:
```python
def test_feature_computation():
    bars = create_sample_bars()
    features = compute_features(bars, "USDINR")
    assert "ret_1m" in features.columns
    assert features["ret_1m"].notna().all()
```

### Integration Tests

**Test Scenarios**:
- End-to-end forecast generation
- Database read/write operations
- Model loading and inference
- API authentication and authorization
- Worker daemon lifecycle

**Example**:
```python
def test_forecast_endpoint():
    response = client.get(
        "/v1/forecast?pair=USDINR&h=4h",
        headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 200
    assert "recommendation" in response.json()
```

### Performance Tests

**Benchmarks**:
- API response time: <500ms (p95)
- Feature computation: <10s for 360min lookback
- Model training: <5min for 14-day dataset
- Database queries: <100ms for typical workloads

**Tools**: pytest-benchmark, locust

### Backtest Validation

**Validation Criteria**:
- Win rate >60% after spread
- Positive average PnL
- Sharpe ratio >0.5
- Max drawdown <10 bps

**Frequency**: Daily automated backtests

---

## 🚀 Deployment Strategy

### Environments

#### Development
- Local Docker Compose
- Single-node ClickHouse
- Demo data generator
- Hot-reload for API

#### Staging
- Multi-container Docker setup
- Shared ClickHouse instance
- Real FX data feeds
- Continuous backtesting

#### Production
- Kubernetes cluster (future)
- ClickHouse cluster with replication
- Kafka cluster for streaming
- Load-balanced API servers
- Automated monitoring and alerting

### Deployment Process

1. **Code Review**: All changes reviewed via pull request
2. **CI Pipeline**: Lint, test, build Docker images
3. **Staging Deploy**: Automated deployment to staging
4. **Validation**: Smoke tests, backtest validation
5. **Production Deploy**: Blue-green deployment with rollback capability
6. **Monitoring**: Track metrics, logs, alerts for 24 hours

### Rollback Strategy

- **API**: Instant rollback via container orchestration
- **Models**: Revert to previous model_id via env var
- **Database**: Schema changes use backward-compatible migrations
- **Workers**: Graceful shutdown with signal handling

---

## 📈 Success Metrics & KPIs

### Product Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **API Uptime** | 99.5% | Prometheus uptime metric |
| **Forecast Accuracy (AUC)** | >0.55 | Model validation metrics |
| **Backtest Win Rate** | >60% | Daily backtest results |
| **API Response Time (p95)** | <500ms | Prometheus latency metric |
| **Data Quality** | <1% errors | Validation error rate |

### Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Active Users** | 100 (6 months) | API key usage tracking |
| **API Requests/Day** | 10,000 | Request count metric |
| **User Retention** | >70% (monthly) | Active users month-over-month |
| **Average Session Length** | >5 minutes | Session duration tracking |

### Technical Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Database Query Time** | <100ms (p95) | ClickHouse query logs |
| **Feature Computation Time** | <10s | Worker execution time |
| **Model Training Time** | <5 minutes | Training job duration |
| **Alert Delivery Time** | <5s | Alert timestamp delta |

---

## 🛣️ Roadmap

### Phase 1: MVP (Complete) ✅
- [x] Core data pipeline (ingestion, features, models)
- [x] LightGBM classifier training
- [x] REST API with forecast endpoint
- [x] Decision engine with embargo logic
- [x] Backtesting framework
- [x] Basic alerting system
- [x] Docker Compose deployment

### Phase 2: Enhancement (Q1 2026)
- [ ] Additional currency pairs (EURUSD, GBPUSD, JPYUSD)
- [ ] Advanced models (XGBoost, neural networks)
- [ ] Bayesian posterior updates with news sentiment
- [ ] Webhook alert delivery
- [ ] Web dashboard for visualization
- [ ] Real-time FX data feed integration
- [ ] Expanded backtesting metrics (Sharpe, drawdown)

### Phase 3: Scale (Q2 2026)
- [ ] Kubernetes deployment
- [ ] ClickHouse cluster with replication
- [ ] Kafka cluster for streaming
- [ ] Multi-region deployment
- [ ] Advanced monitoring (Grafana dashboards)
- [ ] User authentication and RBAC
- [ ] Rate limiting and quota management

### Phase 4: Intelligence (Q3 2026)
- [ ] Reinforcement learning for decision optimization
- [ ] Multi-asset correlation analysis
- [ ] Portfolio-level recommendations
- [ ] Explainable AI (SHAP values)
- [ ] Automated model retraining
- [ ] A/B testing framework for models

### Phase 5: Enterprise (Q4 2026)
- [ ] SaaS offering with tiered pricing
- [ ] White-label solution for brokers
- [ ] Mobile app (iOS/Android)
- [ ] Advanced analytics and reporting
- [ ] Custom model training for enterprise clients
- [ ] 24/7 support and SLA guarantees

---

## 🔒 Security & Compliance

### Security Measures

**Authentication & Authorization**:
- API key authentication for all endpoints
- TLS encryption for external connections
- SQL injection prevention via parameterized queries
- Secrets management via environment variables

**Data Protection**:
- No storage of personally identifiable information (PII)
- Data retention policies with TTL
- Encrypted backups (future)
- Access logging and audit trails

**Infrastructure Security**:
- Docker container isolation
- Network segmentation
- Regular security updates
- Vulnerability scanning (future)

### Compliance Considerations

**Data Privacy**:
- GDPR compliance (if serving EU users)
- Data minimization principles
- Right to erasure support

**Financial Regulations**:
- Disclaimer: System provides information, not financial advice
- No direct trading execution
- User responsibility for trading decisions

**Audit Requirements**:
- Complete decision audit trail in `fxai.decisions`
- Model versioning and registry
- Backtest result preservation

---

## 📚 Documentation

### User Documentation
- **README.md**: Quick start and overview
- **API Reference**: Endpoint specifications and examples
- **User Guide**: How to interpret forecasts and recommendations
- **FAQ**: Common questions and troubleshooting

### Developer Documentation
- **PRD** (this document): Product requirements and architecture
- **Architecture Diagram**: System component overview
- **Database Schema**: Table definitions and relationships
- **Deployment Guide**: Infrastructure setup and configuration
- **Contributing Guide**: Code standards and PR process

### Operational Documentation
- **Runbook**: Common operational tasks and procedures
- **Monitoring Guide**: Metrics, alerts, and dashboards
- **Incident Response**: Escalation and resolution procedures
- **Backup & Recovery**: Data protection procedures

---

## 🤝 Stakeholders

### Product Team
- **Product Manager**: Define requirements, prioritize features
- **UX Designer**: Design user interfaces and workflows (future)
- **Product Analyst**: Track metrics and user behavior

### Engineering Team
- **Backend Engineers**: API, data pipeline, ML infrastructure
- **Data Scientists**: Model development and evaluation
- **DevOps Engineers**: Infrastructure, deployment, monitoring
- **QA Engineers**: Testing, validation, quality assurance

### Business Team
- **Sales**: Customer acquisition and onboarding
- **Customer Success**: User support and training
- **Marketing**: Product positioning and content

### External Stakeholders
- **Users**: Retail traders, corporate treasury teams
- **Data Providers**: FX feed vendors, economic calendar APIs
- **Compliance**: Legal and regulatory advisors

---

## 📞 Support & Feedback

### Support Channels
- **Documentation**: README.md, API reference, user guide
- **GitHub Issues**: Bug reports and feature requests
- **Email**: support@fx-ai-advisor.com (future)
- **Community Forum**: User discussions and best practices (future)

### Feedback Collection
- **User Surveys**: Quarterly satisfaction surveys
- **Usage Analytics**: API request patterns and feature adoption
- **Backtest Results**: Model performance tracking
- **Feature Requests**: GitHub issues and community voting

---

## 📝 Appendix

### Glossary

**Terms**:
- **Basis Point (bps)**: 1/100th of a percent (0.01%)
- **Embargo**: Temporary restriction on trading near high-impact events
- **Horizon**: Time period for forecast (30m, 1h, 2h, 4h)
- **OHLC**: Open, High, Low, Close (bar data)
- **Spread**: Difference between bid and ask price
- **Win Rate**: Fraction of profitable trades after costs

**Metrics**:
- **AUC**: Area Under ROC Curve (model discrimination)
- **Brier Score**: Calibration quality (lower is better)
- **Sharpe Ratio**: Risk-adjusted return measure
- **Max Drawdown**: Largest peak-to-trough decline

### References

**Technical Documentation**:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [ClickHouse Documentation](https://clickhouse.com/docs)
- [LightGBM Documentation](https://lightgbm.readthedocs.io/)
- [Redpanda Documentation](https://docs.redpanda.com/)

**Research Papers**:
- "Machine Learning for Foreign Exchange Prediction"
- "Event-Driven Trading Strategies"
- "Calibration of Probabilistic Forecasts"

### Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-28 | Initial PRD for MVP | Product Team |

---

**Document Status**: ✅ Approved  
**Next Review**: 2026-01-28  
**Owner**: Product Team  
**Last Updated**: 2025-11-28
