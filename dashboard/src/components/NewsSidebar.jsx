import { Newspaper, TrendingUp, AlertCircle, ExternalLink } from 'lucide-react'
import { format, formatDistanceToNow } from 'date-fns'

export default function NewsSidebar({ news, sentiment }) {
  // Merge news with sentiment scores
  const newsWithSentiment = news.map(item => {
    const sentimentScore = sentiment.find(s => s.news_id === item.id)
    return { ...item, sentiment: sentimentScore }
  })

  // Sort by impact score (if available) or recency
  const trendingNews = newsWithSentiment
    .sort((a, b) => {
      const impactA = a.sentiment?.impact_score || 0
      const impactB = b.sentiment?.impact_score || 0
      return impactB - impactA
    })
    .slice(0, 10)

  const getSentimentColor = (score) => {
    if (!score) return 'text-slate-400'
    if (score > 0.3) return 'text-green-400'
    if (score < -0.3) return 'text-red-400'
    return 'text-yellow-400'
  }

  const getSentimentBadge = (score) => {
    if (!score) return { text: 'NEUTRAL', color: 'bg-slate-600' }
    if (score > 0.3) return { text: 'BULLISH', color: 'bg-green-600' }
    if (score < -0.3) return { text: 'BEARISH', color: 'bg-red-600' }
    return { text: 'NEUTRAL', color: 'bg-yellow-600' }
  }

  const getImpactIcon = (score) => {
    if (!score || score < 0.5) return null
    if (score >= 0.8) return <AlertCircle className="w-4 h-4 text-red-400" />
    if (score >= 0.6) return <TrendingUp className="w-4 h-4 text-yellow-400" />
    return null
  }

  return (
    <div className="w-96 bg-slate-800 border-l border-slate-700 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 73px)' }}>
      {/* Header */}
      <div className="sticky top-0 bg-slate-800 border-b border-slate-700 p-4 z-10">
        <div className="flex items-center space-x-2">
          <Newspaper className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-semibold text-white">Trending News</h2>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Top {trendingNews.length} news by impact
        </p>
      </div>

      {/* News List */}
      <div className="p-4 space-y-4">
        {trendingNews.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            <Newspaper className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No recent news available</p>
            <p className="text-xs mt-1">Start the news ingester to see updates</p>
          </div>
        ) : (
          trendingNews.map((item, index) => {
            const sentimentBadge = getSentimentBadge(item.sentiment?.sentiment_overall)
            const timestamp = new Date(item.ts || item.timestamp)
            
            return (
              <div 
                key={item.id || index} 
                className="bg-slate-700/50 rounded-lg p-4 hover:bg-slate-700 transition-colors border border-slate-600/50"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold text-blue-400 uppercase">
                      {item.source}
                    </span>
                    {item.sentiment?.impact_score && (
                      <div className="flex items-center">
                        {getImpactIcon(item.sentiment.impact_score)}
                      </div>
                    )}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded ${sentimentBadge.color} text-white`}>
                    {sentimentBadge.text}
                  </span>
                </div>

                {/* Headline */}
                <h3 className="text-sm font-semibold text-white mb-2 line-clamp-2">
                  {item.headline}
                </h3>

                {/* Content Preview */}
                {item.content && (
                  <p className="text-xs text-slate-300 mb-3 line-clamp-2">
                    {item.content}
                  </p>
                )}

                {/* Sentiment Scores */}
                {item.sentiment && (
                  <div className="mb-3 p-2 bg-slate-800/50 rounded">
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-400">USD: </span>
                        <span className={getSentimentColor(item.sentiment.sentiment_usd)}>
                          {item.sentiment.sentiment_usd?.toFixed(2) || 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400">INR: </span>
                        <span className={getSentimentColor(item.sentiment.sentiment_inr)}>
                          {item.sentiment.sentiment_inr?.toFixed(2) || 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400">Impact: </span>
                        <span className="text-white">
                          {item.sentiment.impact_score?.toFixed(1) || 'N/A'}/10
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400">Confidence: </span>
                        <span className="text-white">
                          {((item.sentiment.confidence || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Footer */}
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>
                    {formatDistanceToNow(timestamp, { addSuffix: true })}
                  </span>
                  {item.url && (
                    <a 
                      href={item.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="flex items-center space-x-1 hover:text-blue-400 transition-colors"
                    >
                      <span>Read</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
