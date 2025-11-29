# 📰 News Sources - Complete List

## ✅ Added 18 RSS News Sources!

### **Major News Agencies** (2)
- ✅ **Reuters Business** - Global business news
- ✅ **Bloomberg Markets** - Financial markets

### **FX-Specific Sources** (3)
- ✅ **ForexLive** - Real-time FX news
- ✅ **FXStreet** - FX analysis and news
- ✅ **DailyFX** - FX market news (NEW!)

### **Market News** (4)
- ✅ **Investing.com Forex** - FX-specific news
- ✅ **Investing.com Economy** - Economic news (NEW!)
- ✅ **MarketWatch Economy** - Economic updates
- ✅ **MarketWatch Markets** - Market top stories (NEW!)

### **Business News** (3)
- ✅ **CNBC World** - Global business (NEW!)
- ✅ **CNBC Forex** - FX-specific (NEW!)
- ✅ **Financial Times Markets** - Premium finance news (NEW!)

### **India-Specific** (3)
- ✅ **Economic Times** - Top Indian business news (NEW!)
- ✅ **Moneycontrol** - Indian markets (NEW!)
- ✅ **Business Standard** - Indian business (NEW!)

### **Central Banks & Policy** (2)
- ✅ **Federal Reserve News** - Fed press releases (NEW!)
- ✅ **ECB Press** - European Central Bank (NEW!)

### **Central Bank Scrapers** (4)
- ✅ **Federal Reserve** - Fed website scraper
- ✅ **Reserve Bank of India** - RBI website scraper
- ✅ **European Central Bank** - ECB website scraper
- ✅ **Bank of Japan** - BOJ website scraper

---

## 📊 Total Coverage

**RSS Feeds**: 18 sources  
**Central Bank Scrapers**: 4 sources  
**Total**: 22 news sources!

---

## 🎯 Coverage by Region

### **Global** (8 sources)
- Reuters, Bloomberg, FT, Investing.com, MarketWatch, DailyFX

### **United States** (4 sources)
- CNBC, Fed News, Fed Scraper

### **India** (5 sources)
- Economic Times, Moneycontrol, Business Standard, RBI Scraper

### **Europe** (3 sources)
- ECB Press, ECB Scraper, FT

### **Asia-Pacific** (2 sources)
- BOJ Scraper

### **FX-Specific** (5 sources)
- ForexLive, FXStreet, DailyFX, CNBC Forex, Investing Forex

---

## 🚀 How to Use

### **Start News Ingester**

```bash
make news-ingester
```

This will:
- Fetch from all 18 RSS feeds
- Scrape 4 central bank websites
- Analyze sentiment with Ollama
- Store in ClickHouse
- Update every 60 seconds

### **View News in Dashboard**

Open: **http://localhost:3001**

You'll see:
- Trending news sorted by impact
- Source icons (📰 💼 💱 etc.)
- Sentiment badges (BULLISH/BEARISH/NEUTRAL)
- USD/INR sentiment scores
- Refresh button

---

## 📈 Expected News Volume

### **High Volume** (>10 items/hour)
- Reuters
- Bloomberg
- CNBC
- Economic Times
- Moneycontrol

### **Medium Volume** (5-10 items/hour)
- ForexLive
- FXStreet
- Investing.com
- MarketWatch

### **Low Volume** (1-5 items/hour)
- DailyFX
- Financial Times
- Central Bank feeds
- Business Standard

### **Event-Driven** (sporadic)
- Fed News (during FOMC meetings)
- ECB Press (during policy meetings)
- Central bank scrapers

---

## 🎨 Source Icons in Dashboard

- 📰 Reuters
- 💼 Bloomberg
- 💱 ForexLive
- 📊 FXStreet
- 🏛️ RBI
- 🏦 Fed
- 🇪🇺 ECB
- 🇯🇵 BOJ
- 📈 Economic Times
- 💹 Moneycontrol
- 📉 CNBC
- 📄 Others

---

## 🔧 Configuration

### **Enable/Disable Sources**

Edit `apps/news/sources.py`:

```python
DEFAULT_RSS_FEEDS = {
    "reuters_business": "URL",  # Comment out to disable
    # "bloomberg_markets": "URL",  # Disabled
}
```

### **Add Custom Source**

```python
DEFAULT_RSS_FEEDS = {
    "my_custom_feed": "https://example.com/rss",
}
```

### **Adjust Polling Interval**

```bash
# Default: 60 seconds
make news-ingester

# Custom interval (e.g., 30 seconds)
.venv/bin/python -m apps.workers.news_ingester --poll-interval 30
```

---

## 📊 News Quality

### **High Quality** (Verified, Reliable)
- ✅ Reuters
- ✅ Bloomberg
- ✅ Financial Times
- ✅ Central Bank feeds

### **Good Quality** (Reliable, Some Noise)
- ✅ CNBC
- ✅ MarketWatch
- ✅ Economic Times
- ✅ Moneycontrol

### **Mixed Quality** (Useful but Noisy)
- ⚠️ ForexLive (fast but sometimes speculative)
- ⚠️ FXStreet (good analysis, some marketing)
- ⚠️ Investing.com (high volume, mixed quality)

---

## 🎯 Recommended Setup

### **For Retail Traders**
Enable:
- ForexLive (fast updates)
- FXStreet (analysis)
- Economic Times (India focus)
- CNBC (global markets)

### **For Hedge Funds**
Enable:
- Reuters (verified news)
- Bloomberg (premium)
- Central bank feeds (policy)
- Financial Times (in-depth)

### **For India-Focused Trading**
Enable:
- Economic Times
- Moneycontrol
- Business Standard
- RBI scraper
- RBI feeds

---

## 🚀 Next Steps

1. **Start the ingester**: `make news-ingester`
2. **Open dashboard**: http://localhost:3001
3. **Watch news flow in**: Check right sidebar
4. **Monitor sentiment**: See BULLISH/BEARISH badges
5. **Test hybrid predictions**: Should show news impact

---

## 📝 Notes

- **RSS feeds are free** - No API keys needed
- **Central bank scrapers** - May break if websites change
- **Sentiment analysis** - Uses Ollama (FREE!)
- **Storage** - All news stored in ClickHouse
- **Deduplication** - Automatic based on URL+timestamp

---

**Enjoy your comprehensive news coverage!** 📰🚀
