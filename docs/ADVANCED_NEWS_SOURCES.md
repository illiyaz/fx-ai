# Advanced News Sources Guide

## 📰 Overview

The FX-AI Advisor now supports advanced news sources including:
- **Twitter/X** - Real-time tweets from central banks and financial news
- **Central Bank Websites** - Official press releases (Fed, RBI, ECB, BOJ)
- **Trading Economics** - Economic calendar and data releases
- **Finnhub** - Forex-specific news aggregation

---

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
make deps
# Or manually:
pip install beautifulsoup4>=4.12 lxml>=5.0 tweepy>=4.14
```

### Step 2: Configure API Keys

Edit `.env`:

```bash
# Advanced News Sources
TWITTER_BEARER_TOKEN=your-twitter-bearer-token
TRADING_ECONOMICS_KEY=your-trading-economics-key
FINNHUB_KEY=your-finnhub-key

# Source Toggles
ENABLE_CENTRAL_BANKS=true    # Free, no API key needed
ENABLE_TWITTER=true           # Requires Twitter API
ENABLE_ADVANCED_APIS=true     # Requires paid APIs
```

### Step 3: Run News Ingester

```bash
make news-ingester
```

---

## 📡 News Sources

### 1. Twitter/X Integration

**What it does**: Monitors tweets from central banks and financial news accounts

**Accounts Monitored**:

**Central Banks**:
- `@federalreserve` - US Federal Reserve
- `@RBI` - Reserve Bank of India
- `@ecb` - European Central Bank
- `@bankofengland` - Bank of England
- `@bankofcanada` - Bank of Canada
- `@RBA_Media` - Reserve Bank of Australia

**Financial News**:
- `@Reuters`, `@Bloomberg`, `@WSJ`, `@FT`
- `@CNBC`, `@ForexLive`, `@FXStreetNews`

**Setup**:

1. **Get Twitter API Access**:
   - Go to https://developer.twitter.com/
   - Create a new app
   - Get Bearer Token from "Keys and tokens" tab

2. **Configure**:
   ```bash
   TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAABearerTokenHere
   ENABLE_TWITTER=true
   ```

3. **Cost**: 
   - Free tier: 1,500 tweets/month
   - Basic: $100/month for 10,000 tweets/month
   - Pro: $5,000/month for 1M tweets/month

**Example Tweet**:
```
@federalreserve: The Federal Reserve raised the target range for 
the federal funds rate to 5.25-5.50 percent. Read more: https://...
```

---

### 2. Federal Reserve (Fed)

**What it does**: Scrapes official press releases from federalreserve.gov

**Source**: https://www.federalreserve.gov/newsevents/pressreleases.htm

**Setup**: No API key needed (web scraping)

**Update Frequency**: Real-time (checks every poll interval)

**Example Headlines**:
- "Federal Reserve issues FOMC statement"
- "Federal Reserve Board announces approval of application by..."
- "Chair Powell's testimony before the Senate Banking Committee"

**Cost**: Free

---

### 3. Reserve Bank of India (RBI)

**What it does**: Scrapes official press releases from rbi.org.in

**Source**: https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx

**Setup**: No API key needed (web scraping)

**Update Frequency**: Real-time

**Example Headlines**:
- "RBI keeps repo rate unchanged at 6.50%"
- "Monetary Policy Statement, 2025-26"
- "Statement on Developmental and Regulatory Policies"

**Cost**: Free

---

### 4. European Central Bank (ECB)

**What it does**: Fetches press releases via ECB's RSS feed

**Source**: https://www.ecb.europa.eu/rss/press.html

**Setup**: No API key needed (RSS feed)

**Update Frequency**: Real-time

**Example Headlines**:
- "Monetary policy decisions"
- "ECB staff macroeconomic projections for the euro area"
- "Christine Lagarde, President of the ECB, speech at..."

**Cost**: Free

---

### 5. Bank of Japan (BOJ)

**What it does**: Scrapes announcements from boj.or.jp

**Source**: https://www.boj.or.jp/en/announcements/index.htm

**Setup**: No API key needed (web scraping)

**Update Frequency**: Real-time

**Example Headlines**:
- "Statement on Monetary Policy"
- "Summary of Opinions at the Monetary Policy Meeting"
- "Governor Ueda's Press Conference"

**Cost**: Free

---

### 6. Trading Economics

**What it does**: Fetches economic calendar events and data releases

**Source**: Trading Economics API

**Setup**:

1. **Get API Key**:
   - Go to https://tradingeconomics.com/api
   - Sign up for an account
   - Get API key from dashboard

2. **Configure**:
   ```bash
   TRADING_ECONOMICS_KEY=your-api-key-here
   ENABLE_ADVANCED_APIS=true
   ```

3. **Pricing**:
   - Free trial: 100 requests
   - Starter: $50/month (1,000 requests)
   - Professional: $500/month (10,000 requests)

**Data Provided**:
- Economic calendar events
- Actual vs Forecast vs Previous values
- Importance ratings
- Country-specific indicators

**Example Event**:
```json
{
  "Country": "United States",
  "Event": "Non Farm Payrolls",
  "Actual": "263K",
  "Forecast": "200K",
  "Previous": "261K",
  "Importance": "High"
}
```

**Cost**: $50-500/month

---

### 7. Finnhub

**What it does**: Aggregates forex-specific news from multiple sources

**Source**: Finnhub API

**Setup**:

1. **Get API Key**:
   - Go to https://finnhub.io/
   - Sign up for free account
   - Get API key from dashboard

2. **Configure**:
   ```bash
   FINNHUB_KEY=your-api-key-here
   ENABLE_ADVANCED_APIS=true
   ```

3. **Pricing**:
   - Free: 60 API calls/minute
   - Starter: $19.99/month (300 calls/min)
   - Professional: $59.99/month (600 calls/min)

**Features**:
- Real-time forex news
- News from 100+ sources
- Sentiment analysis (basic)
- Category filtering

**Example News**:
```json
{
  "category": "forex",
  "headline": "Dollar Strengthens on Fed Hawkish Comments",
  "source": "Reuters",
  "summary": "The U.S. dollar rose against major currencies...",
  "url": "https://..."
}
```

**Cost**: Free tier available, $20-60/month for higher limits

---

## 💰 Cost Comparison

| Source | Cost | API Key Required | Update Frequency | Quality |
|--------|------|------------------|------------------|---------|
| **RSS Feeds** | Free | No | Every 15-60 min | Good |
| **Fed Website** | Free | No | Real-time | Excellent |
| **RBI Website** | Free | No | Real-time | Excellent |
| **ECB RSS** | Free | No | Real-time | Excellent |
| **BOJ Website** | Free | No | Real-time | Excellent |
| **Twitter** | $0-5,000/mo | Yes | Real-time | Excellent |
| **Trading Economics** | $50-500/mo | Yes | Real-time | Excellent |
| **Finnhub** | $0-60/mo | Yes | Real-time | Good |

### Recommended Setup

**Budget: $0/month (Free)**
- ✅ RSS feeds (5 sources)
- ✅ Central bank websites (4 sources)
- ✅ Finnhub free tier
- **Total**: 10+ sources, 0 cost

**Budget: $100/month (Basic)**
- ✅ All free sources
- ✅ Twitter Basic ($100/mo)
- **Total**: 15+ sources, real-time tweets

**Budget: $200/month (Professional)**
- ✅ All free sources
- ✅ Twitter Basic ($100/mo)
- ✅ Trading Economics Starter ($50/mo)
- ✅ Finnhub Starter ($20/mo)
- **Total**: 20+ sources, comprehensive coverage

---

## 🔧 Configuration Examples

### Minimal (Free)

```bash
# .env
ENABLE_CENTRAL_BANKS=true
ENABLE_TWITTER=false
ENABLE_ADVANCED_APIS=false
```

**Sources**: RSS feeds + central banks = ~10 sources

### Standard (Twitter Only)

```bash
# .env
TWITTER_BEARER_TOKEN=your-token
ENABLE_CENTRAL_BANKS=true
ENABLE_TWITTER=true
ENABLE_ADVANCED_APIS=false
```

**Sources**: RSS + central banks + Twitter = ~15 sources

### Premium (All Sources)

```bash
# .env
TWITTER_BEARER_TOKEN=your-token
TRADING_ECONOMICS_KEY=your-key
FINNHUB_KEY=your-key
ENABLE_CENTRAL_BANKS=true
ENABLE_TWITTER=true
ENABLE_ADVANCED_APIS=true
```

**Sources**: All available = ~20+ sources

---

## 📊 Monitoring

### Check News Sources

```bash
# Count news by source
make count-news
```

Output:
```
source                  count
federal_reserve         12
rbi                     8
ecb                     15
twitter_federalreserve  45
forexlive              32
reuters_business        28
finnhub_reuters        18
```

### View Recent News

```bash
make tail-news
```

Output:
```
2025-11-28 14:30:00  federal_reserve  Federal Reserve issues FOMC statement
2025-11-28 14:25:00  twitter_RBI      RBI: Monetary policy remains accommodative
2025-11-28 14:20:00  ecb              ECB maintains key interest rates
```

---

## 🎯 Use Cases

### Use Case 1: Central Bank Monitoring

**Goal**: Track all major central bank announcements

**Configuration**:
```bash
ENABLE_CENTRAL_BANKS=true
ENABLE_TWITTER=true  # For real-time alerts
```

**Sources Used**:
- Fed, RBI, ECB, BOJ websites
- Twitter accounts of central banks

**Benefit**: Immediate awareness of policy changes

### Use Case 2: Economic Data Tracking

**Goal**: Monitor economic calendar events

**Configuration**:
```bash
TRADING_ECONOMICS_KEY=your-key
ENABLE_ADVANCED_APIS=true
```

**Sources Used**:
- Trading Economics calendar

**Benefit**: Anticipate market-moving data releases

### Use Case 3: Comprehensive Coverage

**Goal**: Maximum news coverage for algorithmic trading

**Configuration**:
```bash
# Enable everything
ENABLE_CENTRAL_BANKS=true
ENABLE_TWITTER=true
ENABLE_ADVANCED_APIS=true
```

**Sources Used**: All 20+ sources

**Benefit**: No missed opportunities, comprehensive edge

---

## 🐛 Troubleshooting

### Issue: Twitter API errors

**Error**: `401 Unauthorized`

**Solution**:
1. Check Bearer Token is correct
2. Verify app has read permissions
3. Check API usage limits

### Issue: Web scraping fails

**Error**: `Connection timeout` or `404 Not Found`

**Solution**:
1. Check internet connection
2. Verify website hasn't changed structure
3. Check if website is blocking scrapers (rare for official sites)

### Issue: No news from central banks

**Check**:
```bash
make tail-news | grep federal_reserve
```

**Solution**:
1. Central banks may not publish daily
2. Increase `NEWS_LOOKBACK_HOURS` to 24
3. Check if scraper needs updating (website structure changed)

### Issue: High API costs

**Check**:
```bash
# Count API calls
make count-news | grep -E "twitter|finnhub|trading_economics"
```

**Solution**:
1. Reduce `NEWS_POLL_INTERVAL_SEC` (poll less frequently)
2. Disable expensive sources
3. Use free tier alternatives

---

## 📈 Performance Impact

### News Volume

**Without Advanced Sources**:
- ~50 news items/day
- ~5 relevant items/day

**With Central Banks**:
- ~80 news items/day
- ~15 relevant items/day

**With Twitter**:
- ~200 news items/day
- ~40 relevant items/day

**With All Sources**:
- ~500 news items/day
- ~100 relevant items/day

### LLM Costs

**Sentiment Analysis** (5 items/cycle, 60 sec poll):
- Daily items analyzed: 5 × 1440 = 7,200 (theoretical)
- Actual (batch limited): ~100 items/day
- Cost: 100 × $0.025 = **$2.50/day** = **$75/month**

**With Caching** (5 min TTL):
- Effective items: ~50/day
- Cost: **$37.50/month**

---

## 🔗 API Documentation Links

- [Twitter API](https://developer.twitter.com/en/docs/twitter-api)
- [Trading Economics API](https://docs.tradingeconomics.com/)
- [Finnhub API](https://finnhub.io/docs/api)
- [Federal Reserve](https://www.federalreserve.gov/feeds.htm)
- [RBI](https://www.rbi.org.in/)
- [ECB](https://www.ecb.europa.eu/rss/)
- [BOJ](https://www.boj.or.jp/en/)

---

## 🎉 Summary

**Free Sources** (Recommended for MVP):
- ✅ 5 RSS feeds
- ✅ 4 central bank websites
- ✅ Finnhub free tier
- **Total**: 10+ sources, $0/month

**Premium Setup** (Recommended for Production):
- ✅ All free sources
- ✅ Twitter Basic ($100/mo)
- ✅ Trading Economics ($50/mo)
- **Total**: 20+ sources, $150/month

**Start with free sources, upgrade as needed!**

```bash
# Enable free sources
ENABLE_CENTRAL_BANKS=true
make news-ingester
```

---

**Questions?** Check the main documentation or create an issue on GitHub.
