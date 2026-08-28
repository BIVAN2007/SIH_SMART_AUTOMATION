// api.js
// Thin fetch wrapper around the Layer 2 FastAPI REST endpoints.

import { API_BASE } from './config'

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`API ${res.status} on ${path}: ${text}`)
  }
  return res.json()
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
}
