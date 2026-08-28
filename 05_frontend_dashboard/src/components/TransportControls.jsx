// components/TransportControls.jsx
// Scenario picker + connect/disconnect controls for the live WebSocket run.

const SCENARIOS = [
  { value: 'village_road', label: '1 · Unmarked village road' },
  { value: 'urban_intersection', label: '2 · Unsignaled urban intersection' },
  { value: 'highway_merge', label: '3 · Highway merge (slow mergers)' },
  { value: 'market_area', label: '4 · Dense market, mixed traffic' },
  { value: 'cattle_crossing', label: '5 · Sudden cattle crossing' },
]

export default function TransportControls({
  scenario, setScenario, status, onStart, onStop, done,
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

      <div className="spacer" />
      <span className={`conn-pill conn-${status}`}>{status}</span>
    </div>
  )
}
