// components/RoutePanel.jsx
// The visible "Google Maps" layer: pick a real start and destination place
// in Kolkata, see the route drawn on a real map, then press "Start journey"
// to watch an arrow actually travel from the start pin to the end pin --
// the journey timer runs only for that trip and stops the moment the arrow
// reaches the destination. Live jam/pothole reports (auto or manual) show
// on the same map and get avoided by the route the same way either way.

import { useEffect, useState, useCallback } from 'react'
import { api } from '../api'
import MapView from './MapView'

export default function RoutePanel() {
  const [locations, setLocations] = useState(null)
  const [roads, setRoads] = useState(null)
  const [locError, setLocError] = useState(null)

  const [start, setStart] = useState('esplanade')
  const [destination, setDestination] = useState('em_bypass')
  const [route, setRoute] = useState(null)
  const [routeError, setRouteError] = useState(null)

  const [conditions, setConditions] = useState(null)
  const [conditionsError, setConditionsError] = useState(null)

  const [reportRoad, setReportRoad] = useState(null)
  const [reportType, setReportType] = useState('JAM')

  const [journeyTrigger, setJourneyTrigger] = useState(0)
  const [journeyStatus, setJourneyStatus] = useState('idle') // idle | running | arrived
  const [journeyProgress, setJourneyProgress] = useState(0)

  useEffect(() => {
    api.listLocations().then(setLocations).catch((e) => setLocError(e.message))
    api.listRoads().then((rs) => { setRoads(rs); if (rs.length) setReportRoad(rs[0].id) }).catch((e) => setLocError(e.message))
  }, [])

  const loadConditions = useCallback(() => {
    api.listRoadConditions().then(setConditions).catch((e) => setConditionsError(e.message))
  }, [])

  useEffect(() => {
    loadConditions()
    const interval = setInterval(loadConditions, 5000)
    return () => clearInterval(interval)
  }, [loadConditions])

  const findRoute = useCallback(() => {
    setRouteError(null)
    setJourneyStatus('idle')
    setJourneyProgress(0)
    api.getRoute(start, destination).then(setRoute).catch((e) => setRouteError(e.message))
  }, [start, destination])

  useEffect(() => { if (locations) findRoute() }, [locations]) // eslint-disable-line react-hooks/exhaustive-deps

  const submitReport = useCallback(() => {
    if (!reportRoad) return
    api.reportRoadCondition(reportRoad, reportType, 0.8, 'manual_report')
      .then(() => { loadConditions(); findRoute() })
      .catch((e) => setConditionsError(e.message))
  }, [reportRoad, reportType, loadConditions, findRoute])

  const clearOne = useCallback((id) => {
    api.clearRoadCondition(id).then(() => { loadConditions(); findRoute() }).catch(() => {})
  }, [loadConditions, findRoute])

  const startJourney = useCallback(() => {
    if (!route || route.path.length === 0) return
    setJourneyStatus('running')
    setJourneyProgress(0)
    setJourneyTrigger((t) => t + 1)
  }, [route])

  const roadLabel = (r) => `${r.from_name} \u2194 ${r.to_name}`

  return (
    <div className="block">
      <h2>Route &amp; live road conditions — Kolkata</h2>
      {locError && <div className="note" style={{ color: 'var(--danger)' }}>Backend unreachable: {locError}</div>}

      {locations && (
        <MapView
          locations={locations} route={route} conditions={conditions} roads={roads}
          journeyTrigger={journeyTrigger}
          onProgress={setJourneyProgress}
          onArrive={() => setJourneyStatus('arrived')}
        />
      )}

      <div className="route-row" style={{ marginTop: 10 }}>
        <select value={start} onChange={(e) => setStart(e.target.value)}>
          {locations?.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
        <span className="arrow">→</span>
        <select value={destination} onChange={(e) => setDestination(e.target.value)}>
          {locations?.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
        <button className="primary" onClick={findRoute}>Find route</button>
      </div>

      {routeError && <div className="note" style={{ color: 'var(--danger)' }}>{routeError}</div>}
      {route && route.path.length > 0 && (
        <div className="route-result">
          <div className="mono">{route.path_names.join(' → ')}</div>
          <div className="note">~{route.total_cost} km
            {route.avoided.length > 0 && <> · rerouted around {route.avoided.length} reported road(s)</>}
          </div>

          <div className="journey-row">
            <button className="primary" onClick={startJourney} disabled={journeyStatus === 'running'}>
              {journeyStatus === 'running' ? 'En route…' : 'Start journey'}
            </button>
            {journeyStatus === 'running' && (
              <span className="note">
                {route.path_names[0]} → {route.path_names[route.path_names.length - 1]} · {Math.round(journeyProgress * 100)}%
              </span>
            )}
            {journeyStatus === 'arrived' && <span className="chip chip-ok">Arrived — simulation ended</span>}
          </div>
          {journeyStatus === 'running' && (
            <div className="progress-track"><div className="progress-fill" style={{ width: `${journeyProgress * 100}%` }} /></div>
          )}
        </div>
      )}
      {route && route.path.length === 0 && <div className="note">No route found between those places.</div>}

      <h3 className="subhead">Active reports (jams / potholes / etc)</h3>
      {conditionsError && <div className="note" style={{ color: 'var(--danger)' }}>Backend unreachable: {conditionsError}</div>}
      {!conditionsError && conditions && conditions.length === 0 && (
        <div className="note">No active reports right now — checking automatically every few seconds.</div>
      )}
      {conditions && roads && conditions.map((c) => {
        const road = roads.find((r) => r.id === c.road_id)
        return (
          <div className="condition-row" key={c.id}>
            <span className="chip chip-bad">{c.condition_type}</span>
            <span className="mono">{road ? roadLabel(road) : c.road_id}</span>
            <span className="note">sev {c.severity.toFixed(2)} · {c.reported_by?.startsWith('auto:') ? 'auto-detected' : 'manual'}</span>
            <button className="clear-btn" onClick={() => clearOne(c.id)}>Clear</button>
          </div>
        )
      })}

      <h3 className="subhead">Report a condition manually</h3>
      <div className="route-row">
        <select value={reportRoad || ''} onChange={(e) => setReportRoad(e.target.value)}>
          {roads?.map((r) => <option key={r.id} value={r.id}>{roadLabel(r)}</option>)}
        </select>
        <select value={reportType} onChange={(e) => setReportType(e.target.value)}>
          {['JAM', 'POTHOLE', 'BUMPY_ROAD', 'ACCIDENT', 'CONSTRUCTION'].map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <button onClick={submitReport}>Report</button>
      </div>
    </div>
  )
}
