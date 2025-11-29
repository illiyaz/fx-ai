import { useState, useEffect } from 'react'
import Header from './components/Header'
import PredictionCards from './components/PredictionCards'
import AccuracyChart from './components/AccuracyChart'
import NewsSidebar from './components/NewsSidebar'
import { fetchPrediction, fetchNews, fetchSentiment, fetchBars } from './api/client'

function App() {
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
      const predData = await fetchPrediction('USDINR', '4h', true)
      setPrediction(predData)
      
      // Fetch news
      const newsData = await fetchNews(10)
      setNews(newsData)
      
      // Fetch sentiment
      const sentimentData = await fetchSentiment(10)
      setSentiment(sentimentData)
      
      // Fetch bars for accuracy chart (fetch more for longer time ranges)
      const barsData = await fetchBars('USDINR', 500)
      setAccuracyData(barsData)
      
      setError(null)
    } catch (err) {
      console.error('Error fetching data:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Fetch data on mount and every 30 seconds
  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30s

    return () => clearInterval(interval)
  }, [])

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
