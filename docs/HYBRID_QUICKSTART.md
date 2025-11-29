# Hybrid ML + LLM Quick Start Guide

## 🚀 Getting Started with Hybrid Predictions

This guide will help you set up and use the hybrid ML + LLM system for enhanced FX forecasts.

---

## 📋 Prerequisites

1. **Existing FX-AI System**: You should have the base system running (ClickHouse, API, ML models)
2. **LLM API Keys**: OpenAI or Anthropic API key
3. **Python Dependencies**: Updated packages including `openai` and `anthropic`

---

## 🔧 Setup

### Step 1: Install New Dependencies

```bash
# Activate your virtual environment
source .venv/bin/activate

# Install updated dependencies
make deps
# Or manually:
pip install openai>=1.0 anthropic>=0.18 feedparser>=6.0
```

### Step 2: Configure LLM API Keys

Edit `.env` file:

```bash
# LLM Configuration
OPENAI_API_KEY=sk-your-actual-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-actual-anthropic-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=1000

# Hybrid ML+LLM Settings
ENABLE_LLM_FUSION=true
LLM_MAX_WEIGHT=0.4
LLM_MIN_CONFIDENCE=0.3
LLM_HIGH_IMPACT_THRESHOLD=7.0
LLM_CACHE_TTL_SECONDS=300
```

### Step 3: Initialize News Database Schema

```bash
# Apply new schema
docker exec -i fxai-clickhouse clickhouse-client -n < infra/sql/020_news_llm.sql

# Verify tables created
docker exec -i fxai-clickhouse clickhouse-client -q "SHOW TABLES FROM fxai LIKE '%news%'"
```

Expected output:
```
news_events
news_features
news_items
sentiment_scores
```

---

## 🧪 Testing the System

### Test 1: LLM Client

Create a test script `test_llm.py`:

```python
import asyncio
from datetime import datetime
from apps.llm.client import get_llm_client

async def test_sentiment():
    client = get_llm_client(provider="openai", model="gpt-4-turbo")
    
    result = await client.analyze_sentiment(
        headline="Fed Raises Rates by 25bps, Signals More Hikes Ahead",
        content="The Federal Reserve raised interest rates by 25 basis points today, bringing the target rate to 5.50%. Chair Powell indicated that further rate increases may be necessary to combat persistent inflation.",
        source="reuters",
        timestamp=datetime.now()
    )
    
    print(f"Sentiment Overall: {result.sentiment_overall}")
    print(f"Sentiment USD: {result.sentiment_usd}")
    print(f"Impact Score: {result.impact_score}/10")
    print(f"Confidence: {result.confidence}")
    print(f"Explanation: {result.explanation}")
    print(f"Cost: ${result.api_cost_usd:.4f}")

asyncio.run(test_sentiment())
```

Run:
```bash
python test_llm.py
```

Expected output:
```
Sentiment Overall: 0.75
Sentiment USD: 0.85
Impact Score: 9.0/10
Confidence: 0.9
Explanation: Fed's hawkish rate hike signals continued USD strength...
Cost: $0.0245
```

### Test 2: Bayesian Fusion

Create `test_fusion.py`:

```python
from apps.llm.fusion import (
    BayesianFusionEngine,
    MLPrediction,
    NewsSentiment
)

# Simulate ML prediction
ml_pred = MLPrediction(
    prob_up=0.58,
    expected_delta_bps=2.3,
    confidence=0.65,
    model_id="lgbm_USDINR_4h_test"
)

# Simulate news sentiment
news_sent = NewsSentiment(
    sentiment_score=0.75,  # Bullish
    confidence=0.85,
    impact_score=8.5,
    urgency="high",
    summary="Fed hawkish stance supports USD strength"
)

# Fuse predictions
engine = BayesianFusionEngine()
hybrid = engine.fuse(ml_pred, news_sent)

print(f"ML Probability: {hybrid.prob_up_ml:.3f}")
print(f"Hybrid Probability: {hybrid.prob_up_hybrid:.3f}")
print(f"ML Delta: {hybrid.expected_delta_ml:+.2f} bps")
print(f"Hybrid Delta: {hybrid.expected_delta_hybrid:+.2f} bps")
print(f"Weights: ML={hybrid.fusion_weight_ml:.1%}, LLM={hybrid.fusion_weight_llm:.1%}")
print(f"\nExplanation: {hybrid.explanation}")
```

Run:
```bash
python test_fusion.py
```

Expected output:
```
ML Probability: 0.580
Hybrid Probability: 0.697
ML Delta: +2.30 bps
Hybrid Delta: +3.12 bps
Weights: ML=65.0%, LLM=35.0%

Explanation: Technical analysis: bullish (prob=0.58) | News sentiment: bullish (score=+0.75, impact=8.5/10) | Context: Fed hawkish stance supports USD strength | Combined: bullish (prob=0.70, expected=+3.12 bps) | Weights: ML=65%, News=35%
```

---

## 📊 Usage Examples

### Example 1: Normal Market (ML-Dominant)

**Scenario**: Quiet trading day, no major news

```python
ml_pred = MLPrediction(prob_up=0.62, expected_delta_bps=2.5)
news_sent = NewsSentiment(sentiment_score=0.1, confidence=0.4, impact_score=3.0)

hybrid = engine.fuse(ml_pred, news_sent)
# Result: prob_up_hybrid ≈ 0.63 (minimal adjustment)
# Weights: ML=90%, LLM=10%
```

### Example 2: Breaking News (LLM-Dominant)

**Scenario**: Fed announces surprise rate hike

```python
ml_pred = MLPrediction(prob_up=0.55, expected_delta_bps=1.8)
news_sent = NewsSentiment(
    sentiment_score=0.9,
    confidence=0.95,
    impact_score=9.5,
    urgency="critical"
)

hybrid = engine.fuse(ml_pred, news_sent)
# Result: prob_up_hybrid ≈ 0.78 (significant boost)
# Weights: ML=60%, LLM=40%
```

### Example 3: High Uncertainty (Balanced + WAIT)

**Scenario**: Geopolitical crisis, conflicting signals

```python
ml_pred = MLPrediction(prob_up=0.68, expected_delta_bps=3.2)
news_sent = NewsSentiment(
    sentiment_score=-0.3,
    confidence=0.7,
    impact_score=8.0,
    urgency="high",
    summary="Geopolitical tensions create uncertainty"
)

hybrid = engine.fuse(ml_pred, news_sent)
# Result: prob_up_hybrid ≈ 0.58 (reduced confidence)
# Recommendation: WAIT (high uncertainty)
```

---

## 🔍 Monitoring

### Check LLM Usage and Costs

```sql
-- Daily LLM costs
SELECT 
  toDate(ts) AS date,
  model_version,
  sum(requests) AS total_requests,
  sum(total_cost_usd) AS total_cost,
  avg(avg_latency_ms) AS avg_latency
FROM fxai.llm_usage
WHERE ts >= today() - 7
GROUP BY date, model_version
ORDER BY date DESC;
```

### Check Sentiment Scores

```sql
-- Recent sentiment analysis
SELECT 
  ts,
  news_id,
  sentiment_usd,
  sentiment_inr,
  impact_score,
  confidence,
  explanation
FROM fxai.sentiment_scores
ORDER BY ts DESC
LIMIT 10;
```

### Check Hybrid Predictions

```sql
-- Compare ML vs Hybrid predictions
SELECT 
  ts,
  pair,
  horizon,
  prob_up_ml,
  prob_up_hybrid,
  prob_up_hybrid - prob_up_ml AS adjustment,
  fusion_weight_llm,
  recommendation
FROM fxai.hybrid_predictions
ORDER BY ts DESC
LIMIT 10;
```

---

## 💰 Cost Management

### Estimated Costs

**Development/Testing** (100 forecasts/day):
- OpenAI GPT-4 Turbo: ~$2-5/day
- Anthropic Claude Sonnet: ~$1-3/day

**Production** (10,000 forecasts/day with caching):
- With 50% cache hit rate: ~$40-50/month
- With 75% cache hit rate: ~$25-30/month

### Cost Optimization Tips

1. **Enable Caching**: Cache sentiment for 5 minutes (default)
2. **Smart Triggering**: Only call LLM when new news exists
3. **Batch Processing**: Group similar news items
4. **Use Claude for Medium Priority**: Cheaper alternative to GPT-4
5. **Set Spending Limits**: Configure OpenAI/Anthropic billing alerts

---

## 🎯 Configuration Tuning

### Fusion Parameters

Adjust in `.env`:

```bash
# Maximum weight given to LLM (0-1)
# Higher = more influence from news
LLM_MAX_WEIGHT=0.4  # Default: 40% max

# Minimum confidence to use LLM
# Lower = use more news (but less reliable)
LLM_MIN_CONFIDENCE=0.3  # Default: 30%

# Impact threshold for "high-impact" news
# Lower = more news classified as high-impact
LLM_HIGH_IMPACT_THRESHOLD=7.0  # Default: 7/10
```

### Recommended Settings

**Conservative** (trust ML more):
```bash
LLM_MAX_WEIGHT=0.25
LLM_MIN_CONFIDENCE=0.5
LLM_HIGH_IMPACT_THRESHOLD=8.0
```

**Aggressive** (trust news more):
```bash
LLM_MAX_WEIGHT=0.5
LLM_MIN_CONFIDENCE=0.2
LLM_HIGH_IMPACT_THRESHOLD=6.0
```

**Balanced** (default):
```bash
LLM_MAX_WEIGHT=0.4
LLM_MIN_CONFIDENCE=0.3
LLM_HIGH_IMPACT_THRESHOLD=7.0
```

---

## 🐛 Troubleshooting

### Issue: "openai package not installed"

**Solution**:
```bash
pip install openai>=1.0
```

### Issue: "Invalid API key"

**Solution**:
1. Check `.env` file has correct key
2. Verify key is active on OpenAI/Anthropic dashboard
3. Check for extra spaces or quotes in `.env`

### Issue: High LLM costs

**Solution**:
1. Enable caching: `LLM_CACHE_TTL_SECONDS=300`
2. Increase confidence threshold: `LLM_MIN_CONFIDENCE=0.5`
3. Use cheaper model: `LLM_MODEL=gpt-3.5-turbo` or `claude-3-haiku`
4. Reduce max tokens: `LLM_MAX_TOKENS=500`

### Issue: Slow response times

**Solution**:
1. Use async processing (already implemented)
2. Cache aggressively
3. Use faster model: `claude-3-haiku` (200ms vs 2s)
4. Process news in background worker

---

## 📚 Next Steps

1. **Implement News Ingestion Worker** (Phase 2)
2. **Add News Feature Computation** (Phase 2)
3. **Enhance API with Hybrid Endpoint** (Phase 3)
4. **Retrain Models with News Features** (Phase 4)
5. **Deploy to Production** (Phase 5)

---

## 🔗 Related Documentation

- [LLM Integration Design](./LLM_Integration_Design.md)
- [Product Requirements Document](./PRD.md)
- [Main README](../README.md)

---

**Questions?** Check the main documentation or create an issue on GitHub.
