# Testing Summary - Quick Start

## 🎯 Three Simple Commands

### 1. Quick Test (5 minutes) ⚡
```bash
make e2e-quick
```
**Tests everything that's already set up**

### 2. Full Test (2-3 hours) 🔬
```bash
make e2e-full
```
**Complete test from scratch (data ingestion + training + testing)**

### 3. Component Tests 🧩
```bash
make test-ollama        # Test Ollama LLM
make test-hybrid-api    # Test API endpoints
```

---

## 📊 What Gets Tested

| Component | Quick Test | Full Test | Manual Test |
|-----------|------------|-----------|-------------|
| Infrastructure | ✓ | ✓ | ✓ |
| Data Ingestion | Check only | ✓ | ✓ |
| Model Training | Check only | ✓ | ✓ |
| Ollama LLM | ✓ | ✓ | ✓ |
| News Ingestion | Check only | ✓ | ✓ |
| API Endpoints | ✓ | ✓ | ✓ |
| Hybrid Predictions | ✓ | ✓ | ✓ |
| Performance | ✓ | ✓ | ✓ |
| Error Handling | - | - | ✓ |
| Load Testing | - | - | ✓ |

---

## ✅ Expected Results

### Quick Test Output
```
==========================================
  Test Summary
==========================================

Passed: 18
Failed: 0

🎉 All tests passed! System is ready.

Next steps:
  1. Start news ingester: make news-ingester
  2. Start API server: make api
  3. Test hybrid forecast: make curl-hybrid
```

### What 18 Tests Cover
1. ✓ Docker installed
2. ✓ Python installed
3. ✓ Ollama installed
4. ✓ Llama3 model available
5. ✓ ClickHouse running
6. ✓ Kafka running
7. ✓ Database initialized
8. ✓ Price data available
9. ✓ Features available
10. ✓ ML model trained
11. ✓ Ollama service running
12. ✓ Ollama sentiment working
13. ✓ API server running
14. ✓ Health endpoint working
15. ✓ ML-only forecast working
16. ✓ Hybrid forecast working
17. ✓ Hybrid fusion enabled
18. ✓ API response time <1s

---

## 🚀 Recommended Workflow

### First Time Setup
```bash
# 1. Setup Ollama (5 min)
make setup-ollama

# 2. Run full test (2-3 hours)
make e2e-full

# 3. Start services
make news-ingester &  # Terminal 1
make api &            # Terminal 2

# 4. Test it
make curl-hybrid
```

### Daily Development
```bash
# Quick validation
make e2e-quick

# If all pass, you're good to go!
```

### Before Production
```bash
# Full validation
make e2e-full

# Load test
ab -n 1000 -c 10 -H "X-API-Key: changeme-dev-key" \
  "http://localhost:8080/v1/forecast?pair=USDINR&h=4h&use_hybrid=true"
```

---

## 📚 Documentation

| Document | Purpose | Time |
|----------|---------|------|
| [TESTING_GUIDE.md](docs/TESTING_GUIDE.md) | Quick reference | 5 min read |
| [END_TO_END_TESTING.md](docs/END_TO_END_TESTING.md) | Complete guide | 30 min read |
| [TEST_CHECKLIST.md](TEST_CHECKLIST.md) | Checklist format | 2 min read |

---

## 🎯 Success Criteria

**Minimum** (Development):
- [ ] Infrastructure running
- [ ] Ollama working
- [ ] API responding

**Recommended** (Staging):
- [ ] All minimum + data + model
- [ ] News ingestion active
- [ ] Hybrid predictions working

**Production-Ready**:
- [ ] All recommended + performance
- [ ] 24-hour stability test
- [ ] Load test passed

---

## 🆘 Quick Troubleshooting

| Issue | Fix |
|-------|-----|
| Docker not running | `open -a Docker` |
| Ollama not running | `ollama serve &` |
| No price data | `make ingest-usdinr` |
| No ML model | `make train-lgbm PAIR=USDINR HORIZON=4h` |
| API not responding | `make api` |
| Hybrid not working | `make news-ingester` |

---

## 🎉 Get Started Now

```bash
# One command to test everything
make e2e-quick
```

**That's it!** 🚀

---

**Full documentation**: See `docs/` folder
