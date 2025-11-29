# News Sources - Quick Reference

## 📊 Available Sources (20+)

### Free Sources (No API Key) ✅

| Source | Type | Update Freq | Quality | Setup |
|--------|------|-------------|---------|-------|
| **ForexLive** | RSS | Real-time | ⭐⭐⭐⭐ | Auto |
| **FXStreet** | RSS | 15 min | ⭐⭐⭐⭐ | Auto |
| **Investing.com** | RSS | 30 min | ⭐⭐⭐ | Auto |
| **Reuters** | RSS | 1 hour | ⭐⭐⭐⭐⭐ | Auto |
| **MarketWatch** | RSS | 1 hour | ⭐⭐⭐ | Auto |
| **Federal Reserve** | Web Scrape | Real-time | ⭐⭐⭐⭐⭐ | Auto |
| **RBI** | Web Scrape | Real-time | ⭐⭐⭐⭐⭐ | Auto |
| **ECB** | RSS | Real-time | ⭐⭐⭐⭐⭐ | Auto |
| **BOJ** | Web Scrape | Real-time | ⭐⭐⭐⭐⭐ | Auto |
| **Finnhub** (free) | API | Real-time | ⭐⭐⭐ | API Key |

**Total Free**: 10 sources, $0/month

### Paid Sources (API Key Required) 💰

| Source | Cost/Month | Update Freq | Quality | Features |
|--------|------------|-------------|---------|----------|
| **Twitter** | $0-5,000 | Real-time | ⭐⭐⭐⭐⭐ | Central banks, news |
| **NewsAPI** | $449 | Real-time | ⭐⭐⭐⭐ | 150K+ sources |
| **Alpha Vantage** | $50 | Real-time | ⭐⭐⭐ | News + data |
| **Trading Economics** | $50-500 | Real-time | ⭐⭐⭐⭐⭐ | Economic calendar |
| **Finnhub** (paid) | $20-60 | Real-time | ⭐⭐⭐⭐ | Forex news |

---

## 🚀 Quick Setup

### Option 1: Free (Recommended for MVP)

```bash
# .env
ENABLE_CENTRAL_BANKS=true
ENABLE_TWITTER=false
ENABLE_ADVANCED_APIS=false

# Run
make news-ingester
```

**Result**: 10 sources, $0/month

### Option 2: Twitter Only

```bash
# .env
TWITTER_BEARER_TOKEN=your-token
ENABLE_CENTRAL_BANKS=true
ENABLE_TWITTER=true

# Run
make news-ingester
```

**Result**: 15 sources, $100/month

### Option 3: Full Coverage

```bash
# .env
TWITTER_BEARER_TOKEN=your-token
TRADING_ECONOMICS_KEY=your-key
FINNHUB_KEY=your-key
ENABLE_CENTRAL_BANKS=true
ENABLE_TWITTER=true
ENABLE_ADVANCED_APIS=true

# Run
make news-ingester
```

**Result**: 20+ sources, $150-200/month

---

## 📈 Expected News Volume

| Setup | News/Day | Relevant/Day | LLM Cost/Month |
|-------|----------|--------------|----------------|
| **Free** | 50 | 10 | $7.50 |
| **+ Twitter** | 200 | 40 | $30 |
| **+ All APIs** | 500 | 100 | $75 |

*With caching enabled, costs reduced by ~50%*

---

## 🎯 Recommended Configurations

### For Backtesting & Research
```bash
ENABLE_CENTRAL_BANKS=true
# Free sources only
```

### For Live Trading (Retail)
```bash
ENABLE_CENTRAL_BANKS=true
TWITTER_BEARER_TOKEN=your-token
ENABLE_TWITTER=true
# Central banks + Twitter
```

### For Algorithmic Trading (Professional)
```bash
# Enable everything
ENABLE_CENTRAL_BANKS=true
ENABLE_TWITTER=true
ENABLE_ADVANCED_APIS=true
# All sources for maximum edge
```

---

## 🔗 Full Documentation

- [Advanced News Sources Guide](./ADVANCED_NEWS_SOURCES.md)
- [News Ingestion Guide](./NEWS_INGESTION_GUIDE.md)
- [Hybrid System Complete](./HYBRID_SYSTEM_COMPLETE.md)
