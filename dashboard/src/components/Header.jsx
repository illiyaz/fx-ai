import { Activity, TrendingUp } from 'lucide-react'

export default function Header({ prediction }) {
  const isHybridEnabled = prediction?.hybrid?.enabled || false
  
  return (
    <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-blue-500 p-2 rounded-lg">
            <TrendingUp className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">FX-AI Dashboard</h1>
            <p className="text-sm text-slate-400">Hybrid ML+LLM Prediction System</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* System Status */}
          <div className="flex items-center space-x-2 bg-slate-700 px-4 py-2 rounded-lg">
            <Activity className="w-4 h-4 text-green-400" />
            <span className="text-sm text-slate-300">API Online</span>
          </div>
          
          {/* Hybrid Status */}
          <div className={`flex items-center space-x-2 px-4 py-2 rounded-lg ${
            isHybridEnabled ? 'bg-green-900/30 border border-green-500/30' : 'bg-yellow-900/30 border border-yellow-500/30'
          }`}>
            <div className={`w-2 h-2 rounded-full ${isHybridEnabled ? 'bg-green-400' : 'bg-yellow-400'}`}></div>
            <span className="text-sm text-slate-300">
              {isHybridEnabled ? 'Hybrid Active' : 'ML Only'}
            </span>
          </div>
        </div>
      </div>
    </header>
  )
}
