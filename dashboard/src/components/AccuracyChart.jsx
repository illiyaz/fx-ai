import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import { TrendingUp, Target } from 'lucide-react'
import { format } from 'date-fns'

export default function AccuracyChart({ data, prediction }) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <div className="flex items-center space-x-2 mb-4">
          <Target className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Prediction Accuracy</h3>
        </div>
        <div className="text-center py-12 text-slate-400">
          <p>Loading price data...</p>
        </div>
      </div>
    )
  }

  // Transform data for the chart
  const chartData = data.map((bar, index) => {
    const timestamp = new Date(bar.ts || bar.timestamp)
    
    // Calculate predicted price based on current price + expected delta
    // This is a simplified version - in production you'd have actual predictions stored
    const currentPrice = bar.close
    const predictedPrice = prediction && index === data.length - 1
      ? currentPrice + (prediction.expected_delta_bps / 10000) * currentPrice
      : null

    return {
      time: format(timestamp, 'HH:mm'),
      fullTime: format(timestamp, 'MMM dd, HH:mm'),
      actual: currentPrice,
      predicted: predictedPrice,
      high: bar.high,
      low: bar.low
    }
  })

  // Calculate accuracy metrics
  const latestPrice = chartData[chartData.length - 1]?.actual || 0
  const predictedPrice = chartData[chartData.length - 1]?.predicted || latestPrice
  const priceDiff = predictedPrice - latestPrice
  const priceDiffPct = (priceDiff / latestPrice) * 100

  return (
    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Target className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Live vs Predicted Rates</h3>
        </div>
        
        {/* Accuracy Metrics */}
        <div className="flex items-center space-x-6">
          <div className="text-right">
            <p className="text-xs text-slate-400">Current Rate</p>
            <p className="text-lg font-bold text-white">{latestPrice.toFixed(4)}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-400">Predicted (4h)</p>
            <p className="text-lg font-bold text-blue-400">{predictedPrice.toFixed(4)}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-400">Difference</p>
            <p className={`text-lg font-bold ${priceDiff > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {priceDiff > 0 ? '+' : ''}{priceDiffPct.toFixed(3)}%
            </p>
          </div>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis 
            dataKey="time" 
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
          />
          <YAxis 
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
            domain={['auto', 'auto']}
            tickFormatter={(value) => value.toFixed(2)}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#1e293b', 
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#f1f5f9'
            }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(value) => value?.toFixed(4)}
          />
          <Legend 
            wrapperStyle={{ color: '#94a3b8' }}
          />
          
          {/* Actual Price Line */}
          <Line 
            type="monotone" 
            dataKey="actual" 
            stroke="#3b82f6" 
            strokeWidth={2}
            dot={{ fill: '#3b82f6', r: 3 }}
            name="Live Rate"
          />
          
          {/* High/Low Range */}
          <Line 
            type="monotone" 
            dataKey="high" 
            stroke="#10b981" 
            strokeWidth={1}
            strokeDasharray="3 3"
            dot={false}
            name="High"
          />
          <Line 
            type="monotone" 
            dataKey="low" 
            stroke="#ef4444" 
            strokeWidth={1}
            strokeDasharray="3 3"
            dot={false}
            name="Low"
          />
          
          {/* Predicted Price Point */}
          {prediction && (
            <Line 
              type="monotone" 
              dataKey="predicted" 
              stroke="#a855f7" 
              strokeWidth={3}
              dot={{ fill: '#a855f7', r: 6 }}
              name="Predicted (4h)"
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {/* Prediction Info */}
      {prediction && (
        <div className="mt-4 p-4 bg-slate-700/50 rounded-lg">
          <div className="flex items-start space-x-3">
            <TrendingUp className="w-5 h-5 text-purple-400 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-white mb-1">4-Hour Forecast</p>
              <p className="text-sm text-slate-300">{prediction.action_hint}</p>
              <div className="mt-2 flex items-center space-x-4 text-xs text-slate-400">
                <span>Confidence: {(prediction.confidence * 100).toFixed(0)}%</span>
                <span>•</span>
                <span>Model: {prediction.model_id?.split('_')[0]?.toUpperCase()}</span>
                {prediction.hybrid?.enabled && (
                  <>
                    <span>•</span>
                    <span className="text-purple-400">Hybrid Active</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
