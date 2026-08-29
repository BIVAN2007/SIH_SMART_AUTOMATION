// Manual mode: buttons that inject an agent into the live run right now,
// same as the scripted scenario agents -- the backend can't tell the
// difference. Only enabled while a run is live (WebSocket open).

const SPAWNABLE = [
  { type: 'pedestrian', label: 'Pedestrian crossing' },
  { type: 'cattle', label: 'Cattle crossing' },
  { type: 'auto_rickshaw', label: 'Auto-rickshaw' },
  { type: 'pushcart', label: 'Pushcart' },
  { type: 'two_wheeler', label: 'Two-wheeler' },
]

export default function ManualControls({ status, onSpawn }) {
  const isLive = status === 'open'

  return (
    <div className="block">
      <h2>Manual controls</h2>
      <p className="hint">Inject an agent into the live run — same physics and collision-avoidance as the scripted scenario.</p>
      <div className="manual-buttons">
        {SPAWNABLE.map((s) => (
          <button
            key={s.type}
            disabled={!isLive}
            onClick={() => onSpawn(s.type)}
            title={isLive ? `Spawn ${s.label}` : 'Start a live run first'}
          >
            {s.label}
          </button>
        ))}
      </div>
    </div>
  )
}
