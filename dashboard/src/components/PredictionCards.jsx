import { ArrowUp, ArrowDown, Minus, Brain, Sparkles } from 'lucide-react'

export default function PredictionCards({ prediction }) {
  if (!prediction) return null

  const mlProb = prediction.hybrid?.prob_up_ml || prediction.prob_up
  const hybridProb = prediction.hybrid?.prob_up_hybrid || prediction.prob_up
  const direction = prediction.direction
  const recommendation = prediction.recommendation
  const isHybridEnabled = prediction.hybrid?.enabled || false

  const getDirectionIcon = (dir) => {
    if (dir === 'UP') return <ArrowUp className="w-5 h-5" />
    if (dir === 'DOWN') return <ArrowDown className="w-5 h-5" />
    return <Minus className="w-5 h-5" />
  }

  const getDirectionColor = (dir) => {
    if (dir === 'UP') return 'text-green-400'
    if (dir === 'DOWN') return 'text-red-400'
    return 'text-yellow-400'
  }

  const getRecommendationColor = (rec) => {
    if (rec === 'NOW') return 'bg-green-500'
    if (rec === 'WAIT') return 'bg-yellow-500'
    return 'bg-slate-500'
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* ML-Only Prediction */}
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Brain className="w-5 h-5 text-blue-400" />
            <h3 className="text-lg font-semibold text-white">ML Prediction</h3>
          </div>
          <span className="text-xs text-slate-400">LightGBM</span>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Probability Up</span>
            <span className="text-2xl font-bold text-white">
              {(mlProb * 100).toFixed(4)}%
            </span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Direction</span>
            <div className={`flex items-center space-x-2 ${getDirectionColor(direction)}`}>
              {getDirectionIcon(direction)}
              <span className="font-semibold">{direction}</span>
            </div>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Expected Δ</span>
            <span className="text-white font-mono">
              {prediction.expected_delta_bps?.toFixed(2)} bps
            </span>
          </div>
        </div>
      </div>

      {/* Hybrid Prediction */}
      <div className={`rounded-xl p-6 border ${
        isHybridEnabled 
          ? 'bg-gradient-to-br from-blue-900/30 to-purple-900/30 border-blue-500/30' 
          : 'bg-slate-800 border-slate-700'
      }`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Sparkles className={`w-5 h-5 ${isHybridEnabled ? 'text-purple-400' : 'text-slate-400'}`} />
            <h3 className="text-lg font-semibold text-white">Hybrid Prediction</h3>
          </div>
          {isHybridEnabled && (
            <span className="text-xs px-2 py-1 bg-purple-500/20 text-purple-300 rounded">
              ML + News
            </span>
          )}
        </div>
        
        {isHybridEnabled ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Probability Up</span>
              <span className="text-2xl font-bold text-white">
                {(hybridProb * 100).toFixed(4)}%
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Fusion Weights</span>
              <span className="text-white font-mono text-sm">
                ML {(prediction.hybrid.fusion_weights.ml * 100).toFixed(0)}% | 
                News {(prediction.hybrid.fusion_weights.llm * 100).toFixed(0)}%
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-slate-400">News Sentiment</span>
              <span className={`font-semibold ${
                prediction.hybrid.news_sentiment > 0 ? 'text-green-400' : 
                prediction.hybrid.news_sentiment < 0 ? 'text-red-400' : 'text-yellow-400'
              }`}>
                {prediction.hybrid.news_sentiment?.toFixed(3)}
              </span>
            </div>
            
            <div className="pt-4 border-t border-slate-700">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Recommendation</span>
                <span className={`px-3 py-1 rounded-full text-white font-semibold ${getRecommendationColor(recommendation)}`}>
                  {recommendation}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-slate-400">
            <p className="mb-2">Hybrid mode disabled</p>
            <p className="text-sm">No recent news available</p>
          </div>
        )}
      </div>
    </div>
  )
}
