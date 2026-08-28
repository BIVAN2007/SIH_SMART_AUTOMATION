// App.jsx
import { useState, useCallback } from 'react'
import { useSimulationSocket } from './hooks/useSimulationSocket'
import SimulationCanvas from './components/SimulationCanvas'
import MetricsPanel from './components/MetricsPanel'
import ModeBadge from './components/ModeBadge'
import TransportControls from './components/TransportControls'
import MetricsSummary from './components/MetricsSummary'

const TITLES = {
  village_road: 'Village Road (Unmarked)',
  urban_intersection: 'Unsignaled Urban Intersection',
  highway_merge: 'Highway Merge (Slow Mergers)',
  market_area: 'Dense Market Area (Mixed Traffic)',
  cattle_crossing: 'Sudden Cattle Crossing',
}

export default function App() {
  const [scenario, setScenario] = useState('village_road')
  const [refreshKey, setRefreshKey] = useState(0)
  const { telemetry, status, history, connect, disconnect } = useSimulationSocket()

  const handleStart = useCallback(() => {
    connect(scenario)
  }, [connect, scenario])

  const handleStop = useCallback(() => {
    disconnect()
  }, [disconnect])

  // when a run finishes, bump refreshKey so MetricsSummary re-pulls from the DB
  if (telemetry?.done && status === 'open') {
    setTimeout(() => setRefreshKey((k) => k + 1), 300)
  }

  return (
    <div className="wrap">
      <div className="stage">
        <div className="stagehead">
          <div className="eyebrow">Live telemetry — connected to FastAPI backend</div>
          <div className="title">{TITLES[scenario]}</div>
        </div>
        <div className="canvaswrap">
          <SimulationCanvas scenario={scenario} telemetry={telemetry} history={history} />
        </div>
        <TransportControls
          scenario={scenario}
          setScenario={setScenario}
          status={status}
          onStart={handleStart}
          onStop={handleStop}
          done={telemetry?.done}
        />
      </div>

      <div className="panel">
        <ModeBadge telemetry={telemetry} />
        <MetricsPanel telemetry={telemetry} />
        <MetricsSummary refreshKey={refreshKey} />

        <div className="block">
          <h2>Legend</h2>
          <div className="legend">
            <div className="legend-item"><span className="swatch" style={{ background: '#2DD4BF' }} />Ego vehicle</div>
            <div className="legend-item"><span className="swatch" style={{ background: '#F97316' }} />Auto-rickshaw</div>
            <div className="legend-item"><span className="swatch" style={{ background: '#EF4444' }} />Pedestrian</div>
            <div className="legend-item"><span className="swatch" style={{ background: '#A855F7' }} />Two-wheeler</div>
            <div className="legend-item"><span className="swatch" style={{ background: '#8B5E34' }} />Pushcart</div>
            <div className="legend-item"><span className="swatch" style={{ background: '#4ADE80' }} />Cattle</div>
          </div>
        </div>
      </div>
    </div>
  )
}
