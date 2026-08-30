// components/MapView.jsx
// Real map (OpenStreetMap tiles via Leaflet, no API key needed) showing:
//  - every known location as a small dot
//  - a green "Start" pin and red "End" pin for the current route
//  - the route itself as a bold line, with numbered waypoint markers
//  - active jams/potholes/etc as warning markers on the real road segment
//  - a rotating arrow that actually travels start -> end over time when a
//    journey is started, so movement/direction is visible, not just a
//    static line. Stops exactly at the destination and reports back via
//    onArrive() -- "the simulation ends" when the end point is reached.
//
// Plain Leaflet (not react-leaflet) -- this component owns the map
// instance directly via a ref.

import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

function pinIcon(color, label) {
  return L.divIcon({
    className: 'map-pin',
    html: `<div class="map-pin-body" style="background:${color}">${label}</div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 26],
  })
}
function dotIcon(color) {
  return L.divIcon({
    className: 'map-dot',
    html: `<div class="map-dot-body" style="background:${color}"></div>`,
    iconSize: [10, 10],
    iconAnchor: [5, 5],
  })
}
function numberIcon(n) {
  return L.divIcon({
    className: 'map-num',
    html: `<div class="map-num-body">${n}</div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  })
}
function arrowIcon() {
  return L.divIcon({
    className: 'map-arrow',
    html: `<div class="map-arrow-body"><svg width="26" height="26" viewBox="0 0 24 24">
      <polygon points="12,2 20,22 12,17 4,22" fill="#2DD4BF" stroke="#06201C" stroke-width="1.2"/>
    </svg></div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  })
}

const KOLKATA_CENTER = [22.565, 88.39]
const JOURNEY_SPEED_KMH = 35 // nominal average urban speed used to animate the journey

function haversineMeters(a, b) {
  const R = 6371000
  const toRad = (d) => (d * Math.PI) / 180
  const dLat = toRad(b[0] - a[0]), dLng = toRad(b[1] - a[1])
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a[0])) * Math.cos(toRad(b[0])) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(s))
}
function bearingDeg(a, b) {
  const toRad = (d) => (d * Math.PI) / 180, toDeg = (r) => (r * 180) / Math.PI
  const y = Math.sin(toRad(b[1] - a[1])) * Math.cos(toRad(b[0]))
  const x = Math.cos(toRad(a[0])) * Math.sin(toRad(b[0])) -
            Math.sin(toRad(a[0])) * Math.cos(toRad(b[0])) * Math.cos(toRad(b[1] - a[1]))
  return (toDeg(Math.atan2(y, x)) + 360) % 360
}
function pointAtDistance(coords, targetMeters) {
  let acc = 0
  for (let i = 0; i < coords.length - 1; i++) {
    const segLen = haversineMeters(coords[i], coords[i + 1])
    if (acc + segLen >= targetMeters || i === coords.length - 2) {
      const frac = segLen === 0 ? 0 : Math.min(1, (targetMeters - acc) / segLen)
      const lat = coords[i][0] + (coords[i + 1][0] - coords[i][0]) * frac
      const lng = coords[i][1] + (coords[i + 1][1] - coords[i][1]) * frac
      return { pos: [lat, lng], bearing: bearingDeg(coords[i], coords[i + 1]) }
    }
    acc += segLen
  }
  return { pos: coords[coords.length - 1], bearing: 0 }
}

export default function MapView({ locations, route, conditions, roads, journeyTrigger, onProgress, onArrive }) {
  const mapRef = useRef(null)
  const containerRef = useRef(null)
  const layerRef = useRef(null)
  const journeyMarkerRef = useRef(null)
  const rafRef = useRef(null)

  useEffect(() => {
    if (mapRef.current) return
    mapRef.current = L.map(containerRef.current, { scrollWheelZoom: true }).setView(KOLKATA_CENTER, 12)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(mapRef.current)
    layerRef.current = L.layerGroup().addTo(mapRef.current)
    return () => { cancelAnimationFrame(rafRef.current); mapRef.current?.remove(); mapRef.current = null }
  }, [])

  // static layer: locations, conditions, route line, start/end/waypoint pins
  useEffect(() => {
    const map = mapRef.current
    const layer = layerRef.current
    if (!map || !layer || !locations) return
    layer.clearLayers()
    journeyMarkerRef.current = null

    const byId = Object.fromEntries(locations.map((l) => [l.id, l]))

    locations.forEach((loc) => {
      L.marker([loc.lat, loc.lng], { icon: dotIcon('#5b6472') })
        .bindTooltip(loc.name, { direction: 'top', opacity: 0.85 })
        .addTo(layer)
    })

    if (conditions && roads) {
      const roadById = Object.fromEntries(roads.map((r) => [r.id, r]))
      conditions.forEach((c) => {
        const road = roadById[c.road_id]
        if (!road) return
        const a = byId[road.from_id], b = byId[road.to_id]
        if (!a || !b) return
        L.marker([(a.lat + b.lat) / 2, (a.lng + b.lng) / 2], { icon: pinIcon('#EF4444', '!') })
          .bindTooltip(`${c.condition_type} — ${road.from_name} ↔ ${road.to_name}`, { direction: 'top' })
          .addTo(layer)
      })
    }

    if (route && route.path && route.path.length > 0) {
      const coords = route.path.map((id) => [byId[id].lat, byId[id].lng])
      L.polyline(coords, { color: '#2DD4BF', weight: 5, opacity: 0.9 }).addTo(layer)

      route.path.forEach((id, i) => {
        const loc = byId[id]
        if (i === 0) {
          L.marker([loc.lat, loc.lng], { icon: pinIcon('#22C55E', 'S') })
            .bindTooltip(`Start: ${loc.name}`).addTo(layer)
        } else if (i === route.path.length - 1) {
          L.marker([loc.lat, loc.lng], { icon: pinIcon('#EF4444', 'E') })
            .bindTooltip(`End: ${loc.name}`).addTo(layer)
        } else {
          L.marker([loc.lat, loc.lng], { icon: numberIcon(i) })
            .bindTooltip(loc.name).addTo(layer)
        }
      })

      journeyMarkerRef.current = L.marker(coords[0], { icon: arrowIcon(), zIndexOffset: 1000 }).addTo(layer)
      map.fitBounds(coords, { padding: [40, 40] })
    }
  }, [locations, route, conditions, roads])

  // journey animation: moves the arrow from start to end over a duration
  // based on route distance, stops exactly at the destination, then fires
  // onArrive() -- this IS "the simulation ends" moment.
  useEffect(() => {
    if (!journeyTrigger || !route || !route.path || route.path.length === 0 || !locations) return
    const byId = Object.fromEntries(locations.map((l) => [l.id, l]))
    const coords = route.path.map((id) => [byId[id].lat, byId[id].lng])
    const totalMeters = coords.reduce((sum, c, i) => i === 0 ? 0 : sum + haversineMeters(coords[i - 1], c), 0)
    const durationMs = Math.max(2000, (totalMeters / 1000 / JOURNEY_SPEED_KMH) * 3600 * 1000)

    const marker = journeyMarkerRef.current
    if (!marker) return
    marker.setLatLng(coords[0])

    cancelAnimationFrame(rafRef.current)
    const startTime = performance.now()

    function tick(now) {
      const elapsed = now - startTime
      const fraction = Math.min(1, elapsed / durationMs)
      const { pos, bearing } = pointAtDistance(coords, fraction * totalMeters)
      marker.setLatLng(pos)
      const el = marker.getElement()
      if (el) el.style.transform += ` rotate(${bearing}deg)`
      onProgress?.(fraction)

      if (fraction < 1) {
        rafRef.current = requestAnimationFrame(tick)
      } else {
        marker.setLatLng(coords[coords.length - 1])
        onArrive?.()
      }
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [journeyTrigger]) // eslint-disable-line react-hooks/exhaustive-deps

  return <div ref={containerRef} className="map-container" />
}
