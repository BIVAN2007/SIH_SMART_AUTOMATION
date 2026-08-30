// components/SimulationCanvas.jsx
// Top-down canvas render of the live telemetry: agents, ego vehicle,
// planned path, static context. Same visual language as the earlier
// live_demo.html prototype, now driven by real backend telemetry instead
// of an in-browser simulation.

import { useEffect, useRef } from 'react'

const COLORS = {
  car: '#5B8CFF',
  auto_rickshaw: '#F97316',
  pedestrian: '#EF4444',
  two_wheeler: '#A855F7',
  pushcart: '#8B5E34',
  cattle: '#4ADE80',
}

// Scenario world bounds — kept in sync with backend scenarios.py.
// (Not sent over the wire per-tick to keep messages small; static per scenario.)
const BOUNDS = {
  village_road: [0, 120, -10, 10],
  urban_intersection: [-10, 60, -30, 30],
  highway_merge: [0, 200, -8, 8],
  market_area: [0, 80, -8, 8],
  cattle_crossing: [0, 100, -10, 10],
}

function worldToScreen([x, y], bounds, width, height) {
  const [x0, x1, y0, y1] = bounds
  const pad = 30
  const sx = pad + ((x - x0) / (x1 - x0)) * (width - 2 * pad)
  const sy = height / 2 - ((y - (y0 + y1) / 2) / (y1 - y0)) * (height - 2 * pad) * 0.9
  return [sx, sy]
}

export default function SimulationCanvas({ scenario, telemetry, history }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const { width, height } = canvas
    const bounds = BOUNDS[scenario] || [0, 100, -10, 10]

    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = '#1B2027'
    ctx.fillRect(0, 0, width, height)

    // center guide line
    ctx.strokeStyle = 'rgba(255,255,255,0.08)'
    ctx.setLineDash([4, 10])
    ctx.beginPath()
    const midY = (bounds[2] + bounds[3]) / 2
    const [gx0, gy0] = worldToScreen([bounds[0], midY], bounds, width, height)
    const [gx1, gy1] = worldToScreen([bounds[1], midY], bounds, width, height)
    ctx.moveTo(gx0, gy0)
    ctx.lineTo(gx1, gy1)
    ctx.stroke()
    ctx.setLineDash([])

    if (!telemetry) {
      ctx.fillStyle = '#69788A'
      ctx.font = '13px monospace'
      ctx.fillText('Waiting for connection…', width / 2 - 70, height / 2)
      return
    }

    // start / goal markers -- drawn every frame so they're always visible,
    // clearly labeled and different colors so it's obvious which is which
    if (telemetry.start_pos) {
      const [sx, sy] = worldToScreen(telemetry.start_pos, bounds, width, height)
      ctx.fillStyle = '#22C55E'
      ctx.beginPath()
      ctx.arc(sx, sy, 7, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = '#0B0E11'
      ctx.lineWidth = 1.5
      ctx.stroke()
      ctx.fillStyle = '#22C55E'
      ctx.font = 'bold 11px monospace'
      ctx.fillText('START', sx - 18, sy - 12)
    }
    if (telemetry.goal_pos) {
      const [gx, gy] = worldToScreen(telemetry.goal_pos, bounds, width, height)
      ctx.fillStyle = '#EF4444'
      ctx.beginPath()
      ctx.arc(gx, gy, 7, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = '#0B0E11'
      ctx.lineWidth = 1.5
      ctx.stroke()
      // small flag so it reads as a finish line, not just another dot
      ctx.strokeStyle = '#EF4444'
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.moveTo(gx, gy - 7)
      ctx.lineTo(gx, gy - 20)
      ctx.stroke()
      ctx.fillStyle = '#EF4444'
      ctx.font = 'bold 11px monospace'
      ctx.fillText('END', gx - 12, gy - 22)
    }

    // driven trail
    if (history.length > 1) {
      ctx.strokeStyle = 'rgba(45,212,191,0.35)'
      ctx.lineWidth = 2
      ctx.beginPath()
      history.forEach((p, i) => {
        const [sx, sy] = worldToScreen(p, bounds, width, height)
        i === 0 ? ctx.moveTo(sx, sy) : ctx.lineTo(sx, sy)
      })
      ctx.stroke()
    }

    // planned path
    if (telemetry.planned_path?.length) {
      ctx.strokeStyle = telemetry.path_risk > 0.75 ? '#EF4444' : '#2DD4BF'
      ctx.lineWidth = 2.5
      ctx.setLineDash([6, 5])
      ctx.beginPath()
      telemetry.planned_path.forEach((p, i) => {
        const [sx, sy] = worldToScreen(p, bounds, width, height)
        i === 0 ? ctx.moveTo(sx, sy) : ctx.lineTo(sx, sy)
      })
      ctx.stroke()
      ctx.setLineDash([])
    }

    // agents (ground truth)
    telemetry.agents?.forEach((a) => {
      const [sx, sy] = worldToScreen(a.pos, bounds, width, height)
      ctx.fillStyle = COLORS[a.type] || '#999'
      ctx.beginPath()
      ctx.arc(sx, sy, 6, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = '#0B0E11'
      ctx.lineWidth = 1.5
      ctx.stroke()
    })

    // tracked agents (fusion output) — thin ring overlay to visualize tracking confidence
    telemetry.tracks?.forEach((t) => {
      const [sx, sy] = worldToScreen(t.pos, bounds, width, height)
      ctx.strokeStyle = 'rgba(255,255,255,0.4)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.arc(sx, sy, 10, 0, Math.PI * 2)
      ctx.stroke()
    })

    // ego vehicle
    {
      const [sx, sy] = worldToScreen(telemetry.ego_pos, bounds, width, height)
      ctx.save()
      ctx.translate(sx, sy)
      ctx.rotate(-telemetry.ego_theta)
      ctx.fillStyle = '#2DD4BF'
      ctx.beginPath()
      ctx.moveTo(11, 0)
      ctx.lineTo(-8, -6)
      ctx.lineTo(-8, 6)
      ctx.closePath()
      ctx.fill()
      ctx.restore()
    }
  }, [scenario, telemetry, history])

  return <canvas ref={canvasRef} width={960} height={420} className="sim-canvas" />
}
