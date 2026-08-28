// components/MetricsPanel.jsx
// Live metrics readout, sourced directly from the latest telemetry tick.

export default function MetricsPanel({ telemetry }) {
  const rows = [
    ['Sim time', telemetry ? `${telemetry.t.toFixed(1)} s` : '—'],
    ['Ego speed', telemetry ? `${telemetry.ego_speed_kmh.toFixed(1)} km/h` : '—'],
    ['Min clearance', telemetry && telemetry.min_clearance_m >= 0 ? `${telemetry.min_clearance_m.toFixed(2)} m` : '—'],
    ['Replan latency', telemetry ? `${telemetry.replan_latency_ms.toFixed(1)} ms` : '—'],
    ['Active tracks', telemetry ? telemetry.tracks.length : '—'],
    ['Path risk', telemetry ? telemetry.path_risk.toFixed(2) : '—'],
  ]

  return (
    <div className="block">
      <h2>Live metrics</h2>
      {rows.map(([label, val]) => (
        <div className="metric-row" key={label}>
          <span className="metric-label">{label}</span>
          <span className="metric-val mono">{val}</span>
        </div>
      ))}
    </div>
  )
}
