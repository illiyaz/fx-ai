# News Ingestion Guide

## 📰 Overview

The news ingestion system fetches FX-related news from multiple sources and optionally analyzes sentiment using LLMs.

---

## 🔧 Setup

### Step 1: Initialize Database Schema

```bash
make init-news-schema
```

This creates the following tables:
- `fxai.news_items` - Raw news articles
- `fxai.sentiment_scores` - LLM sentiment analysis
- `fxai.news_events` - Structured events
- `fxai.news_features` - Time-series features

### Step 2: Configure News Sources

Edit `.env`:

```bash
# News Ingestion
NEWS_POLL_INTERVAL_SEC=60        # Poll every 60 seconds
NEWS_LOOKBACK_HOURS=1             # Fetch last 1 hour of news
NEWS_ENABLE_SENTIMENT=true        # Enable LLM analysis
NEWS_SENTIMENT_BATCH_SIZE=5       # Analyze 5 items per cycle

# Optional: API keys for additional sources
NEWSAPI_KEY=your-newsapi-key-here
ALPHAVANTAGE_KEY=your-alphavantage-key-here
```

### Step 3: Test the System

```bash
python scripts/test_news_ingestion.py
```

Expected output:
```
✓ PASS: RSS Fetching
✓ PASS: Relevance Filter
✓ PASS: LLM Sentiment
✓ PASS: Database

🎉 All tests passed! News ingestion system is ready.
```

---

## 🚀 Running the Ingester

### Option 1: With LLM Sentiment Analysis

```bash
make news-ingester
```

This will:
1. Fetch news from RSS feeds every 60 seconds
2. Filter for FX-relevant articles
3. Store in `fxai.news_items`
4. Analyze sentiment with LLM
5. Store results in `fxai.sentiment_scores`

### Option 2: Without LLM (Faster, Free)

```bash
make news-ingester-no-llm
```

This skips sentiment analysis to save costs and time.

### Option 3: Custom Configuration

```bash
NEWS_POLL_INTERVAL_SEC=30 NEWS_SENTIMENT_BATCH_SIZE=10 make news-ingester
```

---

## 📊 Monitoring

### View Recent News

```bash
make tail-news
```

Output:
```
2025-11-28 14:30:00  reuters  Fed Raises Rates by 25bps
2025-11-28 14:25:00  forexlive  USD/INR hits 83.50
2025-11-28 14:20:00  bloomberg  ECB Holds Rates Steady
```

### View Sentiment Analysis

```bash
make tail-sentiment
```

Output:
```
ts                   sentiment_usd  sentiment_inr  impact  conf  explanation
2025-11-28 14:30:00  0.85          -0.20          9.0     0.90  Fed hawkish...
2025-11-28 14:25:00  0.30           0.10          5.5     0.75  Market...
```

### Check News Sources

```bash
make count-news
```

Output:
```
source              count
forexlive           45
reuters_business    32
fxstreet            28
investing_forex     21
```

### Monitor LLM Costs

```bash
make llm-costs
```

Output:
```
date        model_version    total_cost
2025-11-28  gpt-4-turbo     $2.45
2025-11-27  gpt-4-turbo     $3.12
2025-11-26  gpt-4-turbo     $1.89
```

---

## 📡 News Sources

### Default RSS Feeds (Free)

The system includes these RSS feeds by default:

| Source | URL | Update Frequency |
|--------|-----|------------------|
| **ForexLive** | forexlive.com/feed/news | Real-time |
| **FXStreet** | fxstreet.com/rss/news | Every 15 min |
| **Investing.com** | investing.com/rss/news_285.rss | Every 30 min |
| **Reuters** | reutersagency.com/feed | Every hour |
| **MarketWatch** | marketwatch.com/rss/economy | Every hour |

### Optional API Sources (Paid)

**NewsAPI.org** ($449/month for commercial):
- 100,000 requests/month
- Real-time news from 150,000+ sources
- Sign up: https://newsapi.org/pricing

**Alpha Vantage** (Free tier available):
- 25 requests/day (free)
- 1,200 requests/day ($49.99/month)
- Sign up: https://www.alphavantage.co/support/#api-key

---

## 🔍 How It Works

### 1. News Fetching

```python
# Every 60 seconds:
for source in sources:
    items = await source.fetch_latest(lookback_hours=1)
    # Returns: List[NewsItem]
```

### 2. Relevance Filtering

```python
def is_relevant(item: NewsItem) -> bool:
    keywords = ["forex", "currency", "central bank", "fed", "rbi", ...]
    text = item.headline + " " + item.content
    return any(keyword in text.lower() for keyword in keywords)
```

Filters out ~75% of non-FX news.

### 3. Deduplication

```python
# Track seen news IDs to avoid duplicates
if item.id not in seen_ids:
    insert_to_database(item)
    seen_ids.add(item.id)
```

### 4. LLM Sentiment Analysis

```python
# For top 5 news items per cycle:
result = await llm_client.analyze_sentiment(
    headline=item.headline,
    content=item.content,
    ...
)
# Returns: sentiment scores, impact, confidence, topics
```

### 5. Database Storage

```sql
-- News items
INSERT INTO fxai.news_items (id, ts, source, headline, content, url, ...)

-- Sentiment scores
INSERT INTO fxai.sentiment_scores (news_id, sentiment_usd, impact_score, ...)
```

---

## 💰 Cost Analysis

### Scenario 1: RSS Only (Free)

- **Sources**: 5 RSS feeds
- **News/day**: ~200 items
- **Relevant**: ~50 items (after filtering)
- **Cost**: $0

### Scenario 2: RSS + LLM Sentiment

- **Sources**: 5 RSS feeds
- **News/day**: ~50 relevant items
- **LLM analyzed**: 5 items/minute × 60 min × 24 hr = 7,200/day
- **Actual**: 50 items/day (batch size limit)
- **Cost**: 50 × $0.025 = **$1.25/day** = **$37.50/month**

### Scenario 3: RSS + NewsAPI + LLM

- **Sources**: 5 RSS + NewsAPI
- **News/day**: ~150 relevant items
- **LLM analyzed**: 150 items/day
- **LLM cost**: 150 × $0.025 = **$3.75/day**
- **NewsAPI cost**: **$449/month**
- **Total**: **$562/month**

**Recommendation**: Start with RSS + LLM ($37.50/month)

---

## 🎯 Optimization Tips

### 1. Reduce LLM Costs

```bash
# Analyze fewer items per cycle
NEWS_SENTIMENT_BATCH_SIZE=3

# Increase poll interval
NEWS_POLL_INTERVAL_SEC=120

# Use cheaper model
LLM_MODEL=gpt-3.5-turbo  # 10x cheaper
```

### 2. Improve Relevance Filtering

Add custom keywords in `apps/news/sources.py`:

```python
def is_relevant(self, item: NewsItem) -> bool:
    # Add your custom keywords
    keywords = [..., "your_keyword", ...]
    ...
```

### 3. Add Custom RSS Feeds

Edit `apps/news/sources.py`:

```python
DEFAULT_RSS_FEEDS = {
    ...
    "your_source": "https://example.com/rss",
}
```

---

## 🐛 Troubleshooting

### Issue: No news fetched

**Check**:
```bash
# Test RSS feed manually
curl -s "https://www.forexlive.com/feed/news" | head -20
```

**Solution**: RSS feed may be down or changed URL.

### Issue: All news filtered out

**Check relevance filter**:
```python
python scripts/test_news_ingestion.py
```

**Solution**: Adjust keywords in `is_relevant()` method.

### Issue: LLM sentiment fails

**Check API key**:
```bash
echo $OPENAI_API_KEY
```

**Solution**: Set valid API key in `.env`.

### Issue: High LLM costs

**Check usage**:
```bash
make llm-costs
```

**Solution**:
- Reduce `NEWS_SENTIMENT_BATCH_SIZE`
- Increase `NEWS_POLL_INTERVAL_SEC`
- Use `gpt-3.5-turbo` instead of `gpt-4-turbo`

---

## 📚 Advanced Usage

### Custom News Source

Create a custom source class:

```python
from apps.news.sources import NewsSource, NewsItem

class MyCustomSource(NewsSource):
    async def fetch_latest(self, lookback_hours: int) -> List[NewsItem]:
        # Your custom fetching logic
        items = []
        # ... fetch from your API ...
        return items
```

Add to ingester:

```python
from apps.workers.news_ingester import NewsIngester

sources = [MyCustomSource("my_source")]
ingester = NewsIngester(sources=sources)
```

### Webhook Integration

Receive news via webhook instead of polling:

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook/news")
async def receive_news(request: Request):
    data = await request.json()
    item = NewsItem.create(
        headline=data["title"],
        content=data["content"],
        url=data["url"],
        source="webhook"
    )
    # Store in database
    ...
```

---

## 🔗 Related Documentation

- [Hybrid Quick Start](./HYBRID_QUICKSTART.md)
- [LLM Integration Design](./LLM_Integration_Design.md)
- [Main README](../README.md)

---

**Questions?** Check the main documentation or create an issue.
