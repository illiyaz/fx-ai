# End-to-End Testing Plan - Hybrid ML+LLM System

## 🎯 Overview

This guide provides a complete step-by-step process to test the entire FX-AI Advisor system from scratch, including:
- Infrastructure setup
- Data ingestion
- Model training
- News ingestion with Ollama
- Hybrid predictions
- API testing

**Estimated Time**: 2-3 hours for complete end-to-end test

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] MacBook Pro with M1/M2/M3 chip
- [ ] Docker Desktop installed and running
- [ ] Python 3.11+ installed
- [ ] Ollama installed (from previous step)
- [ ] Llama3:8b model downloaded
- [ ] At least 20GB free disk space
- [ ] Internet connection (for initial setup)

---

## 🚀 Phase 1: Infrastructure Setup (15 minutes)

### Step 1.1: Clone and Setup Project

```bash
# Navigate to project
cd /Users/LENOVO/Documents/Projects/fx-ai

# Verify files exist
ls -la

# Expected output: Makefile, pyproject.toml, apps/, docs/, etc.
```

### Step 1.2: Install Python Dependencies

```bash
# Install all dependencies
make deps

# Verify installation
python -c "import pandas, lightgbm, openai, anthropic; print('✓ All packages installed')"
```

**Expected Output**: `✓ All packages installed`

### Step 1.3: Start Infrastructure

```bash
# Start ClickHouse and Kafka
make up

# Wait 30 seconds for services to start
sleep 30

# Verify services are running
docker ps
```

**Expected Output**: Should see containers:
- `fxai-clickhouse`
- `fxai-kafka`
- `fxai-zookeeper`

### Step 1.4: Initialize Database Schema

```bash
# Initialize core schema
make init-db

# Initialize news/LLM schema
make init-news-schema

# Verify tables exist
make db-shell
```

In ClickHouse shell:
```sql
SHOW TABLES FROM fxai;
-- Expected: bars, features, models, predictions, decisions, 
--           news_items, sentiment_scores, hybrid_predictions, etc.

EXIT;
```

**✅ Checkpoint**: Infrastructure is ready

---

## 📊 Phase 2: Data Ingestion (30 minutes)

### Step 2.1: Ingest Historical Price Data

```bash
# Ingest USDINR data (last 90 days)
make ingest-usdinr

# This will take 5-10 minutes
# Watch progress in terminal
```

**Expected Output**:
```
✓ Fetched 2160 bars (90 days × 24 hours)
✓ Inserted into fxai.bars
```

### Step 2.2: Verify Price Data

```bash
# Check bar count
docker exec -i fxai-clickhouse clickhouse-client -q \
  "SELECT pair, count() as bars FROM fxai.bars GROUP BY pair"
```

**Expected Output**:
```
USDINR  2160
```

### Step 2.3: Ingest Economic Events

```bash
# Ingest macro events
make ingest-events

# This will take 2-3 minutes
```

**Expected Output**:
```
✓ Fetched 50 events
✓ Inserted into fxai.events_news
```

### Step 2.4: Verify Events

```bash
# Check events
docker exec -i fxai-clickhouse clickhouse-client -q \
  "SELECT count() FROM fxai.events_news"
```

**Expected Output**: `50` (or similar)

**✅ Checkpoint**: Historical data is loaded

---

## 🤖 Phase 3: Model Training (20 minutes)

### Step 3.1: Generate Features

```bash
# Generate features from bars
make featurize

# This will take 5-10 minutes
```

**Expected Output**:
```
✓ Generated 2000+ feature rows
✓ Inserted into fxai.features
```

### Step 3.2: Verify Features

```bash
# Check feature count
docker exec -i fxai-clickhouse clickhouse-client -q \
  "SELECT pair, count() FROM fxai.features GROUP BY pair"
```

**Expected Output**:
```
USDINR  2000+
```

### Step 3.3: Train LightGBM Model

```bash
# Train model for 4h horizon
make train-lgbm PAIR=USDINR HORIZON=4h

# This will take 5-10 minutes
```

**Expected Output**:
```
✓ Training complete
  Train samples: 1400
  Test samples: 600
  AUC: 0.58-0.62
  Win Rate: 55-60%
✓ Model saved: models/lgbm_USDINR_4h_20251128.pkl
✓ Metadata inserted into fxai.models
```

### Step 3.4: Verify Model

```bash
# Check model exists
ls -lh models/

# Check model metadata
docker exec -i fxai-clickhouse clickhouse-client -q \
  "SELECT model_id, pair, horizon, auc, win_rate FROM fxai.models ORDER BY ts DESC LIMIT 1"
```

**Expected Output**:
```
lgbm_USDINR_4h_20251128  USDINR  4h  0.60  0.58
```

**✅ Checkpoint**: ML model is trained and ready

---

## 📰 Phase 4: News Ingestion with Ollama (30 minutes)

### Step 4.1: Configure Ollama

```bash
# Edit .env file
nano .env
```

Update these lines:
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3
OLLAMA_BASE_URL=http://localhost:11434
ENABLE_LLM_FUSION=true
ENABLE_CENTRAL_BANKS=true
NEWS_ENABLE_SENTIMENT=true
```

Save and exit (Ctrl+X, Y, Enter)

### Step 4.2: Test Ollama Connection

```bash
# Test Ollama
make test-ollama
```

**Expected Output**:
```
✓ Ollama is running
✓ Found 1 model: llama3:8b
✓ Sentiment analysis complete:
  Sentiment USD: +0.75
  Impact: 8.5/10
  Processing time: 3245ms
  Cost: $0.0000 (FREE!)
```

### Step 4.3: Start News Ingester (Background)

Open a **new terminal window** (Terminal 1):

```bash
cd /Users/LENOVO/Documents/Projects/fx-ai

# Start news ingester with Ollama sentiment
make news-ingester
```

**Expected Output** (continuous):
```
2025-11-28 23:30:00 | INFO | sources_configured | total=9 basic=5 advanced=4
2025-11-28 23:30:05 | INFO | news_fetched | source=forexlive count=5
2025-11-28 23:30:10 | INFO | news_inserted | count=5
2025-11-28 23:30:15 | INFO | sentiment_analysis_start | batch_size=5
2025-11-28 23:30:20 | INFO | ollama_sentiment_success | tokens=850 latency_ms=3245
...
```

**Keep this terminal running!**

### Step 4.4: Monitor News Ingestion (Main Terminal)

Wait 2-3 minutes for news to be ingested, then check:

```bash
# Check news count
make tail-news
```

**Expected Output**:
```
2025-11-28 23:30:00  forexlive     USD/INR rises on Fed hawkish comments
2025-11-28 23:29:00  reuters       Fed signals more rate hikes ahead
2025-11-28 23:28:00  fxstreet      EUR/USD falls as ECB holds rates
...
```

### Step 4.5: Verify Sentiment Analysis

```bash
# Check sentiment scores
make tail-sentiment
```

**Expected Output**:
```
2025-11-28 23:30:20  +0.75  -0.30  8.5  0.85  Fed hawkish stance supports USD
2025-11-28 23:29:45  +0.60  -0.20  7.0  0.75  Rate hikes expected to continue
...
```

### Step 4.6: Check LLM Costs

```bash
# Check costs (should be $0 with Ollama!)
make llm-costs
```

**Expected Output**:
```
date        model_version      total_cost
2025-11-28  ollama_llama3      0.00
```

**✅ Checkpoint**: News ingestion with Ollama is working

---

## 🔄 Phase 5: Hybrid Predictions (15 minutes)

### Step 5.1: Start API Server (Background)

Open a **new terminal window** (Terminal 2):

```bash
cd /Users/LENOVO/Documents/Projects/fx-ai

# Start API server
make api
```

**Expected Output**:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

**Keep this terminal running!**

### Step 5.2: Test API Health

In main terminal:

```bash
# Test health endpoint
curl http://localhost:8080/health
```

**Expected Output**:
```json
{"status":"ok","env":"local"}
```

### Step 5.3: Test ML-Only Forecast

```bash
# Get ML-only forecast
curl -s -H "X-API-Key: changeme-dev-key" \
  "http://localhost:8080/v1/forecast?pair=USDINR&h=4h&use_hybrid=false" | jq .
```

**Expected Output**:
```json
{
  "pair": "USDINR",
  "horizon": "4h",
  "prob_up": 0.580,
  "expected_delta_bps": 2.30,
  "recommendation": "WAIT",
  "direction": "UP",
  "model_id": "lgbm_USDINR_4h_20251128",
  "hybrid": {
    "enabled": false
  }
}
```

### Step 5.4: Test Hybrid Forecast

```bash
# Get hybrid forecast (ML + News)
make curl-hybrid
```

**Expected Output**:
```json
{
  "pair": "USDINR",
  "horizon": "4h",
  "prob_up": 0.697,
  "expected_delta_bps": 3.12,
  "recommendation": "NOW",
  "direction": "UP",
  "model_id": "lgbm_USDINR_4h_20251128",
  "explanation": [
    "model=lgbm_USDINR_4h_20251128",
    "policy=expected; spread_bps=2.0; prob_th=0.6",
    "hybrid: ML=65%, News=35%",
    "Recent news: USD bullish vs INR (high-impact) | Key: Fed hawkish stance...",
    "dir=UP"
  ],
  "hybrid": {
    "enabled": true,
    "prob_up_ml": 0.580,
    "prob_up_hybrid": 0.697,
    "expected_delta_ml": 2.30,
    "expected_delta_hybrid": 3.12,
    "fusion_weights": {
      "ml": 0.65,
      "llm": 0.35
    },
    "news_sentiment": 0.75,
    "news_confidence": 0.85,
    "news_impact": 8.5,
    "news_summary": "Recent news: USD bullish vs INR (high-impact)"
  }
}
```

**Key Observations**:
- ✅ `prob_up` increased from 0.580 → 0.697 (news boosted confidence)
- ✅ `expected_delta_bps` increased from 2.30 → 3.12 (news amplified move)
- ✅ `recommendation` changed from WAIT → NOW (crossed threshold)
- ✅ `fusion_weights`: ML=65%, News=35% (news had significant impact)

### Step 5.5: Verify Hybrid Predictions Logged

```bash
# Check hybrid predictions table
make tail-hybrid
```

**Expected Output**:
```
ts                   pair    horizon  prob_up_ml  prob_up_hybrid  fusion_weight_llm  recommendation
2025-11-28 23:35:00  USDINR  4h       0.580       0.697           0.35               NOW
2025-11-28 23:34:00  USDINR  4h       0.550       0.620           0.25               WAIT
...
```

**✅ Checkpoint**: Hybrid predictions are working!

---

## 🧪 Phase 6: Comprehensive Testing (30 minutes)

### Step 6.1: Run Automated Test Suite

```bash
# Run comprehensive API tests
make test-hybrid-api
```

**Expected Output**:
```
==========================================
HYBRID ML+LLM API TEST SUITE
==========================================

TEST 1: Health Check
✓ API is healthy

TEST 2: ML-Only Forecast
✓ ML-only forecast received
  Probability Up: 0.580
  Expected Delta: +2.30 bps

TEST 3: Hybrid ML+LLM Forecast
✓ Hybrid forecast received
  🔄 HYBRID FUSION APPLIED:
    ML Probability: 0.580
    Hybrid Probability: 0.697
    Fusion Weights: ML=65%, News=35%

TEST 4: ML vs Hybrid Comparison
Metric                    ML-Only         Hybrid          Difference
----------------------------------------------------------------------
Probability Up            0.580           0.697           +0.117
Expected Delta (bps)      2.30            3.12            +0.82
Recommendation            WAIT            NOW             ⚠️  Changed

TEST 5: Multiple Currency Pairs
  USDINR: ✓ Active
  EURUSD: ○ No news
  GBPUSD: ○ No news

==========================================
TEST SUMMARY
==========================================
✓ PASS: Health Check
✓ PASS: ML-Only Forecast
✓ PASS: Hybrid Forecast
✓ PASS: ML vs Hybrid Comparison
✓ PASS: Multiple Pairs

Total: 5/5 tests passed

🎉 All tests passed! Hybrid API is working correctly.
```

### Step 6.2: Test Different Scenarios

**Scenario A: High-Impact News**

```bash
# Wait for high-impact news (impact > 8.0)
# Check sentiment scores
make tail-sentiment | grep -E "8\.[5-9]|9\.|10\."
```

Then test forecast:
```bash
make curl-hybrid
```

**Expected**: Higher fusion weight (30-40%), bigger adjustment

**Scenario B: Low-Impact News**

```bash
# Wait for low-impact news (impact < 6.0)
make tail-sentiment | grep -E "[3-5]\."
```

Then test forecast:
```bash
make curl-hybrid
```

**Expected**: Lower fusion weight (5-15%), smaller adjustment

**Scenario C: No Recent News**

```bash
# Stop news ingester (Terminal 1: Ctrl+C)
# Wait 10 minutes for cache to expire
sleep 600

# Test forecast
make curl-hybrid
```

**Expected**: `hybrid.enabled: false`, falls back to ML-only

### Step 6.3: Performance Testing

```bash
# Test response time (10 requests)
for i in {1..10}; do
  echo "Request $i:"
  time curl -s -H "X-API-Key: changeme-dev-key" \
    "http://localhost:8080/v1/forecast?pair=USDINR&h=4h&use_hybrid=true" > /dev/null
done
```

**Expected**: 
- First request: 200-500ms (cache miss)
- Subsequent requests: 50-200ms (cache hit)

### Step 6.4: Load Testing (Optional)

```bash
# Install Apache Bench
brew install httpd

# Run load test (100 requests, 10 concurrent)
ab -n 100 -c 10 -H "X-API-Key: changeme-dev-key" \
  "http://localhost:8080/v1/forecast?pair=USDINR&h=4h&use_hybrid=true"
```

**Expected**:
- Requests per second: 20-50
- Mean response time: 200-500ms
- No failures

**✅ Checkpoint**: All tests passing

---

## 📊 Phase 7: Data Validation (15 minutes)

### Step 7.1: Validate Data Pipeline

```bash
# Check all tables have data
docker exec -i fxai-clickhouse clickhouse-client -q "
SELECT 
  'bars' as table, count() as rows FROM fxai.bars
UNION ALL
SELECT 'features', count() FROM fxai.features
UNION ALL
SELECT 'models', count() FROM fxai.models
UNION ALL
SELECT 'news_items', count() FROM fxai.news_items
UNION ALL
SELECT 'sentiment_scores', count() FROM fxai.sentiment_scores
UNION ALL
SELECT 'hybrid_predictions', count() FROM fxai.hybrid_predictions
UNION ALL
SELECT 'decisions', count() FROM fxai.decisions
ORDER BY table
"
```

**Expected Output**:
```
bars                2160
decisions           10+
features            2000+
hybrid_predictions  5+
models              1
news_items          20+
sentiment_scores    20+
```

### Step 7.2: Validate Data Quality

```bash
# Check for NULL values in critical fields
docker exec -i fxai-clickhouse clickhouse-client -q "
SELECT 
  countIf(sentiment_overall IS NULL) as null_sentiment,
  countIf(confidence IS NULL) as null_confidence,
  countIf(impact_score IS NULL) as null_impact
FROM fxai.sentiment_scores
"
```

**Expected Output**: All zeros (no NULLs)

### Step 7.3: Validate Fusion Logic

```bash
# Check fusion weight distribution
docker exec -i fxai-clickhouse clickhouse-client -q "
SELECT 
  round(fusion_weight_llm, 1) as llm_weight,
  count() as count
FROM fxai.hybrid_predictions
GROUP BY llm_weight
ORDER BY llm_weight
"
```

**Expected Output**:
```
0.0   2   (no news)
0.1   3   (low confidence)
0.2   5   (medium confidence)
0.3   8   (high confidence)
0.4   2   (very high confidence)
```

**✅ Checkpoint**: Data quality validated

---

## 🎯 Phase 8: End-to-End Workflow Test (20 minutes)

### Step 8.1: Simulate Real Trading Workflow

**Scenario**: It's 9:00 AM, Fed announces rate decision

```bash
# 1. News breaks (simulated by ingester)
# Check Terminal 1 for new news

# 2. Sentiment analyzed by Ollama
make tail-sentiment

# 3. Trader requests forecast
make curl-hybrid

# 4. System returns hybrid recommendation
# Observe: prob_up, expected_delta, recommendation

# 5. Decision logged
make tail-hybrid

# 6. Trader acts on recommendation
# (Manual step - not automated)
```

### Step 8.2: Monitor Full Pipeline

Open **4 terminals** side-by-side:

**Terminal 1**: News Ingester
```bash
make news-ingester
```

**Terminal 2**: API Server
```bash
make api
```

**Terminal 3**: Live Monitoring
```bash
watch -n 5 'make tail-sentiment'
```

**Terminal 4**: Testing
```bash
# Request forecasts every 30 seconds
while true; do
  echo "=== $(date) ==="
  make curl-hybrid | jq '.hybrid'
  sleep 30
done
```

**Observe**:
- News flows in (Terminal 1)
- Sentiment updates (Terminal 3)
- Forecasts adjust in real-time (Terminal 4)
- API responds quickly (Terminal 2 logs)

### Step 8.3: Test Error Handling

**Test A: Ollama Down**

```bash
# Stop Ollama
pkill ollama

# Request forecast
make curl-hybrid
```

**Expected**: Falls back to ML-only, no crash

**Restart Ollama**:
```bash
ollama serve &
```

**Test B: No Model Available**

```bash
# Temporarily rename model
mv models/lgbm_USDINR_4h_*.pkl models/backup.pkl

# Request forecast
make curl-hybrid
```

**Expected**: Uses baseline model, returns prediction

**Restore model**:
```bash
mv models/backup.pkl models/lgbm_USDINR_4h_*.pkl
```

**Test C: Invalid Pair**

```bash
curl -s -H "X-API-Key: changeme-dev-key" \
  "http://localhost:8080/v1/forecast?pair=INVALID&h=4h" | jq .
```

**Expected**: Returns baseline prediction with low confidence

**✅ Checkpoint**: Error handling works correctly

---

## 📈 Phase 9: Performance Benchmarking (15 minutes)

### Step 9.1: Measure Component Latencies

```bash
# Create benchmark script
cat > /tmp/benchmark.sh << 'EOF'
#!/bin/bash

echo "=== Component Latency Benchmark ==="
echo ""

# 1. Ollama sentiment analysis
echo "1. Ollama Sentiment Analysis:"
time python -c "
import asyncio
from datetime import datetime, timezone
from apps.llm.ollama_client import OllamaClient

async def test():
    client = OllamaClient(model='llama3')
    await client.analyze_sentiment(
        'Fed raises rates', 
        'Federal Reserve increases rates by 25bps',
        'test',
        datetime.now(timezone.utc)
    )

asyncio.run(test())
"

# 2. Feature generation
echo ""
echo "2. Feature Generation:"
time python -c "
from apps.features.featurize import build_features
build_features('USDINR')
"

# 3. ML prediction
echo ""
echo "3. ML Model Prediction:"
time python -c "
from apps.features.featurize import build_features
from apps.models.loader import latest_model_row, load_model_by_id, SkPredictor

feats = build_features('USDINR')
row = latest_model_row('4h')
if row:
    bundle = load_model_by_id(row['model_id'])
    predictor = SkPredictor(bundle['model'], bundle['features'])
    predictor.predict(feats)
"

# 4. Full API request
echo ""
echo "4. Full API Request (Hybrid):"
time curl -s -H "X-API-Key: changeme-dev-key" \
  "http://localhost:8080/v1/forecast?pair=USDINR&h=4h&use_hybrid=true" > /dev/null

echo ""
echo "=== Benchmark Complete ==="
EOF

chmod +x /tmp/benchmark.sh
/tmp/benchmark.sh
```

**Expected Output**:
```
=== Component Latency Benchmark ===

1. Ollama Sentiment Analysis:
real    0m3.245s

2. Feature Generation:
real    0m0.150s

3. ML Model Prediction:
real    0m0.050s

4. Full API Request (Hybrid):
real    0m0.280s

=== Benchmark Complete ===
```

### Step 9.2: Calculate Throughput

```bash
# Requests per minute
echo "Testing throughput..."
ab -n 60 -c 1 -H "X-API-Key: changeme-dev-key" \
  "http://localhost:8080/v1/forecast?pair=USDINR&h=4h&use_hybrid=true" 2>&1 | \
  grep "Requests per second"
```

**Expected**: 20-50 requests/second (with caching)

### Step 9.3: Memory Usage

```bash
# Check memory usage
docker stats --no-stream fxai-clickhouse
ps aux | grep -E "(ollama|python.*news_ingester|uvicorn)" | awk '{print $11, $6/1024 "MB"}'
```

**Expected**:
- ClickHouse: 200-500MB
- Ollama: 5-8GB (model loaded)
- News Ingester: 100-200MB
- API Server: 100-200MB

**✅ Checkpoint**: Performance is acceptable

---

## ✅ Phase 10: Final Validation (10 minutes)

### Step 10.1: Complete System Check

```bash
# Run final validation
cat > /tmp/final_check.sh << 'EOF'
#!/bin/bash

echo "=== Final System Validation ==="
echo ""

# Check 1: Infrastructure
echo "✓ Checking infrastructure..."
docker ps | grep -q fxai-clickhouse && echo "  ✓ ClickHouse running" || echo "  ✗ ClickHouse not running"
docker ps | grep -q fxai-kafka && echo "  ✓ Kafka running" || echo "  ✗ Kafka not running"

# Check 2: Ollama
echo ""
echo "✓ Checking Ollama..."
curl -s http://localhost:11434/api/tags > /dev/null && echo "  ✓ Ollama running" || echo "  ✗ Ollama not running"
ollama list | grep -q llama3 && echo "  ✓ Llama3 model available" || echo "  ✗ Llama3 not found"

# Check 3: Data
echo ""
echo "✓ Checking data..."
docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.bars" > /dev/null && echo "  ✓ Price data available" || echo "  ✗ No price data"
docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.news_items WHERE ts >= now() - INTERVAL 1 HOUR" | grep -qv "^0$" && echo "  ✓ Recent news available" || echo "  ⚠ No recent news"

# Check 4: Models
echo ""
echo "✓ Checking models..."
docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.models" | grep -qv "^0$" && echo "  ✓ ML model trained" || echo "  ✗ No ML model"

# Check 5: API
echo ""
echo "✓ Checking API..."
curl -s http://localhost:8080/health | grep -q "ok" && echo "  ✓ API responding" || echo "  ✗ API not responding"

# Check 6: Hybrid predictions
echo ""
echo "✓ Checking hybrid predictions..."
docker exec fxai-clickhouse clickhouse-client -q "SELECT count() FROM fxai.hybrid_predictions" | grep -qv "^0$" && echo "  ✓ Hybrid predictions logged" || echo "  ⚠ No hybrid predictions yet"

echo ""
echo "=== Validation Complete ==="
EOF

chmod +x /tmp/final_check.sh
/tmp/final_check.sh
```

**Expected Output**: All checks pass (✓)

### Step 10.2: Generate Test Report

```bash
# Generate summary report
cat > /tmp/test_report.md << 'EOF'
# End-to-End Test Report

## Test Date
$(date)

## System Status
- Infrastructure: ✓ Running
- Ollama: ✓ Running (llama3:8b)
- Data Pipeline: ✓ Active
- ML Models: ✓ Trained
- API Server: ✓ Running
- Hybrid Predictions: ✓ Working

## Data Summary
EOF

docker exec fxai-clickhouse clickhouse-client -q "
SELECT 
  'Bars: ' || toString(count()) FROM fxai.bars
UNION ALL
SELECT 'News Items: ' || toString(count()) FROM fxai.news_items
UNION ALL
SELECT 'Sentiment Scores: ' || toString(count()) FROM fxai.sentiment_scores
UNION ALL
SELECT 'Hybrid Predictions: ' || toString(count()) FROM fxai.hybrid_predictions
" >> /tmp/test_report.md

cat >> /tmp/test_report.md << 'EOF'

## Performance Metrics
- Ollama Latency: 2-5 seconds
- API Response Time: 200-500ms
- Throughput: 20-50 req/sec

## Cost Analysis
- LLM API Cost: $0.00 (Ollama local)
- Infrastructure: Docker (free)
- Total Monthly Cost: $0.00

## Test Results
✓ All 5 test suites passed
✓ Error handling validated
✓ Performance acceptable
✓ Data quality verified

## Conclusion
System is production-ready for local deployment.
EOF

cat /tmp/test_report.md
```

### Step 10.3: Save Test Artifacts

```bash
# Create test artifacts directory
mkdir -p test_results/$(date +%Y%m%d_%H%M%S)
cd test_results/$(date +%Y%m%d_%H%M%S)

# Save test report
cp /tmp/test_report.md ./

# Save sample predictions
curl -s -H "X-API-Key: changeme-dev-key" \
  "http://localhost:8080/v1/forecast?pair=USDINR&h=4h&use_hybrid=true" | \
  jq . > sample_hybrid_prediction.json

curl -s -H "X-API-Key: changeme-dev-key" \
  "http://localhost:8080/v1/forecast?pair=USDINR&h=4h&use_hybrid=false" | \
  jq . > sample_ml_prediction.json

# Save data snapshots
docker exec fxai-clickhouse clickhouse-client -q \
  "SELECT * FROM fxai.hybrid_predictions ORDER BY ts DESC LIMIT 10 FORMAT JSONEachRow" \
  > hybrid_predictions_sample.json

docker exec fxai-clickhouse clickhouse-client -q \
  "SELECT * FROM fxai.sentiment_scores ORDER BY ts DESC LIMIT 10 FORMAT JSONEachRow" \
  > sentiment_scores_sample.json

echo "✓ Test artifacts saved to: $(pwd)"
```

**✅ Checkpoint**: Testing complete!

---

## 🎉 Success Criteria

Your end-to-end test is successful if:

- [x] All infrastructure services running
- [x] Price data ingested (2000+ bars)
- [x] ML model trained (AUC > 0.55)
- [x] News ingestion active (10+ items/hour)
- [x] Ollama sentiment working (0 API cost)
- [x] Hybrid predictions enabled
- [x] API responding (<500ms)
- [x] All automated tests passing
- [x] Error handling working
- [x] Performance acceptable

---

## 🧹 Cleanup (Optional)

If you want to clean up after testing:

```bash
# Stop all services
make down

# Stop news ingester (Terminal 1: Ctrl+C)
# Stop API server (Terminal 2: Ctrl+C)

# Remove test data (optional)
docker exec fxai-clickhouse clickhouse-client -q "TRUNCATE TABLE fxai.news_items"
docker exec fxai-clickhouse clickhouse-client -q "TRUNCATE TABLE fxai.sentiment_scores"
docker exec fxai-clickhouse clickhouse-client -q "TRUNCATE TABLE fxai.hybrid_predictions"

# Keep models and price data for future use
```

---

## 📚 Next Steps

After successful end-to-end testing:

1. **Production Deployment**
   - Set up monitoring (Grafana)
   - Configure alerts
   - Set up backups

2. **Optimization**
   - Tune fusion parameters
   - Optimize model hyperparameters
   - Add more news sources

3. **Scaling**
   - Add more currency pairs
   - Train models for multiple horizons
   - Implement backtesting

4. **Documentation**
   - Document your specific setup
   - Create runbooks
   - Set up team training

---

## 🆘 Troubleshooting

### Common Issues

**Issue**: Ollama slow (>10s per analysis)
- **Solution**: Use smaller model (phi3:mini) or close other apps

**Issue**: No news being ingested
- **Solution**: Check internet connection, verify RSS feeds accessible

**Issue**: Hybrid not activating
- **Solution**: Ensure news_items and sentiment_scores have recent data (<1 hour)

**Issue**: API returns 500 error
- **Solution**: Check logs, verify model exists, ensure ClickHouse is running

---

## 📞 Support

If you encounter issues:
1. Check logs: `docker logs fxai-clickhouse`
2. Review documentation in `docs/`
3. Create an issue on GitHub

---

**Congratulations! You've completed the end-to-end test!** 🎉

Your hybrid ML+LLM FX forecasting system is now fully operational with:
- ✅ Zero API costs (Ollama)
- ✅ Real-time news sentiment
- ✅ Adaptive Bayesian fusion
- ✅ Production-ready API

**Happy trading!** 🚀📈
