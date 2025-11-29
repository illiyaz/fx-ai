# Testing Guide - Quick Reference

## 🎯 Testing Options

### Option 1: Automated Quick Test (5 minutes) ⚡

**Best for**: Quick validation that everything works

```bash
make e2e-quick
```

**What it tests**:
- ✓ Infrastructure (Docker, ClickHouse, Kafka)
- ✓ Ollama LLM (connection and inference)
- ✓ Data availability (bars, features, models)
- ✓ News ingestion (if running)
- ✓ API endpoints (health, ML, hybrid)
- ✓ Performance (response time)

**Expected output**:
```
==========================================
  FX-AI Advisor - E2E Test Runner
==========================================

Phase 1: Checking Prerequisites
----------------------------------------
[✓] Docker installed
[✓] Python installed
[✓] Ollama installed
[✓] Llama3 model available

Phase 2: Infrastructure Setup
----------------------------------------
[✓] ClickHouse running
[✓] Kafka running
[✓] Database initialized

Phase 3: Data Availability
----------------------------------------
[✓] Price data available (2160 bars)
[✓] Features available (2000 rows)
[✓] ML model trained (1 models)

Phase 4: Ollama LLM
----------------------------------------
[✓] Ollama service running
[✓] Ollama sentiment analysis working

Phase 5: News Ingestion
----------------------------------------
[⚠] No recent news. Start: make news-ingester

Phase 6: API Server
----------------------------------------
[✓] API server running
[✓] Health endpoint working
[✓] ML-only forecast working
[✓] Hybrid forecast working
[✓] Hybrid fusion enabled

Phase 7: Performance Check
----------------------------------------
[✓] API response time: 285ms (excellent)

==========================================
  Test Summary
==========================================

Passed: 18
Failed: 0

🎉 All tests passed! System is ready.
```

---

### Option 2: Full End-to-End Test (2-3 hours) 🔬

**Best for**: Complete validation from scratch

```bash
make e2e-full
```

**What it does**:
1. Ingests price data (30 min)
2. Ingests events (5 min)
3. Generates features (10 min)
4. Trains ML model (15 min)
5. Runs automated tests (5 min)

**Use when**:
- First time setup
- After major changes
- Before production deployment

---

### Option 3: Component-Specific Tests 🧩

**Test individual components**:

```bash
# Test Ollama only
make test-ollama

# Test API only
make test-hybrid-api

# Test news ingestion
python scripts/test_news_ingestion.py

# Test LLM client
python scripts/test_llm.py
```

---

### Option 4: Manual Step-by-Step (2-3 hours) 📝

**Best for**: Learning and troubleshooting

Follow: [END_TO_END_TESTING.md](./END_TO_END_TESTING.md)

**10 phases**:
1. Infrastructure Setup (15 min)
2. Data Ingestion (30 min)
3. Model Training (20 min)
4. News Ingestion with Ollama (30 min)
5. Hybrid Predictions (15 min)
6. Comprehensive Testing (30 min)
7. Data Validation (15 min)
8. End-to-End Workflow (20 min)
9. Performance Benchmarking (15 min)
10. Final Validation (10 min)

---

## 📋 Quick Checklist

Use: [TEST_CHECKLIST.md](../TEST_CHECKLIST.md)

**10 phases, 40+ checkpoints**:
- [ ] Infrastructure
- [ ] Data Ingestion
- [ ] Model Training
- [ ] Ollama Setup
- [ ] API Testing
- [ ] Automated Tests
- [ ] Validation
- [ ] Workflow Test
- [ ] Performance
- [ ] Final Check

---

## 🎬 Recommended Testing Workflow

### For First-Time Setup

```bash
# Day 1: Setup and Data (1 hour)
make setup-ollama          # Install Ollama + Llama3
make up                    # Start infrastructure
make init-db               # Initialize database
make init-news-schema      # Initialize news schema
make ingest-usdinr         # Ingest price data (30 min)

# Day 2: Training and Testing (1 hour)
make featurize             # Generate features (10 min)
make train-lgbm PAIR=USDINR HORIZON=4h  # Train model (15 min)
make e2e-quick             # Run quick test (5 min)

# Day 3: Production Run (ongoing)
# Terminal 1
make news-ingester         # Start news ingestion

# Terminal 2
make api                   # Start API server

# Terminal 3
make curl-hybrid           # Test hybrid forecasts
```

### For Daily Development

```bash
# Quick validation
make e2e-quick

# If changes to ML
make train-lgbm PAIR=USDINR HORIZON=4h
make e2e-quick

# If changes to API
make api
make test-hybrid-api

# If changes to Ollama integration
make test-ollama
```

### Before Production Deployment

```bash
# Full validation
make e2e-full

# Load testing
ab -n 1000 -c 10 -H "X-API-Key: changeme-dev-key" \
  "http://localhost:8080/v1/forecast?pair=USDINR&h=4h&use_hybrid=true"

# Stress testing
# Run for 24 hours, monitor memory/CPU
```

---

## 🔍 What to Look For

### ✅ Good Signs

**Infrastructure**:
- Docker containers running (3/3)
- ClickHouse responding (<100ms)
- No error logs

**Data**:
- 2000+ price bars
- 2000+ features
- 1+ trained models
- 10+ news items/hour
- 10+ sentiment scores/hour

**Performance**:
- Ollama: 2-5 seconds per analysis
- API: <500ms response time
- No memory leaks (stable over time)

**Quality**:
- ML model AUC: 0.55-0.65
- Hybrid fusion weight: 10-40%
- No NULL values in critical fields

### ⚠️ Warning Signs

**Infrastructure**:
- Containers restarting
- ClickHouse slow (>1s queries)
- Disk space <10GB

**Data**:
- <100 price bars
- No recent news (<1 hour old)
- Model AUC <0.52

**Performance**:
- Ollama >10s per analysis
- API >2s response time
- Memory usage growing

**Quality**:
- Many NULL sentiment scores
- Fusion weight always 0
- Predictions always same

### ❌ Red Flags

**Infrastructure**:
- Containers not starting
- ClickHouse connection refused
- Out of disk space

**Data**:
- No price data
- No trained model
- No news ingestion

**Performance**:
- Ollama timeouts
- API 500 errors
- Out of memory errors

**Quality**:
- Model AUC <0.50 (worse than random)
- All predictions identical
- Sentiment scores all 0

---

## 🐛 Troubleshooting Tests

### Test fails: "Docker not running"

```bash
# Start Docker Desktop
open -a Docker

# Wait for Docker to start
sleep 30

# Retry test
make e2e-quick
```

### Test fails: "Ollama not running"

```bash
# Start Ollama
ollama serve &

# Or restart Ollama app
pkill ollama
open -a Ollama

# Retry test
make e2e-quick
```

### Test fails: "No price data"

```bash
# Ingest data
make ingest-usdinr

# Wait for completion (30 min)
# Retry test
make e2e-quick
```

### Test fails: "No ML model"

```bash
# Train model
make featurize
make train-lgbm PAIR=USDINR HORIZON=4h

# Retry test
make e2e-quick
```

### Test fails: "API not responding"

```bash
# Check if API is running
curl http://localhost:8080/health

# If not, start it
make api

# Retry test
make e2e-quick
```

### Test fails: "Hybrid not enabled"

```bash
# Check news exists
make tail-news

# If no news, start ingester
make news-ingester

# Wait 5 minutes
sleep 300

# Retry test
make e2e-quick
```

---

## 📊 Test Reports

### Generate Test Report

```bash
# Run test and save report
make e2e-quick > test_report_$(date +%Y%m%d).txt

# View report
cat test_report_$(date +%Y%m%d).txt
```

### Sample Test Report

```
==========================================
  Test Summary
==========================================

Date: 2025-11-28 23:45:00
Duration: 45 seconds

Infrastructure: ✓ PASS
  - Docker: ✓
  - ClickHouse: ✓
  - Kafka: ✓

Data: ✓ PASS
  - Bars: 2160
  - Features: 2000
  - Models: 1

Ollama: ✓ PASS
  - Service: ✓
  - Inference: ✓ (3.2s)

News: ⚠ WARNING
  - Recent news: 0 (start news-ingester)

API: ✓ PASS
  - Health: ✓
  - ML forecast: ✓
  - Hybrid forecast: ✓
  - Response time: 285ms

Performance: ✓ EXCELLENT

Overall: 18/18 tests passed (100%)
Status: READY FOR PRODUCTION
```

---

## 🎯 Success Criteria

### Minimum (Development)

- [x] Infrastructure running
- [x] Some price data (>100 bars)
- [x] ML model trained
- [x] Ollama working
- [x] API responding

### Recommended (Staging)

- [x] All minimum criteria
- [x] 2000+ price bars
- [x] News ingestion active
- [x] Hybrid predictions working
- [x] All automated tests passing

### Production-Ready

- [x] All recommended criteria
- [x] Model AUC >0.55
- [x] API response <500ms
- [x] 24-hour stability test passed
- [x] Load test passed (100+ req/sec)
- [x] Error handling validated
- [x] Monitoring configured

---

## 🚀 Next Steps After Testing

### If All Tests Pass ✅

1. **Start Production Services**
   ```bash
   make news-ingester &
   make api &
   ```

2. **Set Up Monitoring**
   - Configure Grafana dashboards
   - Set up alerts
   - Monitor logs

3. **Optimize Performance**
   - Tune fusion parameters
   - Optimize model hyperparameters
   - Add more news sources

### If Some Tests Fail ⚠️

1. **Review Warnings**
   - Check which tests failed
   - Read error messages
   - Consult troubleshooting section

2. **Fix Issues**
   - Follow troubleshooting steps
   - Re-run failed tests
   - Verify fixes

3. **Re-test**
   ```bash
   make e2e-quick
   ```

### If Many Tests Fail ❌

1. **Start Fresh**
   ```bash
   make down
   make up
   make init-db
   make init-news-schema
   ```

2. **Follow Manual Guide**
   - Read [END_TO_END_TESTING.md](./END_TO_END_TESTING.md)
   - Execute step-by-step
   - Note where it fails

3. **Get Help**
   - Check logs
   - Review documentation
   - Create GitHub issue

---

## 📚 Related Documentation

- [END_TO_END_TESTING.md](./END_TO_END_TESTING.md) - Complete testing guide
- [TEST_CHECKLIST.md](../TEST_CHECKLIST.md) - Quick checklist
- [OLLAMA_SETUP.md](./OLLAMA_SETUP.md) - Ollama setup guide
- [HYBRID_SYSTEM_COMPLETE.md](./HYBRID_SYSTEM_COMPLETE.md) - System overview
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Troubleshooting guide

---

## 🎉 Summary

**Three ways to test**:

1. **Quick** (5 min): `make e2e-quick`
2. **Full** (2-3 hours): `make e2e-full`
3. **Manual** (2-3 hours): Follow [END_TO_END_TESTING.md](./END_TO_END_TESTING.md)

**Recommended workflow**:
```bash
# First time
make e2e-full

# Daily development
make e2e-quick

# Before production
make e2e-full + load testing
```

**Success criteria**: 18/18 tests passing

**Get started**:
```bash
make e2e-quick
```

**Happy testing!** 🚀🧪
