# -----------------------------
# FX-AI Makefile (MVP)
# -----------------------------

# Default shell
SHELL := /bin/bash
PY := .venv/bin/python

# Compose file (override by: make up COMPOSE=path.yml)
COMPOSE ?= infra/docker/compose.yml

# Backtest defaults (override via: make backtest-spread H=30m LB=6 PROBTH=0.58 SPREAD=2.5)
PAIR ?= USDINR
H ?= 4h
LB ?= 24
PROBTH ?= 0.6
SPREAD ?= 2.0

.PHONY: help deps run api fmt lint test clickhouse-up redpanda-up up down logs initdb env clean cache featurizer-daemon

# Load .env automatically if present
ifneq (,$(wildcard .env))
	include .env
	export
endif

help:
	@echo ""
	@echo "FX-AI Makefile Targets"
	@echo "----------------------"
	@echo "make deps          - Install project deps (editable) + dev extras"
	@echo "make api           - Run FastAPI (apps.api.main:app)"
	@echo "make run           - Alias for 'api'"
	@echo "make fmt           - Auto-fix formatting (ruff+black+isort)"
	@echo "make lint          - Lint & type-check"
	@echo "make test          - Run tests (quiet)"
	@echo "make up            - Start ClickHouse + Redpanda + Console"
	@echo "make down          - Stop and remove containers/volumes"
	@echo "make logs          - Follow docker-compose logs"
	@echo "make clickhouse-up - Start only ClickHouse"
	@echo "make redpanda-up   - Start only Redpanda"
	@echo "make initdb        - Apply ClickHouse schema"
	@echo "make env           - Show important env vars"
	@echo "make clean         - Clean Python build artifacts"
	@echo "make cache         - Clear pip & docker image caches (safe)"
	@echo "make featurizer-daemon - Run the featurizer daemon"
	@echo ""

# -----------------------------
# Dev Environment
# -----------------------------


deps:
	$(PY) -m pip install -U pip
	$(PY) -m pip install -e .[dev]
  
api:
	$(PY) -m uvicorn apps.api.main:app --host 0.0.0.0 --port $${API_PORT:-9090}

# Backward-compat alias
run: api
dep: deps

fmt:
	$(PY) -m ruff check --fix .
	$(PY) -m black .
	$(PY) -m isort .

lint:
	$(PY) -m ruff check .
	$(PY) -m mypy apps

test:
	$(PY) -m pytest -q || true

env:
	@echo "APP_ENV          = $${APP_ENV}"
	@echo "API_PORT         = $${API_PORT}"
	@echo "API_KEY          = $${API_KEY}"
	@echo "APP_API_PORT     = $${APP_API_PORT}"
	@echo "APP_API_KEY      = $${APP_API_KEY}"
	@echo "CLICKHOUSE_URL   = $${CLICKHOUSE_URL}"
	@echo "KAFKA_BROKERS    = $${KAFKA_BROKERS}"

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name ".pytest_cache" -type d -prune -exec rm -rf {} +
	rm -rf .mypy_cache dist build *.egg-info

cache:
	$(PY) -m pip cache purge || true
	docker image prune -f || true

# -----------------------------
# Local Infra (Docker Compose)
# -----------------------------

clickhouse-up:
	docker compose -f $(COMPOSE) up -d clickhouse

redpanda-up:
	docker compose -f $(COMPOSE) up -d redpanda

up:
	docker compose -f $(COMPOSE) up -d

logs:
	docker compose -f $(COMPOSE) logs -f

down:
	docker compose -f $(COMPOSE) down -v


initdb:
	docker exec -i fxai-clickhouse clickhouse-client -n < infra/sql/init.sql

venvcheck:
	which python
	$(PY) -c "import sys; print(sys.executable)"
	$(PY) -c "import fastapi, pydantic, pydantic_settings, uvicorn; print('deps OK')"

dbcheck:
	curl -s http://localhost:8123/ping || true
	echo
	curl -s "http://localhost:8123/?query=SHOW%20TABLES%20FROM%20fxai%20FORMAT%20Pretty" || true

curl-health:
	curl -s http://localhost:9090/health | jq . || curl -s http://localhost:9090/health

curl-forecast:
	curl -s -H "X-API-Key: $${API_KEY:-changeme-dev-key}" "http://localhost:9090/v1/forecast?pair=USDINR&h=4h" | jq . || \
	curl -s -H "X-API-Key: $${API_KEY:-changeme-dev-key}" "http://localhost:9090/v1/forecast?pair=USDINR&h=4h"


ingest-demo:
	$(PY) -m apps.ingestion.demo_ingest --pair USDINR --minutes 120 --interval-seconds 5

# Ingest historical data (use demo for now - replace with real data source later)
ingest-usdinr:
	@echo "Ingesting USDINR historical data (synthetic for demo)..."
	$(PY) -m apps.ingestion.demo_ingest --pair USDINR --minutes 2160 --interval-seconds 1
	@echo "✓ Ingested 2160 bars (90 days of hourly data)"

ingest-events:
	@echo "Ingesting macro events..."
	@if [ -f data/macro_events_sample.csv ]; then \
		$(PY) -m apps.ingestion.macro_loader --csv data/macro_events_sample.csv; \
	else \
		echo "⚠ No macro events CSV found. Skipping."; \
	fi

rows-raw:
	docker exec -i fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.bars_raw"

rows-1m:
	docker exec -i fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.bars_1m"

tail-1m:
	docker exec -i fxai-clickhouse clickhouse-client -q "SELECT ts,pair,open,high,low,close,spread_avg FROM fxai.bars_1m ORDER BY ts DESC LIMIT 5"

tail-valid:
	docker exec -i fxai-clickhouse clickhouse-client -q "SELECT ts, pair, rule, level, message FROM fxai.validations ORDER BY ts DESC LIMIT 10"

count-valid:
	docker exec -i fxai-clickhouse clickhouse-client -q "SELECT rule, level, count() FROM fxai.validations GROUP BY rule, level ORDER BY count() DESC"

load-macro:
	$(PY) -m apps.ingestion.macro_loader --csv $${CSV:-data/macro_events_sample.csv}

tail-macro:
	docker exec -i fxai-clickhouse clickhouse-client -q "SELECT ts,currency,country,event,importance FROM fxai.macro_events ORDER BY ts DESC LIMIT 10"

featurize:
	$(PY) -m apps.features.featurize --pair USDINR

train-baseline:
	@echo "stub: training script will arrive later (LightGBM/metrics)"

tail-features:
	docker exec -i fxai-clickhouse clickhouse-client -q "SELECT * FROM fxai.features_1m ORDER BY ts DESC LIMIT 5"

forecast-cli:
	curl -s -H "X-API-Key: $${API_KEY:-changeme-dev-key}" \
		"http://localhost:9090/v1/forecast?pair=USDINR&h=4h" | jq .

tail-decisions:
	docker exec -i fxai-clickhouse clickhouse-client -q "SELECT ts, pair, horizon, posterior_prob_up, recommendation, policy_version FROM fxai.decisions ORDER BY ts DESC LIMIT 10"

count-decisions:
	docker exec -i fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.decisions"

backtest:
	$(PY) -m apps.backtest.quick_check --pair USDINR --horizon 4h --lookback-hours 24

backtest-spread:
	@echo "Backtest: pair=$(PAIR) horizon=$(H) lookback=$(LB)h prob_th=$(PROBTH) spread=$(SPREAD)bps"
	$(PY) -m apps.backtest.quick_check --pair $(PAIR) --horizon $(H) --lookback-hours $(LB) --prob-th $(PROBTH) --spread-bps $(SPREAD)

decisions-by-horizon:
	docker exec -i fxai-clickhouse clickhouse-client -q "SELECT horizon, count() FROM fxai.decisions GROUP BY horizon ORDER BY horizon"

featurizer-daemon:
	$(PY) -m apps.workers.featurizer_daemon --pairs $${PAIRS:-USDINR} --interval $${INTERVAL:-60} --lookback-minutes $${LOOKBACK:-360}

worker-build:
	docker compose -f $(COMPOSE) build featurizer

worker-up:
	docker compose -f $(COMPOSE) up -d featurizer

worker-logs:
	docker compose -f $(COMPOSE) logs -f featurizer

worker-down:
	docker compose -f $(COMPOSE) rm -sf featurizer

migrate-decisions:
	docker exec -i fxai-clickhouse clickhouse-client -q "ALTER TABLE fxai.decisions ADD COLUMN IF NOT EXISTS expected_delta_bps Float64 AFTER posterior_prob_up"

migrate-backtest:
	docker exec -i fxai-clickhouse clickhouse-client -q "CREATE TABLE IF NOT EXISTS fxai.backtest_metrics ( ts DateTime DEFAULT now(), pair LowCardinality(String), horizon LowCardinality(String), lookback_hours UInt32, prob_th Float64, spread_bps Float64, trades UInt32, win_rate Float64, avg_pnl_bps Float64, med_pnl_bps Float64 ) ENGINE=MergeTree ORDER BY (pair, horizon, ts)"

backtester-build:
	docker compose -f $(COMPOSE) build backtester

backtester-up:
	docker compose -f $(COMPOSE) up -d backtester

backtester-logs:
	docker compose -f $(COMPOSE) logs -f backtester

backtester-down:
	docker compose -f $(COMPOSE) rm -sf backtester
# --- Models: training & registry ---

train-lgbm:
	$(PY) -m apps.train.train_lgbm --pair $(PAIR) --horizon $(H) --lookback-hours $(LB)

models-tail:
	docker exec -i fxai-clickhouse clickhouse-client -q \
	"SELECT model_id, created_at, algo, horizon, train_start, train_end, metrics_json \
	 FROM fxai.models ORDER BY created_at DESC LIMIT 5"

# Fetch latest model_id for a horizon (echo only)
model-latest-id:
	docker exec -i fxai-clickhouse clickhouse-client -q \
	"SELECT model_id FROM fxai.models WHERE horizon='$(H)' ORDER BY created_at DESC LIMIT 1"

# Forecast using the latest model for the chosen horizon
forecast-with-latest:
	@MID=$$(docker exec -i fxai-clickhouse clickhouse-client -q \
	  "SELECT model_id FROM fxai.models WHERE horizon='$(H)' ORDER BY created_at DESC LIMIT 1"); \
	echo "Using model_id=$$MID"; \
	curl -s -H "X-API-Key: $${API_KEY:-changeme-dev-key}" \
	  "http://localhost:9090/v1/forecast?pair=$(PAIR)&h=$(H)&model_id=$$MID" | jq . || true

backfill-features:
	$(PY) -m apps.features.featurize --pair $(PAIR) --lookback-minutes $${MINUTES:-10080}

# --- Alerts ---

alerts-create:
	docker exec -i fxai-clickhouse clickhouse-client -n < infra/sql/010_alerts.sql

alerts-daemon:
	$(PY) -m apps.workers.alerter_daemon

alerts-run:
	ALERT_POLL_SEC=$${POLL:-10} ALERT_LOOKBACK_MIN=$${LBMIN:-120} $(PY) -m apps.workers.alerter_daemon

alerts-tail:
	docker exec -i fxai-clickhouse clickhouse-client -q \
	"SELECT ts, decision_ts, pair, horizon, direction, expected_delta_bps, sent, dest \
	 FROM fxai.alerts ORDER BY ts DESC LIMIT 10"

# --- News & LLM Integration ---

init-news-schema:
	docker exec -i fxai-clickhouse clickhouse-client -n < infra/sql/020_news_llm.sql

news-ingester:
	$(PY) -m apps.workers.news_ingester \
		--poll-interval $${NEWS_POLL_INTERVAL_SEC:-60} \
		--lookback-hours $${NEWS_LOOKBACK_HOURS:-1} \
		--enable-sentiment

news-ingester-no-llm:
	$(PY) -m apps.workers.news_ingester \
		--poll-interval $${NEWS_POLL_INTERVAL_SEC:-60} \
		--lookback-hours $${NEWS_LOOKBACK_HOURS:-1}

tail-news:
	docker exec -i fxai-clickhouse clickhouse-client -q \
	"SELECT ts, source, headline FROM fxai.news_items ORDER BY ts DESC LIMIT 10"

tail-sentiment:
	docker exec -i fxai-clickhouse clickhouse-client -q \
	"SELECT ts, sentiment_usd, sentiment_inr, impact_score, confidence, explanation \
	 FROM fxai.sentiment_scores ORDER BY ts DESC LIMIT 10"

count-news:
	docker exec -i fxai-clickhouse clickhouse-client -q \
	"SELECT source, count() FROM fxai.news_items GROUP BY source ORDER BY count() DESC"

llm-costs:
	docker exec -i fxai-clickhouse clickhouse-client -q \
	"SELECT toDate(ts) AS date, model_version, sum(api_cost_usd) AS total_cost \
	 FROM fxai.sentiment_scores WHERE ts >= today() - 7 GROUP BY date, model_version ORDER BY date DESC"

tail-hybrid:
	docker exec -i fxai-clickhouse clickhouse-client -q \
	"SELECT ts, pair, horizon, prob_up_ml, prob_up_hybrid, fusion_weight_llm, recommendation \
	 FROM fxai.hybrid_predictions ORDER BY ts DESC LIMIT 10"

test-hybrid-api:
	$(PY) scripts/test_hybrid_api.py

curl-hybrid:
	curl -s -H "X-API-Key: $${API_KEY:-changeme-dev-key}" \
		"http://localhost:9090/v1/forecast?pair=USDINR&h=4h&use_hybrid=true" | jq .

# --- Ollama (Local LLM) ---

setup-ollama:
	./scripts/setup_ollama.sh

test-ollama:
	$(PY) scripts/test_ollama.py

insert-sample-news:
	$(PY) scripts/insert_sample_news.py

# --- Dashboard ---

dashboard-install:
	cd dashboard && npm install

dashboard-dev:
	cd dashboard && npm run dev

dashboard-build:
	cd dashboard && npm run build

dashboard-preview:
	cd dashboard && npm run preview

ollama-list:
	ollama list

ollama-pull-llama3:
	ollama pull llama3:8b

ollama-pull-mistral:
	ollama pull mistral:7b

ollama-pull-phi3:
	ollama pull phi3:mini

ollama-serve:
	ollama serve

# --- End-to-End Testing ---

e2e-test:
	./scripts/run_e2e_test.sh

e2e-full:
	@echo "Running full end-to-end test (this will take 2-3 hours)..."
	@echo ""
	@echo "Phase 1: Data ingestion..."
	make ingest-usdinr
	make ingest-events
	@echo ""
	@echo "Phase 2: Feature generation..."
	make featurize
	@echo ""
	@echo "Phase 3: Model training..."
	make train-lgbm PAIR=USDINR HORIZON=4h
	@echo ""
	@echo "Phase 4: Running automated tests..."
	./scripts/run_e2e_test.sh
	@echo ""
	@echo "✓ Full E2E test complete!"

e2e-quick:
	@echo "Running quick E2E test (assumes data already exists)..."
	./scripts/run_e2e_test.sh

status:
	./scripts/quick_status.sh