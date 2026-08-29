// components/MapView.jsx
// A real map (OpenStreetMap tiles via Leaflet, no API key needed) showing:
//  - every known location as a small dot
//  - a green "Start" pin and red "End" pin for the current route
//  - the route itself as a bold line, with numbered waypoint markers so the
//    order (start -> ... -> end) is obvious
//  - active jams/potholes/etc as warning markers drawn on the midpoint of
//    the real road segment they were reported on
//
// Plain Leaflet (not react-leaflet) to keep the dependency footprint small
// -- this component owns the map instance directly via a ref.

import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Leaflet's default marker icons reference image files that don't resolve
// correctly under Vite's bundler -- build our own small colored pins with
// plain divIcon/SVG instead of fighting that.
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

const KOLKATA_CENTER = [22.565, 88.39]

export default function MapView({ locations, route, conditions, roads }) {
  const mapRef = useRef(null)
  const containerRef = useRef(null)
  const layerRef = useRef(null)

  useEffect(() => {
    if (mapRef.current) return
    mapRef.current = L.map(containerRef.current, { scrollWheelZoom: true }).setView(KOLKATA_CENTER, 12)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(mapRef.current)
    layerRef.current = L.layerGroup().addTo(mapRef.current)
    return () => { mapRef.current?.remove(); mapRef.current = null }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    const layer = layerRef.current
    if (!map || !layer || !locations) return
    layer.clearLayers()

    const byId = Object.fromEntries(locations.map((l) => [l.id, l]))

    // every known location, as a small dot with its name
    locations.forEach((loc) => {
      L.marker([loc.lat, loc.lng], { icon: dotIcon('#5b6472') })
        .bindTooltip(loc.name, { direction: 'top', opacity: 0.85 })
        .addTo(layer)
    })

    // active jam/pothole/etc markers, at the midpoint of the real road
    if (conditions && roads) {
      const roadById = Object.fromEntries(roads.map((r) => [r.id, r]))
      conditions.forEach((c) => {
        const road = roadById[c.road_id]
        if (!road) return
        const a = byId[road.from_id], b = byId[road.to_id]
        if (!a || !b) return
        const midLat = (a.lat + b.lat) / 2, midLng = (a.lng + b.lng) / 2
        L.marker([midLat, midLng], { icon: pinIcon('#EF4444', '!') })
          .bindTooltip(`${c.condition_type} — ${road.from_name} ↔ ${road.to_name}`, { direction: 'top' })
          .addTo(layer)
      })
    }

    // route: bold line + numbered waypoints + clear start/end pins
    if (route && route.path && route.path.length > 0) {
      const coords = route.path.map((id) => [byId[id].lat, byId[id].lng])
      L.polyline(coords, { color: '#2DD4BF', weight: 5, opacity: 0.9 }).addTo(layer)

      route.path.forEach((id, i) => {
        const loc = byId[id]
        if (i === 0) {
          L.marker([loc.lat, loc.lng], { icon: pinIcon('#22C55E', 'S') })
            .bindTooltip(`Start: ${loc.name}`, { permanent: false }).addTo(layer)
        } else if (i === route.path.length - 1) {
          L.marker([loc.lat, loc.lng], { icon: pinIcon('#EF4444', 'E') })
            .bindTooltip(`End: ${loc.name}`, { permanent: false }).addTo(layer)
        } else {
          L.marker([loc.lat, loc.lng], { icon: numberIcon(i) })
            .bindTooltip(loc.name, { permanent: false }).addTo(layer)
        }
      })

      map.fitBounds(coords, { padding: [40, 40] })
    }
  }, [locations, route, conditions, roads])

  return <div ref={containerRef} className="map-container" />
}
