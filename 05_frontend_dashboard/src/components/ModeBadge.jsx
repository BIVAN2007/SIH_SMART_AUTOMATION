// components/ModeBadge.jsx
// Displays the current behavioral decision state (LaneFollow/Yield/etc)
// with color coding matching severity.

const MODE_COLOR = {
  LaneFollow: 'var(--accent)',
  UnmarkedRoadFollow: 'var(--accent)',
  Crawl: 'var(--warn)',
  Yield: 'var(--warn)',
  EmergencyStop: 'var(--danger)',
}

export default function ModeBadge({ telemetry }) {
  const mode = telemetry?.mode || 'LaneFollow'
  const note = telemetry?.mode_note || 'Awaiting live data…'
  const color = MODE_COLOR[mode] || 'var(--accent)'

  return (
    <div className="block">
      <h2>Decision state</h2>
      <div className="modebadge">
        <span className="dot" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
        <span>{mode}</span>
      </div>
      <div className="note">{note}</div>
      {telemetry?.collision && (
        <div className="note" style={{ color: 'var(--danger)', marginTop: 6, fontWeight: 600 }}>
          ⚠ Collision threshold breached this run
        </div>
      )}
    </div>
  )
}
