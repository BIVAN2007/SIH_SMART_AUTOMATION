// WebSocket integration with the FastAPI live telemetry endpoint.
import { useEffect, useRef, useState, useCallback } from 'react'
import { WS_BASE } from '../config'

export function useSimulationSocket() {
  const [telemetry, setTelemetry] = useState(null)
  const [status, setStatus] = useState('idle')
  const [history, setHistory] = useState([])
  const wsRef = useRef(null)

  const connect = useCallback((scenario, seed, speed = 1) => {
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }

    setHistory([])
    setTelemetry(null)
    setStatus('connecting')

    const params = seed != null ? `?seed=${encodeURIComponent(seed)}` : ''
    const url = `${WS_BASE}/ws/live/${encodeURIComponent(scenario)}${params}`

    console.info('[ADAS] Opening WebSocket:', url)
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (wsRef.current === ws) {
        setStatus('open')
        ws.send(JSON.stringify({ type: 'set_speed', value: speed }))
      }
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setTelemetry(data)
        if (Array.isArray(data.ego_pos)) {
          setHistory((prev) => {
            const next = [...prev, data.ego_pos]
            return next.length > 400 ? next.slice(-400) : next
          })
        }
      } catch (err) {
        console.error('[ADAS] Invalid telemetry message:', err)
      }
    }

    ws.onerror = (event) => {
      console.error('[ADAS] WebSocket error:', event)
      if (wsRef.current === ws) setStatus('error')
    }

    ws.onclose = (event) => {
      console.warn('[ADAS] WebSocket closed:', event.code, event.reason)
      if (wsRef.current === ws) {
        wsRef.current = null
        setStatus((s) => (s === 'error' ? 'error' : 'closed'))
      }
    }
  }, [])

  const setSpeed = useCallback((speed) => {
    const value = Number(speed)
    if (!Number.isFinite(value)) return
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'set_speed', value }))
    }
  }, [])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }
    setStatus('closed')
  }, [])

  useEffect(() => () => {
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
    }
  }, [])

  return { telemetry, status, history, connect, setSpeed, disconnect }
}
