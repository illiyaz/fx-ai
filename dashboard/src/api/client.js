const API_BASE = '/api'
const API_KEY = 'changeme-dev-key'

const headers = {
  'X-API-Key': API_KEY,
  'Content-Type': 'application/json'
}

export async function fetchPrediction(pair = 'USDINR', horizon = '4h', useHybrid = true) {
  const response = await fetch(
    `${API_BASE}/v1/forecast?pair=${pair}&h=${horizon}&use_hybrid=${useHybrid}`,
    { headers }
  )
  if (!response.ok) throw new Error('Failed to fetch prediction')
  return response.json()
}

export async function fetchNews(limit = 10) {
  try {
    const response = await fetch(`${API_BASE}/v1/news/recent?limit=${limit}`, { headers })
    if (!response.ok) {
      // If endpoint doesn't exist, return mock data
      return []
    }
    return response.json()
  } catch (error) {
    // Fallback: fetch from ClickHouse directly via a custom endpoint
    // For now, return empty array
    console.warn('News endpoint not available:', error)
    return []
  }
}

export async function fetchSentiment(limit = 10) {
  try {
    const response = await fetch(`${API_BASE}/v1/sentiment/recent?limit=${limit}`, { headers })
    if (!response.ok) {
      return []
    }
    return response.json()
  } catch (error) {
    console.warn('Sentiment endpoint not available:', error)
    return []
  }
}

export async function fetchBars(pair = 'USDINR', limit = 50) {
  try {
    const response = await fetch(`${API_BASE}/v1/bars/recent?pair=${pair}&limit=${limit}`, { headers })
    if (!response.ok) {
      return []
    }
    return response.json()
  } catch (error) {
    console.warn('Bars endpoint not available:', error)
    return []
  }
}

export async function fetchHealth() {
  const response = await fetch(`${API_BASE}/health`)
  if (!response.ok) throw new Error('API unhealthy')
  return response.json()
}
