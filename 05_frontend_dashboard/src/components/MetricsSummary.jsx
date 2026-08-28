// components/MetricsSummary.jsx
// Pulls aggregate completion/collision rate per scenario from the backend's
// database via GET /api/metrics/summary. This is the "report table" view --
// distinct from MetricsPanel, which shows the live single-run telemetry.

import { useEffect, useState, useCallback } from 'react'
import { api } from '../api'

export default function MetricsSummary({ refreshKey }) {
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    api.metricsSummary().then(setSummary).catch((e) => setError(e.message))
  }, [])

  useEffect(() => { load() }, [load, refreshKey])

  return (
    <div className="block">
      <h2>Run history (database)</h2>
      {error && <div className="note" style={{ color: 'var(--danger)' }}>Backend unreachable: {error}</div>}
      {!error && !summary && <div className="note">Loading…</div>}
      {summary && summary.scenarios.length === 0 && (
        <div className="note">No runs recorded yet — start a live run or POST /api/runs.</div>
      )}
      {summary && summary.scenarios.map((s) => (
        <div className="summary-row" key={s.scenario}>
          <div className="summary-name mono">{s.scenario}</div>
          <div className="summary-bars">
            <span className="chip chip-ok">{s.completion_rate_pct}% complete</span>
            <span className={`chip ${s.collision_rate_pct > 0 ? 'chip-bad' : 'chip-ok'}`}>
              {s.collision_rate_pct}% collision
            </span>
            <span className="chip">{s.total_runs} runs</span>
          </div>
        </div>
      ))}
      <button className="refresh-btn" onClick={load}>Refresh</button>
    </div>
  )
}
