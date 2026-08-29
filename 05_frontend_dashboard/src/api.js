// REST client for the FastAPI backend.
import { API_BASE } from './config'

async function request(path, options = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 15000)

  try {
    const headers = { Accept: 'application/json', ...(options.headers || {}) }
    if (options.body != null) headers['Content-Type'] = 'application/json'

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    })

    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(`API ${res.status} on ${path}${text ? `: ${text}` : ''}`)
    }

    return await res.json()
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error(`Request timed out: ${path}`)
    }
    if (err instanceof TypeError) {
      throw new Error(`Cannot reach backend at ${API_BASE}. Check VITE_API_BASE and backend deployment.`)
    }
    throw err
  } finally {
    clearTimeout(timeout)
  }
}

export const api = {
  listScenarios: () => request('/api/scenarios'),

  createRun: (scenario, seed) =>
    request('/api/runs', {
      method: 'POST',
      body: JSON.stringify({ scenario, seed: seed ?? null }),
    }),

  listRuns: (scenario, limit = 50) => {
    const params = new URLSearchParams()
    if (scenario) params.set('scenario', scenario)
    params.set('limit', String(limit))
    return request(`/api/runs?${params.toString()}`)
  },

  getRun: (id) => request(`/api/runs/${id}`),

  metricsSummary: () => request('/api/metrics/summary'),

  listLocations: () => request('/api/navigation/locations'),
  listRoads: () => request('/api/navigation/roads'),

  getRoute: (start, destination) => {
    const params = new URLSearchParams({ start, destination })
    return request(`/api/navigation/route?${params.toString()}`)
  },

  listRoadConditions: () => request('/api/road-conditions'),

  reportRoadCondition: (road_id, condition_type, severity, reported_by) =>
    request('/api/road-conditions', {
      method: 'POST',
      body: JSON.stringify({ road_id, condition_type, severity, reported_by }),
    }),

  clearRoadCondition: (id) => request(`/api/road-conditions/${id}`, { method: 'DELETE' }),
}
