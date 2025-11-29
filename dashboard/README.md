# FX-AI Dashboard

Beautiful, real-time dashboard for the FX-AI Hybrid Prediction System.

## Features

### 📊 Live vs Predicted Rates Chart
- Real-time price visualization
- 4-hour prediction overlay
- High/Low range indicators
- Accuracy metrics display

### 🎯 Prediction Cards
- **ML-Only Prediction**: LightGBM model output
- **Hybrid Prediction**: Bayesian fusion of ML + News sentiment
- Fusion weights visualization
- Recommendation badges (NOW/WAIT)

### 📰 Trending News Sidebar
- Top news by impact score
- Sentiment analysis (Bullish/Bearish/Neutral)
- USD/INR sentiment breakdown
- Impact and confidence metrics
- Real-time updates

### 🎨 Modern UI
- Dark mode design
- Responsive layout
- TailwindCSS styling
- Lucide icons
- Recharts visualizations

## Quick Start

### 1. Install Dependencies

```bash
make dashboard-install
```

Or manually:
```bash
cd dashboard
npm install
```

### 2. Start the API Server

The dashboard connects to your API on port 9090:

```bash
# In terminal 1
make api
```

### 3. Start the Dashboard

```bash
# In terminal 2
make dashboard-dev
```

Or manually:
```bash
cd dashboard
npm run dev
```

### 4. Open in Browser

Navigate to: **http://localhost:3000**

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Dashboard (React)                     │
│                   http://localhost:3000                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ API Proxy
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                         │
│                http://localhost:9090                     │
│                                                          │
│  Endpoints:                                              │
│  • /v1/forecast          - Predictions                   │
│  • /v1/news/recent       - News items                    │
│  • /v1/sentiment/recent  - Sentiment scores              │
│  • /v1/bars/recent       - Price bars                    │
│  • /health               - Health check                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   ClickHouse DB                          │
│                                                          │
│  Tables:                                                 │
│  • bars_1m           - Price data                        │
│  • features_1m       - Engineered features               │
│  • models            - Trained models                    │
│  • news_items        - News articles                     │
│  • sentiment_scores  - LLM sentiment analysis            │
│  • hybrid_predictions - Fused predictions                │
└─────────────────────────────────────────────────────────┘
```

## Components

### Header
- System status indicators
- Hybrid mode toggle
- API health check

### PredictionCards
- Side-by-side ML vs Hybrid comparison
- Probability gauges
- Fusion weights
- News sentiment summary

### AccuracyChart
- Line chart with Recharts
- Live rates (blue line)
- High/Low range (dashed)
- Predicted rate (purple dot)
- Accuracy metrics

### NewsSidebar
- Scrollable news feed
- Impact-based sorting
- Sentiment badges
- USD/INR sentiment scores
- Confidence indicators

## Configuration

### API Connection

Edit `dashboard/vite.config.js` to change the API URL:

```javascript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:9090',  // Change this
        changeOrigin: true,
      }
    }
  }
})
```

### API Key

Edit `dashboard/src/api/client.js`:

```javascript
const API_KEY = 'changeme-dev-key'  // Change this
```

### Refresh Interval

Edit `dashboard/src/App.jsx`:

```javascript
const interval = setInterval(fetchData, 30000)  // 30 seconds
```

## Build for Production

```bash
make dashboard-build
```

Or manually:
```bash
cd dashboard
npm run build
```

The built files will be in `dashboard/dist/`.

## Preview Production Build

```bash
make dashboard-preview
```

Or manually:
```bash
cd dashboard
npm run preview
```

## Troubleshooting

### Dashboard shows "Loading..."
- Ensure API server is running: `make api`
- Check API is on port 9090
- Verify API key is correct

### No news showing
- Start news ingester: `make news-ingester`
- Insert sample news: `./scripts/quick_test_hybrid.sh`
- Check ClickHouse has data: `make tail-news`

### Chart not showing
- Ensure price data exists: `make tail-bars`
- Check bars_1m table has recent data
- Verify API endpoint: `curl -H "X-API-Key: changeme-dev-key" http://localhost:9090/v1/bars/recent?pair=USDINR`

### Hybrid not enabled
- Restart API server to pick up .env changes
- Ensure `LLM_PROVIDER=ollama` in .env
- Check recent sentiment exists: `make tail-sentiment`

## Development

### Tech Stack
- **React 18** - UI framework
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Recharts** - Charts
- **Lucide React** - Icons
- **date-fns** - Date formatting

### File Structure
```
dashboard/
├── src/
│   ├── components/
│   │   ├── Header.jsx           # Top header
│   │   ├── PredictionCards.jsx  # ML vs Hybrid cards
│   │   ├── AccuracyChart.jsx    # Main chart
│   │   └── NewsSidebar.jsx      # News feed
│   ├── api/
│   │   └── client.js            # API client
│   ├── App.jsx                  # Main app
│   ├── main.jsx                 # Entry point
│   └── index.css                # Global styles
├── index.html
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## Next Steps

1. **Add More Charts**
   - Sentiment timeline
   - Prediction accuracy over time
   - Model performance comparison

2. **Add Filters**
   - Currency pair selector
   - Time range picker
   - News source filter

3. **Add Alerts**
   - High-impact news notifications
   - Prediction threshold alerts
   - System health warnings

4. **Add Export**
   - Download predictions as CSV
   - Export charts as images
   - Generate PDF reports

## License

Part of the FX-AI Advisor project.
