# LLM Integration Design Document
## FX-AI Advisor — News & Sentiment Analysis Layer

**Version:** 1.0  
**Date:** November 28, 2025  
**Status:** Proposed Enhancement  
**Priority:** High  

---

## 🎯 Executive Summary

### Objective
Integrate Large Language Models (LLMs) to analyze real-time news, social media, and central bank communications to enhance FX trading recommendations with sentiment analysis and event interpretation.

### Value Proposition
- **Capture Market-Moving Events**: React to breaking news before it's reflected in price data
- **Sentiment-Aware Decisions**: Incorporate market sentiment into probability adjustments
- **Richer Explanations**: Provide context-aware narratives for recommendations
- **Early Warning System**: Detect emerging risks from news flow

### Success Metrics
- **News Processing Latency**: <10 seconds from publication to sentiment score
- **Sentiment Accuracy**: >70% correlation with subsequent price moves
- **Explanation Quality**: >80% user satisfaction with narrative clarity
- **False Positive Rate**: <20% for high-impact event detection

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     News Ingestion Layer                         │
│  RSS Feeds │ APIs │ Twitter/X │ Central Bank Websites           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Processing Pipeline                       │
│  Relevance Filter → Sentiment Analysis → Entity Extraction      │
│  → Impact Scoring → Event Classification                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      News Feature Store                          │
│  fxai.news_items │ fxai.sentiment_scores │ fxai.news_events    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Enhanced Decision Engine                       │
│  Technical Features + News Sentiment → Bayesian Update          │
│  → Adjusted Probability → Recommendation + Rich Narrative       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Model Extensions

### New Tables

#### news_items
**Purpose**: Store raw news articles and social media posts

```sql
CREATE TABLE IF NOT EXISTS fxai.news_items (
  id String,                              -- Unique news item ID
  ts DateTime64(3),                       -- Publication timestamp
  source LowCardinality(String),          -- reuters, bloomberg, twitter, rbi, fed
  headline String,                        -- Article headline
  content String,                         -- Full article text (or tweet)
  url String,                             -- Source URL
  author String DEFAULT '',               -- Author/publisher
  language LowCardinality(String) DEFAULT 'en',
  raw_json String                         -- Original JSON for debugging
) ENGINE=MergeTree
ORDER BY (ts, source)
TTL toDateTime(ts) + INTERVAL 90 DAY;
```

#### sentiment_scores
**Purpose**: LLM-generated sentiment analysis

```sql
CREATE TABLE IF NOT EXISTS fxai.sentiment_scores (
  news_id String,                         -- Reference to news_items.id
  ts DateTime64(3),                       -- Analysis timestamp
  model_version String,                   -- LLM model used (gpt-4, claude-3, etc.)
  
  -- Sentiment scores (-1 to +1)
  sentiment_overall Float32,              -- Overall market sentiment
  sentiment_usd Float32,                  -- USD-specific sentiment
  sentiment_inr Float32,                  -- INR-specific sentiment
  
  -- Confidence and impact
  confidence Float32,                     -- Model confidence (0-1)
  impact_score Float32,                   -- Predicted impact magnitude (0-10)
  urgency Enum8('low'=0,'medium'=1,'high'=2,'critical'=3),
  
  -- Entity extraction
  currencies Array(String),               -- Mentioned currencies
  countries Array(String),                -- Mentioned countries
  institutions Array(String),             -- Central banks, governments, etc.
  topics Array(String),                   -- inflation, rates, trade, geopolitics
  
  -- Reasoning
  explanation String,                     -- LLM's reasoning
  key_phrases Array(String),              -- Important extracted phrases
  
  processing_time_ms UInt32               -- Performance tracking
) ENGINE=MergeTree
ORDER BY (ts, news_id);
```

#### news_events
**Purpose**: Structured events extracted from news

```sql
CREATE TABLE IF NOT EXISTS fxai.news_events (
  event_id String,                        -- Unique event ID
  ts DateTime64(3),                       -- Event timestamp
  event_type LowCardinality(String),      -- rate_decision, inflation_data, geopolitical, etc.
  
  -- Event details
  title String,                           -- Event title (LLM-generated)
  summary String,                         -- Brief summary
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
ORDER BY (ts, event_type);
```

#### news_features
**Purpose**: Time-series features derived from news for ML models

```sql
CREATE TABLE IF NOT EXISTS fxai.news_features (
  ts DateTime,                            -- Minute-aligned timestamp
  pair LowCardinality(String),            -- Currency pair
  
  -- Sentiment aggregates (rolling windows)
  sentiment_1h Float32,                   -- Avg sentiment last 1 hour
  sentiment_4h Float32,                   -- Avg sentiment last 4 hours
  sentiment_24h Float32,                  -- Avg sentiment last 24 hours
  
  -- Volume metrics
  news_count_1h UInt16,                   -- News items last 1 hour
  high_impact_count_1h UInt16,            -- High-impact news last 1 hour
  
  -- Volatility indicators
  sentiment_volatility_1h Float32,        -- Std dev of sentiment
  topic_diversity Float32,                -- Entropy of topics discussed
  
  -- Event proximity
  minutes_to_critical_event Int32,        -- Time to next critical news event
  ongoing_event_severity UInt8            -- Current event severity (0-3)
) ENGINE=MergeTree
ORDER BY (pair, ts);
```

---

## 🤖 LLM Processing Pipeline

### Stage 1: News Ingestion

**Sources**:
- **RSS Feeds**: Reuters, Bloomberg, ForexLive, FXStreet
- **APIs**: NewsAPI, Alpha Vantage News, Finnhub
- **Twitter/X**: Official central bank accounts, financial journalists
- **Central Banks**: RBI, Fed, ECB press releases and speeches
- **Government**: Treasury announcements, economic data releases

**Ingestion Worker** (`apps/workers/news_ingester.py`):
```python
class NewsIngester:
    def __init__(self):
        self.sources = [
            RSSSource("https://www.reuters.com/finance/rss"),
            TwitterSource(accounts=["RBI", "federalreserve"]),
            APISource("newsapi.org", api_key=...),
        ]
    
    async def ingest_continuous(self):
        while True:
            for source in self.sources:
                items = await source.fetch_latest()
                await self.store_news_items(items)
            await asyncio.sleep(60)  # Poll every minute
```

### Stage 2: Relevance Filtering

**Purpose**: Filter out irrelevant news to reduce LLM costs

**Approach**: Lightweight classifier (BERT-based or keyword matching)

**Criteria**:
- Contains currency mentions (USD, INR, EUR, etc.)
- Contains FX-related keywords (exchange rate, forex, central bank, etc.)
- From trusted financial sources
- Published within last 24 hours

**Implementation**:
```python
def is_relevant(news_item: NewsItem) -> bool:
    # Quick keyword check
    keywords = ["forex", "exchange rate", "currency", "central bank", "fed", "rbi"]
    if not any(kw in news_item.headline.lower() for kw in keywords):
        return False
    
    # Currency mention check
    currencies = ["USD", "INR", "EUR", "GBP", "JPY"]
    if not any(curr in news_item.content for curr in currencies):
        return False
    
    return True
```

### Stage 3: LLM Sentiment Analysis

**LLM Options**:
1. **OpenAI GPT-4** (Primary): Best reasoning, expensive
2. **Anthropic Claude 3** (Backup): Good balance of cost/performance
3. **Local LLM (Llama 3)**: Cost-effective, requires GPU infrastructure

**Prompt Template**:
```python
SENTIMENT_PROMPT = """
You are a financial analyst specializing in foreign exchange markets.

Analyze the following news article and provide:
1. Overall market sentiment (-1 to +1, where -1 is very bearish, +1 is very bullish)
2. USD-specific sentiment (-1 to +1)
3. INR-specific sentiment (-1 to +1)
4. Impact score (0-10, where 10 is market-moving)
5. Urgency (low, medium, high, critical)
6. Affected currency pairs (list)
7. Key topics (list: inflation, interest_rates, trade, geopolitics, etc.)
8. Brief explanation (2-3 sentences)

News Article:
Headline: {headline}
Content: {content}
Source: {source}
Published: {timestamp}

Respond in JSON format:
{{
  "sentiment_overall": <float>,
  "sentiment_usd": <float>,
  "sentiment_inr": <float>,
  "impact_score": <float>,
  "urgency": "<string>",
  "affected_pairs": [<strings>],
  "topics": [<strings>],
  "explanation": "<string>",
  "confidence": <float>
}}
"""
```

**Implementation**:
```python
async def analyze_sentiment(news_item: NewsItem) -> SentimentScore:
    prompt = SENTIMENT_PROMPT.format(
        headline=news_item.headline,
        content=news_item.content[:2000],  # Truncate for token limits
        source=news_item.source,
        timestamp=news_item.ts
    )
    
    response = await openai.ChatCompletion.acreate(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,  # Lower temp for consistency
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    return SentimentScore(**result, news_id=news_item.id)
```

### Stage 4: Event Extraction

**Purpose**: Aggregate related news into structured events

**Approach**: Clustering + LLM summarization

**Event Detection Prompt**:
```python
EVENT_EXTRACTION_PROMPT = """
You are analyzing a collection of related news articles about a potential market-moving event.

Articles:
{articles}

Determine:
1. Is this a significant event? (yes/no)
2. Event type (rate_decision, inflation_data, geopolitical_crisis, trade_announcement, etc.)
3. Event title (concise, 5-10 words)
4. Summary (2-3 sentences)
5. Severity (low, medium, high, critical)
6. Affected currency pairs
7. Expected direction (bullish_usd, bearish_usd, mixed, unknown)
8. Expected volatility increase (0-1)
9. Time horizon in minutes (how long will impact last)

Respond in JSON format.
"""
```

### Stage 5: Feature Aggregation

**Purpose**: Create time-series features for ML models

**Aggregation Logic**:
```python
def compute_news_features(pair: str, ts: datetime) -> NewsFeatures:
    # Fetch sentiment scores from last 24 hours
    scores = query_sentiment_scores(pair, lookback_hours=24)
    
    # Rolling aggregates
    sentiment_1h = scores.last_1h().mean()
    sentiment_4h = scores.last_4h().mean()
    sentiment_24h = scores.mean()
    
    # Volume metrics
    news_count_1h = len(scores.last_1h())
    high_impact_count_1h = len(scores.last_1h().filter(impact_score > 7))
    
    # Volatility
    sentiment_volatility_1h = scores.last_1h().std()
    
    # Event proximity
    next_event = query_next_critical_event(pair)
    minutes_to_event = (next_event.ts - ts).total_seconds() / 60 if next_event else -1
    
    return NewsFeatures(
        ts=ts, pair=pair,
        sentiment_1h=sentiment_1h,
        sentiment_4h=sentiment_4h,
        sentiment_24h=sentiment_24h,
        news_count_1h=news_count_1h,
        high_impact_count_1h=high_impact_count_1h,
        sentiment_volatility_1h=sentiment_volatility_1h,
        minutes_to_critical_event=minutes_to_event
    )
```

---

## 🎯 Integration with Existing System

### Enhanced Feature Set

**Original Features** (10):
- ret_1m, ret_5m, ret_15m
- vol_5m, vol_15m
- sma_5, sma_15
- momentum_15m
- minutes_to_event, is_high_importance

**New News Features** (8):
- sentiment_1h, sentiment_4h, sentiment_24h
- news_count_1h, high_impact_count_1h
- sentiment_volatility_1h
- topic_diversity
- minutes_to_critical_event

**Total Features**: 18

### Bayesian Probability Update

**Current**: Model outputs `prob_up` directly

**Enhanced**: Adjust probability based on news sentiment

```python
def bayesian_update(prior_prob: float, sentiment_score: float, confidence: float) -> float:
    """
    Update probability using Bayes' rule with sentiment as evidence.
    
    Args:
        prior_prob: Model's base probability (0-1)
        sentiment_score: News sentiment (-1 to +1)
        confidence: LLM confidence in sentiment (0-1)
    
    Returns:
        Posterior probability (0-1)
    """
    # Convert sentiment to likelihood ratio
    # Positive sentiment increases prob_up, negative decreases it
    sentiment_weight = 0.3 * confidence  # Max 30% adjustment
    adjustment = sentiment_score * sentiment_weight
    
    # Bayesian update (simplified)
    posterior = prior_prob + adjustment * (1 - prior_prob) if adjustment > 0 else prior_prob * (1 + adjustment)
    
    return np.clip(posterior, 0.0, 1.0)
```

**Example**:
- Model says: `prob_up = 0.55` (weak bullish)
- News sentiment: `+0.8` (strong bullish), confidence `0.9`
- Adjustment: `0.8 * 0.3 * 0.9 = 0.216`
- Posterior: `0.55 + 0.216 * (1 - 0.55) = 0.647` ✅

### Enhanced API Response

**Before**:
```json
{
  "prob_up": 0.62,
  "recommendation": "NOW",
  "explanation": ["model=lgbm_USDINR_4h", "policy=expected"]
}
```

**After**:
```json
{
  "prob_up": 0.62,
  "prob_up_prior": 0.55,
  "prob_up_posterior": 0.67,
  "recommendation": "NOW",
  "explanation": [
    "model=lgbm_USDINR_4h",
    "policy=expected",
    "news_sentiment=+0.8 (bullish)",
    "recent_events: RBI holds rates steady, USD strength on Fed hawkish comments"
  ],
  "news_summary": "Recent news suggests USD strength due to Federal Reserve's hawkish stance on inflation. RBI's decision to hold rates steady supports INR stability. Net sentiment favors USD appreciation.",
  "news_confidence": 0.85,
  "news_count_1h": 3,
  "high_impact_events": [
    {
      "title": "Fed Chair Powell signals prolonged higher rates",
      "severity": "high",
      "sentiment_usd": 0.9,
      "published": "2025-11-28T14:30:00Z"
    }
  ]
}
```

### Enhanced Decision Logic

```python
def enhanced_forecast(pair: str, horizon: str) -> ForecastResponse:
    # 1. Get technical features and model prediction
    tech_features = build_features(pair)
    model_pred = model.predict(tech_features)
    prior_prob = model_pred["prob_up"]
    
    # 2. Get news features and sentiment
    news_features = build_news_features(pair)
    sentiment_1h = news_features["sentiment_1h"]
    sentiment_confidence = news_features.get("confidence", 0.5)
    
    # 3. Bayesian update
    posterior_prob = bayesian_update(prior_prob, sentiment_1h, sentiment_confidence)
    
    # 4. Adjust expected delta based on news
    base_delta = model_pred["expected_delta_bps"]
    news_multiplier = 1.0 + (sentiment_1h * 0.3)  # Up to 30% adjustment
    adjusted_delta = base_delta * news_multiplier
    
    # 5. Generate rich narrative
    narrative = generate_narrative(pair, model_pred, news_features)
    
    # 6. Apply decision policy with posterior probability
    recommendation = choose_recommendation(
        {"prob_up": posterior_prob, "expected_delta_bps": adjusted_delta},
        policy=DECISION_POLICY,
        spread_bps=DECISION_SPREAD_BPS
    )
    
    return ForecastResponse(
        prob_up=posterior_prob,
        prob_up_prior=prior_prob,
        expected_delta_bps=adjusted_delta,
        recommendation=recommendation,
        news_summary=narrative,
        news_confidence=sentiment_confidence,
        ...
    )
```

---

## 🛠️ Implementation Plan

### Phase 1: Infrastructure (Week 1-2)

**Tasks**:
- [ ] Create new database tables (news_items, sentiment_scores, news_events, news_features)
- [ ] Set up LLM API clients (OpenAI, Anthropic)
- [ ] Implement news ingestion worker
- [ ] Set up RSS/API connectors

**Deliverables**:
- Database schema migrations
- News ingestion daemon
- Basic news storage

### Phase 2: LLM Pipeline (Week 3-4)

**Tasks**:
- [ ] Implement sentiment analysis with GPT-4
- [ ] Build relevance filtering
- [ ] Create event extraction logic
- [ ] Develop feature aggregation

**Deliverables**:
- LLM processing pipeline
- Sentiment scoring system
- News feature computation

### Phase 3: Integration (Week 5-6)

**Tasks**:
- [ ] Extend feature set with news features
- [ ] Implement Bayesian probability update
- [ ] Enhance API response with news context
- [ ] Update decision engine

**Deliverables**:
- Enhanced forecast endpoint
- Bayesian update logic
- Rich narrative generation

### Phase 4: Model Retraining (Week 7-8)

**Tasks**:
- [ ] Retrain LightGBM with 18 features (including news)
- [ ] Backtest with news-enhanced models
- [ ] Compare performance vs baseline
- [ ] Optimize feature weights

**Deliverables**:
- News-enhanced models
- Performance comparison report
- Optimized feature set

### Phase 5: Monitoring & Optimization (Week 9-10)

**Tasks**:
- [ ] Set up LLM cost tracking
- [ ] Implement caching for repeated news
- [ ] Add sentiment accuracy monitoring
- [ ] Create news dashboard

**Deliverables**:
- Cost monitoring dashboard
- Performance metrics
- Production deployment

---

## 💰 Cost Analysis

### LLM API Costs

**OpenAI GPT-4 Turbo Pricing** (as of Nov 2025):
- Input: $10 / 1M tokens
- Output: $30 / 1M tokens

**Estimated Usage**:
- News items per day: ~500 (filtered from ~2000 raw)
- Avg tokens per analysis: 1500 input + 500 output
- Daily cost: 500 * (1500 * $10 + 500 * $30) / 1M = **$15/day**
- Monthly cost: **~$450**

**Cost Optimization Strategies**:
1. **Relevance Filtering**: Reduce items by 75% → **$112.50/month**
2. **Caching**: Cache sentiment for duplicate news → **-20%** → **$90/month**
3. **Local LLM**: Use Llama 3 for low-priority news → **-50%** → **$45/month**
4. **Batch Processing**: Group similar news → **-10%** → **$40/month**

**Target**: **$40-50/month** for production

### Infrastructure Costs

**Additional Resources**:
- **Storage**: +50GB for news data → **$5/month**
- **Compute**: News ingestion worker → **$20/month**
- **GPU** (optional, for local LLM): **$100-200/month**

**Total Additional Cost**: **$65-75/month** (cloud LLM) or **$165-275/month** (local LLM)

---

## 📊 Expected Performance Improvements

### Baseline (Current System)
- **Win Rate**: 60-65% (technical features only)
- **AUC**: 0.55-0.58
- **Avg PnL**: 1.5-2.0 bps per trade

### With News Integration (Projected)
- **Win Rate**: 65-72% (+5-7 percentage points)
- **AUC**: 0.60-0.65 (+0.05-0.07)
- **Avg PnL**: 2.5-3.5 bps per trade (+1.0-1.5 bps)

### Key Improvements
1. **Early Event Detection**: Capture moves before price reflects news
2. **Reduced False Signals**: Filter out noise during high-impact events
3. **Better Embargo Logic**: More nuanced event risk assessment
4. **Richer Explanations**: Users understand *why* recommendation was made

---

## 🚨 Risks & Mitigations

### Risk 1: LLM Hallucinations
**Impact**: Incorrect sentiment leading to bad recommendations  
**Mitigation**:
- Use structured JSON output with validation
- Implement confidence thresholds (ignore low-confidence scores)
- Cross-reference with multiple news sources
- Human review of critical events

### Risk 2: API Rate Limits
**Impact**: Unable to process news in real-time  
**Mitigation**:
- Implement request queuing and retry logic
- Use multiple API keys for redundancy
- Cache results aggressively
- Fallback to baseline model if LLM unavailable

### Risk 3: Cost Overruns
**Impact**: Monthly costs exceed budget  
**Mitigation**:
- Set hard spending limits via API quotas
- Monitor costs daily
- Implement tiered processing (GPT-4 for critical, Claude for medium, local for low)
- Use relevance filtering aggressively

### Risk 4: Latency
**Impact**: News processing too slow for real-time trading  
**Mitigation**:
- Async processing pipeline
- Parallel LLM calls for multiple news items
- Pre-compute features every minute
- Cache recent sentiment scores

### Risk 5: Data Quality
**Impact**: Poor quality news sources reduce accuracy  
**Mitigation**:
- Whitelist trusted sources only
- Implement source quality scoring
- Detect and filter spam/duplicate content
- Regular audit of news quality

---

## 🎯 Success Criteria

### Technical Metrics
- [ ] News processing latency <10 seconds (p95)
- [ ] Sentiment accuracy >70% (validated against price moves)
- [ ] LLM API uptime >99%
- [ ] Cost per forecast <$0.10

### Business Metrics
- [ ] Win rate improvement >5 percentage points
- [ ] User satisfaction with explanations >80%
- [ ] Reduction in false positives >20%
- [ ] API usage increase >30% (due to better quality)

### Operational Metrics
- [ ] Zero critical incidents from LLM failures
- [ ] Monthly LLM costs <$100
- [ ] News ingestion uptime >99.5%
- [ ] Feature computation time <15 seconds

---

## 📚 Example Use Cases

### Use Case 1: Fed Rate Decision

**Scenario**: Fed announces 25bps rate hike (hawkish)

**News Flow**:
1. **T-0**: Reuters headline: "Fed raises rates 25bps, signals more hikes ahead"
2. **T+30s**: LLM analyzes → sentiment_usd: +0.9, impact: 9/10, urgency: critical
3. **T+60s**: Event extracted: "Fed hawkish rate hike"
4. **T+90s**: Features updated: sentiment_1h: +0.85, high_impact_count_1h: 1

**Model Response**:
- Prior prob_up (USDINR): 0.52 (neutral)
- News adjustment: +0.25 (strong USD bullish)
- Posterior prob_up: 0.77 (high confidence)
- Recommendation: **NOW** (buy USD, sell INR)
- Explanation: "Federal Reserve's hawkish rate hike signals continued USD strength. Expect USDINR to rise 5-8 bps over next 4 hours."

### Use Case 2: Geopolitical Crisis

**Scenario**: Unexpected geopolitical tension in Middle East

**News Flow**:
1. Multiple breaking news alerts
2. LLM detects: high uncertainty, risk-off sentiment
3. Sentiment volatility spikes
4. Event classified: "geopolitical_crisis", severity: high

**Model Response**:
- Prior prob_up: 0.65 (bullish)
- News adjustment: -0.15 (risk-off reduces confidence)
- Posterior prob_up: 0.50 (neutral)
- Recommendation: **WAIT** (high uncertainty)
- Explanation: "Geopolitical tensions create elevated uncertainty. Recommend waiting for clarity before taking positions."

### Use Case 3: RBI Policy Statement

**Scenario**: RBI maintains status quo but hints at future easing

**News Flow**:
1. RBI press release analyzed
2. LLM detects dovish undertones despite no rate change
3. Sentiment_INR: -0.4 (mildly bearish INR)

**Model Response**:
- Prior prob_up: 0.58 (mildly bullish)
- News adjustment: +0.10 (dovish RBI supports USD/INR rise)
- Posterior prob_up: 0.68 (bullish)
- Recommendation: **NOW** (if expected_delta > spread)
- Explanation: "RBI's dovish tone suggests potential future easing, supporting USDINR appreciation."

---

## 🔄 Future Enhancements

### Phase 2: Advanced NLP
- **Named Entity Recognition**: Extract specific people, institutions, policies
- **Relationship Extraction**: Map causal relationships (e.g., "inflation → rate hike → USD strength")
- **Temporal Analysis**: Track how sentiment evolves over time
- **Multi-lingual Support**: Analyze non-English sources (Hindi, Chinese, etc.)

### Phase 3: Social Media Integration
- **Twitter/X Sentiment**: Track financial influencers and traders
- **Reddit Analysis**: Monitor r/forex, r/wallstreetbets
- **Telegram Channels**: Analyze trading group sentiment
- **Sentiment Aggregation**: Combine professional news + social media

### Phase 4: Predictive Analytics
- **Event Forecasting**: Predict upcoming events from news patterns
- **Sentiment Momentum**: Track rate of sentiment change
- **Contrarian Signals**: Detect over-optimism/pessimism
- **Narrative Tracking**: Follow evolving market narratives

### Phase 5: Explainable AI
- **SHAP Values**: Show contribution of each news item to decision
- **Attention Visualization**: Highlight key phrases in news
- **Counterfactual Analysis**: "What if this news didn't happen?"
- **Confidence Intervals**: Probabilistic ranges for predictions

---

## 📖 References

### LLM Providers
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Llama 3 Model Card](https://huggingface.co/meta-llama/Meta-Llama-3-8B)

### News Sources
- [Reuters API](https://www.reuters.com/tools/api)
- [NewsAPI](https://newsapi.org/)
- [Alpha Vantage News](https://www.alphavantage.co/documentation/#news-sentiment)
- [Finnhub News API](https://finnhub.io/docs/api/news)

### Research Papers
- "Large Language Models for Financial Sentiment Analysis" (2024)
- "News-Driven Trading Strategies in FX Markets" (2023)
- "Bayesian Updating with LLM-Generated Priors" (2024)

---

**Document Status**: 📝 Draft for Review  
**Next Steps**: Team review → Cost approval → Implementation kickoff  
**Owner**: Product & Engineering Teams  
**Estimated Timeline**: 10 weeks to production
