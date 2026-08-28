// hooks/useSimulationSocket.js
// Manages the WebSocket connection to /ws/live/{scenario} and exposes the
// latest telemetry tick + connection state. This is the single integration
// point between the React app and Layer 2's backend.

import { useEffect, useRef, useState, useCallback } from 'react'
import { WS_BASE } from '../config'

export function useSimulationSocket() {
  const [telemetry, setTelemetry] = useState(null)
  const [status, setStatus] = useState('idle') // idle | connecting | open | closed | error
  const [history, setHistory] = useState([])   // driven path, for trail rendering
  const wsRef = useRef(null)

  const connect = useCallback((scenario, seed) => {
    // tear down any existing connection first
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setHistory([])
    setTelemetry(null)
    setStatus('connecting')

    const params = seed != null ? `?seed=${seed}` : ''
    const ws = new WebSocket(`${WS_BASE}/ws/live/${scenario}${params}`)
    wsRef.current = ws

    ws.onopen = () => setStatus('open')

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setTelemetry(data)
      setHistory((prev) => {
        const next = [...prev, data.ego_pos]
        return next.length > 400 ? next.slice(next.length - 400) : next
      })
    }

    ws.onerror = () => setStatus('error')

    ws.onclose = () => setStatus((s) => (s === 'error' ? 'error' : 'closed'))
  }, [])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setStatus('closed')
  }, [])

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [])

  return { telemetry, status, history, connect, disconnect }
}
