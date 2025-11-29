# FX-AI Advisor — MVP

> **AI-powered foreign exchange trading advisory system** providing ML-based forecasts and decision recommendations for currency pairs.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![ClickHouse](https://img.shields.io/badge/ClickHouse-24.6-yellow.svg)](https://clickhouse.com/)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Data Pipeline](#data-pipeline)
- [API Documentation](#api-documentation)
- [Model Training](#model-training)
- [Backtesting](#backtesting)
- [Configuration](#configuration)
- [Development](#development)
- [Deployment](#deployment)
- [Monitoring](#monitoring)

## 🎯 Overview

FX-AI Advisor is a production-grade MVP that combines real-time feature engineering, machine learning forecasting, and policy-based decision-making to provide actionable trading recommendations for foreign exchange markets. The system focuses on the USDINR pair but is extensible to other currency pairs.

### Key Capabilities

- **Real-time Forecasting**: ML-powered predictions for multiple time horizons (30m, 1h, 2h, 4h)
- **Decision Recommendations**: Clear NOW/WAIT signals with plain-English action hints
- **Macro Event Integration**: Incorporates economic calendar data and embargo logic
- **Backtesting Framework**: Comprehensive strategy evaluation with PnL tracking
- **Feature Engineering**: Automated computation of technical indicators and event proximity
- **Model Registry**: Version-controlled ML models with metadata tracking

## ✨ Features

### Trading Intelligence
- 🎯 **Probabilistic Forecasts**: Calibrated probability of price movements
- 📊 **Expected Returns**: Basis point predictions with confidence ranges
- 🚦 **Smart Recommendations**: Policy-based NOW/WAIT decisions
- 📅 **Event-Aware**: Automatic embargo near high-impact macro events
- 🔄 **Multi-Horizon**: Support for 30m, 1h, 2h, and 4h forecasts

### Technical Features
- ⚡ **High Performance**: ClickHouse for sub-second queries on time-series data
- 🔄 **Real-time Processing**: Streaming architecture with Kafka/Redpanda
- 🤖 **ML Pipeline**: LightGBM models with automated training and registry
- 📈 **Feature Store**: Pre-computed rolling indicators and event proximity
- 🧪 **Backtesting**: Historical performance validation with spread costs
- 🔍 **Data Quality**: Automated validation and anomaly detection

## 🏗️ Architecture

### Tech Stack

**Backend & API**
- FastAPI 0.115+ (REST API)
- Uvicorn (ASGI server)
- Pydantic 2.7+ (data validation)

**Data Storage**
- ClickHouse 24.6 (time-series database)
- Redpanda (Kafka-compatible streaming)

**Machine Learning**
- LightGBM 4.3+ (gradient boosting)
- scikit-learn 1.5+ (ML utilities)
- pandas, numpy (data processing)

**Infrastructure**
- Docker & Docker Compose
- Python 3.11+

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│  FastAPI (/v1/forecast, /v1/bars/recent, /health)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Feature Engineering                       │
│  Rolling Stats │ Macro Proximity │ Technical Indicators     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      ML Models                               │
│  LightGBM Classifier │ Baseline │ Model Registry            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Decision Engine                            │
│  Policy Rules │ Embargo Logic │ Recommendation Generator    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ClickHouse (bars, features, decisions, models, alerts)     │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Make (optional, for convenience commands)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd fx-ai
```

2. **Create virtual environment and install dependencies**
```bash
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
make deps
```

3. **Start infrastructure services**
```bash
make up        # Start ClickHouse + Redpanda + Console
make initdb    # Initialize database schema
```

4. **Verify installation**
```bash
make venvcheck  # Check Python dependencies
make dbcheck    # Check ClickHouse connection
```

### Running the System

**Start the API server**
```bash
make api
# API available at http://localhost:8080
```

**Ingest demo data**
```bash
make ingest-demo          # Generate demo tick data
make load-macro           # Load macro events from CSV
```

**Compute features**
```bash
make featurize            # One-time feature computation
make featurizer-daemon    # Continuous feature updates
```

**Test the API**
```bash
make curl-health          # Health check
make curl-forecast        # Get forecast for USDINR 4h
```

## 📁 Project Structure

```
fx-ai/
├── apps/
│   ├── api/                    # FastAPI application
│   │   └── main.py            # API endpoints & request handlers
│   ├── common/                 # Shared utilities
│   │   ├── clickhouse_client.py  # Database client
│   │   ├── schemas.py         # Pydantic models
│   │   └── validators.py      # Data validation
│   ├── features/               # Feature engineering
│   │   ├── featurize.py       # Feature computation logic
│   │   └── labels.py          # Label generation for training
│   ├── train/                  # Model training
│   │   └── train_lgbm.py      # LightGBM training pipeline
│   ├── backtest/               # Backtesting framework
│   │   └── quick_check.py     # Strategy evaluation
│   ├── ingestion/              # Data ingestion
│   │   ├── demo_ingest.py     # Demo tick generator
│   │   └── macro_loader.py    # Macro events loader
│   ├── workers/                # Background daemons
│   │   ├── featurizer_daemon.py   # Feature computation worker
│   │   ├── backtest_daemon.py     # Backtest worker
│   │   └── alerter_daemon.py      # Alert delivery worker
│   └── models/                 # Model utilities
│       ├── baselines.py       # Baseline predictors
│       └── loader.py          # Model loading & inference
├── config/                     # Configuration files
│   ├── policy_v1.1.yaml       # Decision policy parameters
│   └── impact_map.yaml        # Macro event impact scoring
├── infra/
│   ├── docker/
│   │   └── compose.yml        # Docker Compose configuration
│   └── sql/
│       └── init.sql           # Database schema
├── models/                     # Trained model artifacts
│   └── *.pkl                  # Serialized models
├── data/                       # Sample data
│   └── macro_events_sample.csv
├── tests/                      # Test suite
├── .env                        # Environment variables
├── Dockerfile                  # Container image definition
├── Makefile                    # Task automation
├── pyproject.toml             # Python project configuration
└── README.md                  # This file
```

## 🔄 Data Pipeline

### 1. Data Ingestion

**Price Data Flow**
```
Raw Ticks (bid/ask/spread)
    ↓
fxai.bars_raw (staging table)
    ↓ [Materialized View]
fxai.bars_1m (OHLC 1-minute bars)
```

**Macro Events**
```
CSV/API/ICS Sources
    ↓
fxai.macro_events (economic calendar)
```

**Ingestion Commands**
```bash
# Generate demo tick data
make ingest-demo

# Load macro events from CSV
make load-macro CSV=data/macro_events_sample.csv

# Check data
make rows-1m      # Count 1-minute bars
make tail-1m      # View recent bars
make tail-macro   # View recent macro events
```

### 2. Feature Engineering

**Computed Features** (stored in `fxai.features_1m`):

| Feature | Description |
|---------|-------------|
| `ret_1m`, `ret_5m`, `ret_15m` | Returns over 1, 5, 15 minutes |
| `vol_5m`, `vol_15m` | Rolling volatility (std of 1m returns) |
| `sma_5`, `sma_15` | Simple moving averages |
| `momentum_15m` | Price - SMA(15) |
| `minutes_to_event` | Minutes to next high-importance macro event |
| `is_high_importance` | Binary flag if within 90 minutes of event |

**Feature Computation**
```bash
# One-time computation
make featurize PAIR=USDINR

# Backfill historical features
make backfill-features PAIR=USDINR MINUTES=10080

# Start continuous daemon
make featurizer-daemon PAIRS=USDINR INTERVAL=60 LOOKBACK=360

# Docker worker
make worker-up
make worker-logs
```

### 3. Model Training

**Training Pipeline**
```bash
# Train LightGBM model
make train-lgbm PAIR=USDINR H=4h LB=336

# Parameters:
# PAIR   - Currency pair (default: USDINR)
# H      - Horizon: 30m, 1h, 2h, 4h (default: 4h)
# LB     - Lookback hours for training data (default: 336 = 14 days)
```

**Model Registry**
- Models saved to `models/lgbm_{pair}_{horizon}_{timestamp}.pkl`
- Metadata tracked in `fxai.models` table
- Includes: model_id, algorithm, horizon, training window, metrics (AUC, Brier score)

**View Models**
```bash
make models-tail              # View recent models
make model-latest-id H=4h     # Get latest model ID for horizon
```

### 4. Forecasting & Decisions

**Decision Flow**
```
Latest Features
    ↓
Model Prediction (prob_up, expected_delta_bps)
    ↓
Policy Engine (embargo check, threshold comparison)
    ↓
Recommendation (NOW/WAIT) + Direction + Action Hint
    ↓
fxai.decisions (logged for backtesting)
```

**Decision Policies**

**Policy: "expected"** (default)
- Act if `|expected_delta_bps| > spread_bps`
- Threshold: 2.0 bps (configurable via `DECISION_SPREAD_BPS`)

**Policy: "prob"**
- Act if `prob_up >= prob_th` or `prob_up <= (1 - prob_th)`
- Threshold: 0.6 (configurable via `DECISION_PROB_TH`)

**Embargo Logic**
- Force WAIT if high-importance macro event within X minutes
- Default: 0 minutes (disabled), configurable via `DECISION_EMBARGO_MIN`

## 📡 API Documentation

### Base URL
```
http://localhost:8080
```

### Authentication
All endpoints (except `/health`) require API key authentication:
```bash
X-API-Key: changeme-dev-key
```

### Endpoints

#### `GET /health`
Health check endpoint.

**Response**
```json
{
  "status": "ok",
  "env": "local"
}
```

#### `GET /v1/forecast`
Get trading forecast and recommendation.

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pair` | string | required | Currency pair (e.g., USDINR) |
| `h` | string | `4h` | Horizon: 30m, 1h, 2h, 4h |
| `policy` | string | `expected` | Decision policy: expected, prob |
| `spread_bps` | float | `2.0` | Spread cost in basis points |
| `prob_th` | float | `0.6` | Probability threshold for prob policy |
| `model_id` | string | `null` | Specific model ID to use |
| `embargo_min` | int | `0` | Embargo window in minutes |

**Example Request**
```bash
curl -H "X-API-Key: changeme-dev-key" \
  "http://localhost:8080/v1/forecast?pair=USDINR&h=4h&policy=expected&spread_bps=2.0"
```

**Example Response**
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

**Response Fields**
- `prob_up`: Probability price moves up (0-1)
- `expected_delta_bps`: Expected price change in basis points
- `recommendation`: `NOW` (act), `WAIT` (hold), or `PARTIAL` (insufficient data)
- `direction`: `UP` or `DOWN`
- `action_hint`: Plain-English guidance for traders
- `model_id`: Which model generated the forecast

#### `GET /v1/bars/recent`
Get recent OHLC bars.

**Query Parameters**
- `pair` (required): Currency pair
- `limit` (default: 50, max: 1000): Number of bars

**Example**
```bash
curl -H "X-API-Key: changeme-dev-key" \
  "http://localhost:8080/v1/bars/recent?pair=USDINR&limit=10"
```

#### `GET /v1/validations/recent`
Get recent data quality validation issues.

**Query Parameters**
- `pair` (optional): Filter by currency pair
- `limit` (default: 50, max: 1000): Number of records

## 🎓 Model Training

### Training Process

1. **Prepare Data**
```bash
# Ensure you have sufficient bars and features
make rows-1m
make tail-features
```

2. **Train Model**
```bash
make train-lgbm PAIR=USDINR H=4h LB=336
```

3. **Verify Model**
```bash
make models-tail
```

### Model Architecture

**LightGBM Binary Classifier**
- **Task**: Predict if price moves up or down over horizon
- **Features**: 10 features (returns, volatility, SMAs, momentum, event proximity)
- **Training**: Time-ordered 80/20 train/validation split
- **Hyperparameters**:
  - `n_estimators`: 200
  - `learning_rate`: 0.05
  - `max_depth`: -1 (no limit)
  - `subsample`: 0.9
  - `colsample_bytree`: 0.9
  - `class_weight`: balanced

**Metrics**
- **AUC**: Area under ROC curve (discrimination)
- **Brier Score**: Calibration quality (lower is better)

### Baseline Models

When no trained model is available, the system uses a baseline predictor:
- Returns `prob_up = 0.5` (neutral)
- Returns `expected_delta_bps = 0.0` (no expected move)
- Recommendation typically: `WAIT`

## 🧪 Backtesting

### Running Backtests

**Quick Backtest**
```bash
make backtest PAIR=USDINR H=4h LB=24
```

**Parameterized Backtest**
```bash
make backtest-spread \
  PAIR=USDINR \
  H=4h \
  LB=24 \
  PROBTH=0.6 \
  SPREAD=2.0
```

**Continuous Backtesting (Docker)**
```bash
make backtester-up
make backtester-logs
```

### Backtest Metrics

**Output Example**
```
Backtest: pair=USDINR horizon=4h window=24h
Trades: 15 | Win rate: 0.667 | Avg PnL (bps): 1.85 | Median: 1.20
```

**Metrics Explained**
- **Trades**: Number of trades executed
- **Win Rate**: Fraction of profitable trades (after spread)
- **Avg PnL**: Mean profit/loss per trade in basis points
- **Median PnL**: Median profit/loss (robust to outliers)

**View Historical Results**
```bash
make decisions-by-horizon     # Decision count by horizon
make tail-decisions           # Recent decisions
make count-decisions          # Total decision count
```

### Backtest Strategies

**Strategy 1: Probability Threshold**
```bash
# Trade if prob_up >= 0.6 or prob_up <= 0.4
make backtest PAIR=USDINR H=4h LB=24 PROBTH=0.6
```

**Strategy 2: Expected Move Gating**
```bash
# Trade only if |expected_delta_bps| > spread_bps
python -m apps.backtest.quick_check \
  --pair USDINR \
  --horizon 4h \
  --lookback-hours 24 \
  --spread-bps 2.0 \
  --gate-by-expected \
  --write-metrics
```

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
# Application
APP_ENV=local
API_PORT=8080
API_KEY=changeme-dev-key

# ClickHouse
CLICKHOUSE_URL=http://localhost:8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DB=fxai

# Kafka/Redpanda
KAFKA_BROKERS=localhost:9092

# Decision Policy
DECISION_POLICY=expected          # expected | prob
DECISION_SPREAD_BPS=2.0           # Spread cost threshold
DECISION_PROB_TH=0.6              # Probability threshold
DECISION_EMBARGO_MIN=0            # Embargo window (minutes)
DEFAULT_MODEL_ID=                 # Optional: force specific model

# Workers
FEAT_PAIRS=USDINR                 # Comma-separated pairs
FEAT_INTERVAL_SEC=60              # Feature computation interval
FEAT_LOOKBACK_MIN=360             # Feature lookback window
```

### Policy Configuration (`config/policy_v1.1.yaml`)

```yaml
embargo:
  schedule_window_min: 10
  shock_levels_block: ["high", "critical"]

posterior_update:
  news_weight: 0.8
  shock_penalty:
    none: 0.0
    caution: 0.15
    high: 0.4
    critical: 0.8

decision_thresholds:
  wait: { prob_min: 0.62, exp_delta_bps_min: 8 }
  now: { prob_max: 0.38, exp_delta_bps_min: 8 }

range_widening_alpha: 0.35
```

### Macro Event Impact (`config/impact_map.yaml`)

Maps economic events to currency impact scores for better event-aware predictions.

## 🛠️ Development

### Code Quality

**Format Code**
```bash
make fmt     # Auto-fix with ruff, black, isort
```

**Lint & Type Check**
```bash
make lint    # ruff + mypy
```

**Run Tests**
```bash
make test
```

### Database Operations

**Query ClickHouse**
```bash
# Direct SQL
docker exec -i fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.bars_1m"

# Via Makefile
make rows-1m
make tail-1m
make tail-features
make tail-decisions
```

**Schema Migrations**
```bash
make migrate-decisions    # Add expected_delta_bps column
make migrate-backtest     # Create backtest_metrics table
```

### Alerts System

**Create Alerts Table**
```bash
make alerts-create
```

**Run Alerter Daemon**
```bash
make alerts-daemon

# With custom parameters
make alerts-run POLL=10 LBMIN=120
```

**View Alerts**
```bash
make alerts-tail
```

### Cleanup

**Clean Python Artifacts**
```bash
make clean
```

**Clear Caches**
```bash
make cache
```

**Stop Infrastructure**
```bash
make down    # Stop and remove containers + volumes
```

## 🚢 Deployment

### Docker Deployment

**Build Worker Images**
```bash
make worker-build
make backtester-build
```

**Start Workers**
```bash
make worker-up          # Featurizer daemon
make backtester-up      # Backtest daemon
```

**View Logs**
```bash
make worker-logs
make backtester-logs
make logs               # All services
```

### Production Considerations

**Security**
- Change `API_KEY` in production
- Use strong ClickHouse credentials
- Enable TLS for external connections
- Implement rate limiting on API endpoints

**Scalability**
- Run multiple featurizer workers for different pairs
- Horizontal scaling of API servers behind load balancer
- ClickHouse replication for high availability
- Kafka/Redpanda clustering for fault tolerance

**Monitoring**
- Prometheus metrics exposed by API
- ClickHouse query performance monitoring
- Worker health checks via Docker healthchecks
- Alert delivery tracking in `fxai.alerts` table

**Data Retention**
- `bars_raw`: 30 days (TTL configured)
- `bars_1m`: 180 days
- `macro_events`: 365 days
- `validations`: 30 days
- `alerts`: 90 days

## 📊 Monitoring

### Data Quality

**Validation Rules** (tracked in `fxai.validations`):
- Spread sanity checks
- NaN/null detection
- Non-monotonic timestamp detection
- Price jump anomalies

**View Validations**
```bash
make tail-valid       # Recent validation issues
make count-valid      # Summary by rule and level
```

### Performance Metrics

**API Metrics**
- Request latency
- Forecast generation time
- Model inference time
- Database query performance

**Model Metrics**
- AUC (discrimination)
- Brier score (calibration)
- Validation set size
- Training window coverage

**Backtest Metrics**
- Win rate
- Average PnL
- Sharpe ratio (in `fxai.backtest_summary`)
- Maximum drawdown

### Observability

**Structured Logging**
- JSON logs via `structlog`
- Request/response logging
- Error tracking with stack traces
- Performance timing logs

**Health Checks**
```bash
make curl-health      # API health
make dbcheck          # Database connectivity
make venvcheck        # Python environment
```

## 📚 Additional Resources

### Makefile Commands Reference

```bash
make help             # Show all available commands

# Development
make deps             # Install dependencies
make api              # Run API server
make fmt              # Format code
make lint             # Lint and type-check
make test             # Run tests

# Infrastructure
make up               # Start all services
make down             # Stop all services
make logs             # View logs
make initdb           # Initialize database

# Data
make ingest-demo      # Generate demo data
make load-macro       # Load macro events
make featurize        # Compute features

# Training & Backtesting
make train-lgbm       # Train model
make backtest         # Run backtest
make forecast-cli     # CLI forecast test

# Workers
make featurizer-daemon    # Run featurizer
make worker-up            # Start Docker worker
make alerts-daemon        # Run alerter

# Database Queries
make rows-1m          # Count bars
make tail-1m          # View recent bars
make tail-features    # View recent features
make tail-decisions   # View recent decisions
make models-tail      # View recent models
```

### Database Schema

See `infra/sql/init.sql` for complete schema definitions.

**Key Tables**:
- `fxai.bars_raw` - Raw tick data
- `fxai.bars_1m` - 1-minute OHLC bars
- `fxai.features_1m` - Computed features
- `fxai.macro_events` - Economic calendar
- `fxai.decisions` - Forecast decisions
- `fxai.models` - Model registry
- `fxai.backtest_metrics` - Backtest results
- `fxai.alerts` - Alert delivery log
- `fxai.validations` - Data quality issues

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code passes `make lint` and `make test`
- New features include tests
- Documentation is updated
- Commit messages are descriptive

## 📄 License

[Add your license information here]

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [ClickHouse](https://clickhouse.com/)
- [LightGBM](https://lightgbm.readthedocs.io/)
- [Redpanda](https://redpanda.com/)

---

**Note**: This is an MVP for educational and research purposes. Not financial advice. Always conduct your own research and risk assessment before making trading decisions