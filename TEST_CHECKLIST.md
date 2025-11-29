# End-to-End Testing Checklist

Quick reference checklist for testing the complete system.

**Estimated Time**: 2-3 hours

---

## ☑️ Phase 1: Infrastructure (15 min)

```bash
- [ ] make deps
- [ ] make up
- [ ] make init-db
- [ ] make init-news-schema
- [ ] Verify: docker ps shows 3 containers
```

---

## ☑️ Phase 2: Data Ingestion (30 min)

```bash
- [ ] make ingest-usdinr
- [ ] make ingest-events
- [ ] Verify: make db-shell → SHOW TABLES
- [ ] Check: SELECT count() FROM fxai.bars
```

---

## ☑️ Phase 3: Model Training (20 min)

```bash
- [ ] make featurize
- [ ] make train-lgbm PAIR=USDINR HORIZON=4h
- [ ] Verify: ls models/
- [ ] Check: SELECT * FROM fxai.models
```

---

## ☑️ Phase 4: Ollama Setup (30 min)

```bash
- [ ] make setup-ollama (choose option 1: llama3)
- [ ] Edit .env: LLM_PROVIDER=ollama
- [ ] make test-ollama
- [ ] Terminal 1: make news-ingester (keep running)
- [ ] Wait 2-3 minutes
- [ ] make tail-news
- [ ] make tail-sentiment
```

---

## ☑️ Phase 5: API Testing (15 min)

```bash
- [ ] Terminal 2: make api (keep running)
- [ ] curl http://localhost:8080/health
- [ ] Test ML-only: curl with use_hybrid=false
- [ ] Test Hybrid: make curl-hybrid
- [ ] Verify: hybrid.enabled = true
- [ ] Check: make tail-hybrid
```

---

## ☑️ Phase 6: Automated Tests (30 min)

```bash
- [ ] make test-hybrid-api
- [ ] Verify: 5/5 tests passed
- [ ] Test high-impact news scenario
- [ ] Test low-impact news scenario
- [ ] Test no-news scenario
```

---

## ☑️ Phase 7: Validation (15 min)

```bash
- [ ] Check all tables have data
- [ ] Verify no NULL values
- [ ] Check fusion weight distribution
- [ ] Validate data quality
```

---

## ☑️ Phase 8: Workflow Test (20 min)

```bash
- [ ] Monitor 4 terminals simultaneously
- [ ] Observe news → sentiment → forecast flow
- [ ] Test error handling (Ollama down)
- [ ] Test error handling (no model)
- [ ] Test error handling (invalid pair)
```

---

## ☑️ Phase 9: Performance (15 min)

```bash
- [ ] Measure Ollama latency (<5s)
- [ ] Measure API response time (<500ms)
- [ ] Run load test (ab -n 100 -c 10)
- [ ] Check memory usage
```

---

## ☑️ Phase 10: Final Check (10 min)

```bash
- [ ] Run final validation script
- [ ] Generate test report
- [ ] Save test artifacts
- [ ] All success criteria met
```

---

## ✅ Success Criteria

- [x] Infrastructure running
- [x] 2000+ price bars
- [x] ML model trained (AUC > 0.55)
- [x] News ingestion active
- [x] Ollama sentiment working ($0 cost)
- [x] Hybrid predictions enabled
- [x] API responding (<500ms)
- [x] All tests passing
- [x] Error handling working
- [x] Performance acceptable

---

## 🎯 Quick Commands

```bash
# Start everything
make up && make news-ingester &
make api &

# Test everything
make test-ollama
make test-hybrid-api

# Monitor everything
make tail-news
make tail-sentiment
make tail-hybrid

# Stop everything
make down
pkill -f news_ingester
pkill -f uvicorn
```

---

## 📊 Expected Results

| Metric | Expected Value |
|--------|----------------|
| Price Bars | 2000+ |
| News Items | 10+/hour |
| Sentiment Scores | 10+/hour |
| ML Model AUC | 0.55-0.65 |
| Ollama Latency | 2-5 seconds |
| API Response | 200-500ms |
| LLM Cost | $0.00 |
| Hybrid Fusion Weight | 10-40% |

---

## 🆘 Quick Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| Ollama slow | Use phi3:mini model |
| No news | Check internet, wait 5 min |
| Hybrid not working | Check news < 1 hour old |
| API error | Restart: make api |
| ClickHouse error | Restart: make down && make up |

---

**Full documentation**: [END_TO_END_TESTING.md](docs/END_TO_END_TESTING.md)
