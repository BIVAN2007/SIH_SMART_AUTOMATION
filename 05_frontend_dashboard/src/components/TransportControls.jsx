// Scenario picker + live simulation transport/speed controls.

const SCENARIOS = [
  { value: 'village_road', label: '1 · Unmarked village road' },
  { value: 'urban_intersection', label: '2 · Unsignaled urban intersection' },
  { value: 'highway_merge', label: '3 · Highway merge (slow mergers)' },
  { value: 'market_area', label: '4 · Dense market, mixed traffic' },
  { value: 'cattle_crossing', label: '5 · Sudden cattle crossing' },
]

const SPEEDS = [
  { value: 0.25, label: '0.25×' },
  { value: 0.5, label: '0.5×' },
  { value: 1, label: '1×' },
  { value: 2, label: '2×' },
  { value: 4, label: '4×' },
]

export default function TransportControls({
  scenario, setScenario, status, onStart, onStop, done, speed, onSpeedChange,
}) {
  const isLive = status === 'connecting' || status === 'open'

  return (
    <div className="transport">
      <select value={scenario} onChange={(e) => setScenario(e.target.value)} disabled={isLive}>
        {SCENARIOS.map((s) => (
          <option key={s.value} value={s.value}>{s.label}</option>
        ))}
      </select>

      {!isLive ? (
        <button className="primary" onClick={onStart}>
          {done ? 'Run again' : 'Start live run'}
        </button>
      ) : (
        <button onClick={onStop}>Stop</button>
      )}

      <div className="speed-control">
        <span className="speedlabel">SIM SPEED</span>
        <select value={speed} onChange={(e) => onSpeedChange(e.target.value)} aria-label="Simulation speed">
          {SPEEDS.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
      </div>

      <div className="spacer" />
      <span className={`conn-pill conn-${status}`}>{status}</span>
    </div>
  )
}
