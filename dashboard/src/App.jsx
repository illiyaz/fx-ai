import { useState, useEffect } from 'react'
import Header from './components/Header'
import PredictionCards from './components/PredictionCards'
import AccuracyChart from './components/AccuracyChart'
import NewsSidebar from './components/NewsSidebar'
import { fetchPrediction, fetchNews, fetchSentiment, fetchBars } from './api/client'

const CURRENCY_PAIRS = [
  { value: 'USDINR', label: 'USD/INR', flag: '🇮🇳' },
  { value: 'EURUSD', label: 'EUR/USD', flag: '🇪🇺' },
  { value: 'GBPUSD', label: 'GBP/USD', flag: '🇬🇧' },
  { value: 'USDJPY', label: 'USD/JPY', flag: '🇯🇵' },
  { value: 'AUDUSD', label: 'AUD/USD', flag: '🇦🇺' },
  { value: 'USDCAD', label: 'USD/CAD', flag: '🇨🇦' },
  { value: 'USDCHF', label: 'USD/CHF', flag: '🇨🇭' },
  { value: 'NZDUSD', label: 'NZD/USD', flag: '🇳🇿' },
]

function App() {
  const [selectedPair, setSelectedPair] = useState('USDINR')
  const [prediction, setPrediction] = useState(null)
  const [news, setNews] = useState([])
  const [sentiment, setSentiment] = useState([])
  const [accuracyData, setAccuracyData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Fetch data function
  const fetchData = async () => {
    try {
      setLoading(true)
      
      // Fetch prediction (hybrid)
      const predData = await fetchPrediction(selectedPair, '4h', true)
      setPrediction(predData)
      
      // Fetch news
      const newsData = await fetchNews(10)
      setNews(newsData)
      
      // Fetch sentiment
      const sentimentData = await fetchSentiment(10)
      setSentiment(sentimentData)
      
      // Fetch bars for accuracy chart (fetch more for longer time ranges)
      const barsData = await fetchBars(selectedPair, 500)
      setAccuracyData(barsData)
      
      setError(null)
    } catch (err) {
      console.error('Error fetching data:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Fetch data on mount and every 30 seconds, or when pair changes
  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30s

    return () => clearInterval(interval)
  }, [selectedPair])

  if (loading && !prediction) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (error && !prediction) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">Error: {error}</p>
          <p className="text-slate-400 text-sm">Make sure the API server is running on port 9090</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <Header prediction={prediction} />
      
      {/* Currency Pair Selector */}
      <div className="px-6 pt-4 pb-2">
        <div className="flex items-center space-x-3">
          <label className="text-sm font-medium text-slate-400">Currency Pair:</label>
          <div className="relative">
            <select
              value={selectedPair}
              onChange={(e) => setSelectedPair(e.target.value)}
              className="appearance-none bg-slate-800 text-white px-4 py-2 pr-10 rounded-lg border border-slate-700 hover:border-slate-600 focus:outline-none focus:border-blue-500 transition-colors cursor-pointer font-medium"
            >
              {CURRENCY_PAIRS.map((pair) => (
                <option key={pair.value} value={pair.value}>
                  {pair.flag} {pair.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
          {loading && (
            <div className="flex items-center space-x-2 text-slate-400 text-sm">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
              <span>Loading...</span>
            </div>
          )}
        </div>
      </div>
      
      <div className="flex">
        {/* Main Content - Left Side */}
        <div className="flex-1 p-6">
          {/* Prediction Cards */}
          <PredictionCards prediction={prediction} />
          
          {/* Accuracy Chart - Your Key Feature! */}
          <div className="mt-6">
            <AccuracyChart 
              data={accuracyData} 
              prediction={prediction}
            />
          </div>
        </div>
        
        {/* News Sidebar - Right Side */}
        <NewsSidebar 
          news={news} 
          sentiment={sentiment}
          onRefresh={fetchData}
        />
      </div>
    </div>
  )
}

export default App
