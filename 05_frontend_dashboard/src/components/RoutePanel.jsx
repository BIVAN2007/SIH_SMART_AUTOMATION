// components/RoutePanel.jsx
// The visible "Google Maps" layer: pick a start and destination road,
// get the best route back from GET /api/navigation/route -- automatically
// routed around anything reported via POST /api/road-conditions (jams,
// potholes, accidents). Also shows the live list of active conditions and
// lets you report one yourself, so V2V avoidance is something you can
// actually see happen, not just an API that exists.

import { useEffect, useState, useCallback } from 'react'
import { api } from '../api'

// Mirrors the road ids defined in driving_stack/road_network.py.
// If you rename roads there, update this list to match.
const ROADS = ['Road_A', 'Road_B', 'Road_C', 'Road_D', 'Road_E', 'Road_F', 'Road_G']
const CONDITIONS = ['JAM', 'POTHOLE', 'BUMPY_ROAD', 'ACCIDENT', 'CONSTRUCTION']

export default function RoutePanel() {
  const [start, setStart] = useState('Road_A')
  const [destination, setDestination] = useState('Road_G')
  const [route, setRoute] = useState(null)
  const [routeError, setRouteError] = useState(null)

  const [conditions, setConditions] = useState(null)
  const [conditionsError, setConditionsError] = useState(null)

  const [reportRoad, setReportRoad] = useState('Road_B')
  const [reportType, setReportType] = useState('JAM')

  const loadConditions = useCallback(() => {
    api.listRoadConditions().then(setConditions).catch((e) => setConditionsError(e.message))
  }, [])

  useEffect(() => { loadConditions() }, [loadConditions])

  const findRoute = useCallback(() => {
    setRouteError(null)
    api.getRoute(start, destination).then(setRoute).catch((e) => setRouteError(e.message))
  }, [start, destination])

  const submitReport = useCallback(() => {
    api.reportRoadCondition(reportRoad, reportType, 0.8, 'manual_report')
      .then(() => { loadConditions(); findRoute() })
      .catch((e) => setConditionsError(e.message))
  }, [reportRoad, reportType, loadConditions, findRoute])

  const clearOne = useCallback((id) => {
    api.clearRoadCondition(id).then(() => { loadConditions(); findRoute() }).catch(() => {})
  }, [loadConditions, findRoute])

  return (
    <div className="block">
      <h2>Route &amp; live road conditions</h2>

      <div className="route-row">
        <select value={start} onChange={(e) => setStart(e.target.value)}>
          {ROADS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <span className="arrow">→</span>
        <select value={destination} onChange={(e) => setDestination(e.target.value)}>
          {ROADS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <button className="primary" onClick={findRoute}>Find route</button>
      </div>

      {routeError && <div className="note" style={{ color: 'var(--danger)' }}>{routeError}</div>}
      {route && route.path.length > 0 && (
        <div className="route-result">
          <div className="mono">{route.path.join(' → ')}</div>
          <div className="note">cost {route.total_cost}
            {route.avoided.length > 0 && <> · avoided: {route.avoided.join(', ')}</>}
          </div>
        </div>
      )}
      {route && route.path.length === 0 && <div className="note">No route found between those roads.</div>}

      <h3 className="subhead">Active reports</h3>
      {conditionsError && <div className="note" style={{ color: 'var(--danger)' }}>Backend unreachable: {conditionsError}</div>}
      {!conditionsError && conditions && conditions.length === 0 && (
        <div className="note">No active jams, potholes, or other reports right now.</div>
      )}
      {conditions && conditions.map((c) => (
        <div className="condition-row" key={c.id}>
          <span className="chip chip-bad">{c.condition_type}</span>
          <span className="mono">{c.road_id}</span>
          <span className="note">sev {c.severity.toFixed(2)} · via {c.reported_by || 'auto'}</span>
          <button className="clear-btn" onClick={() => clearOne(c.id)}>Clear</button>
        </div>
      ))}

      <h3 className="subhead">Report a condition</h3>
      <div className="route-row">
        <select value={reportRoad} onChange={(e) => setReportRoad(e.target.value)}>
          {ROADS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <select value={reportType} onChange={(e) => setReportType(e.target.value)}>
          {CONDITIONS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <button onClick={submitReport}>Report</button>
      </div>
    </div>
  )
}
