# 🎨 FX-AI Dashboard - Quick Start Guide

## What We Built

A beautiful, real-time dashboard with **3 key features**:

### 1. 📊 Live vs Predicted Rates Chart
Shows your actual FX rates alongside 4-hour predictions to visualize accuracy in real-time.

### 2. 🎯 ML vs Hybrid Comparison
Side-by-side cards showing:
- ML-only prediction (LightGBM)
- Hybrid prediction (ML + News sentiment)
- Fusion weights and confidence

### 3. 📰 Trending News Sidebar
Right-hand panel with:
- Top news by impact score
- Sentiment analysis (Bullish/Bearish/Neutral)
- USD/INR sentiment breakdown
- Real-time updates

---

## 🚀 How to Run

### Step 1: Install Dashboard Dependencies

```bash
make dashboard-install
```

This will install React, TailwindCSS, Recharts, and other dependencies.

### Step 2: Ensure API is Running

The dashboard needs your API server on port 9090:

```bash
# Terminal 1
make api
```

### Step 3: Start the Dashboard

```bash
# Terminal 2
make dashboard-dev
```

### Step 4: Open in Browser

Navigate to: **http://localhost:3000**

---

## 📸 What You'll See

```
┌─────────────────────────────────────────────────────────────────┐
│  FX-AI Dashboard                          [API Online] [Hybrid] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ ML Prediction    │  │ Hybrid Prediction│  │ Trending News│ │
│  │                  │  │                  │  │              │ │
│  │ ↑ 0.0049%       │  │ ↑ 0.0047%       │  │ 📰 Fed cuts  │ │
│  │ Direction: DOWN  │  │ ML 72% News 28% │  │    [-0.6] 🔴│ │
│  │ Δ: 1.11 bps     │  │ Sentiment: -0.15│  │              │ │
│  │                  │  │ ⭐ NOW          │  │ 📰 RBI hold  │ │
│  └──────────────────┘  └──────────────────┘  │    [0.0] ⚪ │ │
│                                               │              │ │
│  ┌────────────────────────────────────────┐  │ 📰 USD up    │ │
│  │ Live vs Predicted Rates                │  │    [+0.7] 🟢│ │
│  │                                        │  │              │ │
│  │  Current: 84.2345  Predicted: 84.2456 │  │ 📰 INR high  │ │
│  │  Difference: +0.013%                   │  │    [+0.5] 🟢│ │
│  │                                        │  │              │ │
│  │  [Chart showing price line + prediction]│  │ 📰 Trade ok  │ │
│  │                                        │  │    [+0.4] 🟢│ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │  │              │ │
│  │                                        │  └──────────────┘ │
│  │  4h Forecast: USD likely to strengthen │                   │
│  │  Confidence: 20% | Model: LGBM        │                   │
│  └────────────────────────────────────────┘                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Features Breakdown

### Header
- **System Status**: Green = API online
- **Hybrid Status**: Shows if news fusion is active

### Prediction Cards (Left)
- **ML Card**: Pure machine learning prediction
- **Hybrid Card**: ML + News sentiment fusion
  - Shows fusion weights (e.g., ML 72%, News 28%)
  - Displays news sentiment score
  - Recommendation badge (NOW/WAIT)

### Accuracy Chart (Center)
- **Blue Line**: Actual live rates
- **Purple Dot**: Predicted rate (4 hours ahead)
- **Green/Red Dashed**: High/Low range
- **Metrics**: Current vs Predicted difference

### News Sidebar (Right)
- **Sorted by Impact**: Most important news first
- **Sentiment Badges**: Bullish 🟢 / Bearish 🔴 / Neutral ⚪
- **Detailed Scores**: USD sentiment, INR sentiment, impact, confidence
- **Timestamps**: How long ago the news was published

---

## 🔧 Configuration

### Change Refresh Rate

Edit `dashboard/src/App.jsx`:

```javascript
const interval = setInterval(fetchData, 30000)  // 30 seconds (default)
```

Change to:
```javascript
const interval = setInterval(fetchData, 10000)  // 10 seconds (faster)
```

### Change API Key

Edit `dashboard/src/api/client.js`:

```javascript
const API_KEY = 'changeme-dev-key'  // Your API key
```

### Change API URL

Edit `dashboard/vite.config.js`:

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:9090',  // Your API URL
  }
}
```

---

## 🐛 Troubleshooting

### Dashboard shows "Loading..."
**Problem**: Can't connect to API

**Solutions**:
1. Ensure API is running: `make api`
2. Check API is on port 9090: `curl http://localhost:9090/health`
3. Verify API key matches in `dashboard/src/api/client.js`

### No News Showing
**Problem**: News sidebar is empty

**Solutions**:
1. Start news ingester: `make news-ingester`
2. Insert sample news: `./scripts/quick_test_hybrid.sh`
3. Check data: `make tail-news`

### Chart Not Showing
**Problem**: Accuracy chart is blank

**Solutions**:
1. Check price data exists: `make tail-bars`
2. Verify API endpoint: 
   ```bash
   curl -H "X-API-Key: changeme-dev-key" \
     http://localhost:9090/v1/bars/recent?pair=USDINR
   ```

### Hybrid Not Enabled
**Problem**: Hybrid card shows "disabled"

**Solutions**:
1. Restart API server (to pick up .env changes)
2. Ensure `LLM_PROVIDER=ollama` in `.env`
3. Check sentiment data: `make tail-sentiment`
4. Run: `./scripts/quick_test_hybrid.sh`

---

## 📦 Build for Production

### Build Static Files

```bash
make dashboard-build
```

Output: `dashboard/dist/`

### Preview Production Build

```bash
make dashboard-preview
```

### Deploy

The `dist/` folder contains static files you can deploy to:
- **Netlify**: Drag & drop `dist/` folder
- **Vercel**: Connect GitHub repo
- **AWS S3**: Upload to S3 bucket
- **Nginx**: Copy to `/var/www/html`

---

## 🎨 Customization Ideas

### 1. Add More Currency Pairs

Add a dropdown to switch between pairs:
- USDINR
- EURUSD
- GBPUSD
- USDJPY

### 2. Add Time Range Selector

Let users choose:
- Last 1 hour
- Last 4 hours
- Last 24 hours
- Last 7 days

### 3. Add More Charts

- Sentiment timeline
- Prediction accuracy over time
- Model performance comparison
- Volume analysis

### 4. Add Notifications

- Browser notifications for high-impact news
- Alert when prediction confidence > 80%
- Warning when API goes offline

### 5. Add Export Features

- Download predictions as CSV
- Export charts as PNG
- Generate PDF reports

---

## 🚀 Next Steps

1. **Install & Run**
   ```bash
   make dashboard-install
   make dashboard-dev
   ```

2. **Open Browser**
   - Navigate to http://localhost:3000
   - Explore the features

3. **Customize**
   - Adjust refresh rate
   - Add your branding
   - Tweak colors in `tailwind.config.js`

4. **Deploy**
   - Build: `make dashboard-build`
   - Deploy `dist/` folder to your hosting

---

## 📚 Technical Details

### Stack
- **React 18**: UI framework
- **Vite**: Fast build tool
- **TailwindCSS**: Utility-first CSS
- **Recharts**: Chart library
- **Lucide**: Icon library
- **date-fns**: Date formatting

### API Endpoints Used
- `GET /v1/forecast` - Predictions
- `GET /v1/news/recent` - News items
- `GET /v1/sentiment/recent` - Sentiment scores
- `GET /v1/bars/recent` - Price bars
- `GET /health` - Health check

### Performance
- **Initial Load**: ~2-3 seconds
- **Auto-refresh**: Every 30 seconds
- **API Calls**: 4 endpoints per refresh
- **Bundle Size**: ~500KB (gzipped)

---

## ✅ Success Checklist

- [ ] Dashboard installed (`make dashboard-install`)
- [ ] API server running (`make api`)
- [ ] Dashboard running (`make dashboard-dev`)
- [ ] Browser open at http://localhost:3000
- [ ] Prediction cards showing data
- [ ] Chart displaying price history
- [ ] News sidebar populated (if news ingester running)
- [ ] Hybrid mode enabled (if sentiment data available)

---

**Enjoy your beautiful FX-AI Dashboard!** 🎉
