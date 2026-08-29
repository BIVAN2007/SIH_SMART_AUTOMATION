// components/AutoAlertBanner.jsx
// Fires a visible confirmation the moment the backend auto-detects and
// reports a jam (repeated hard braking, see pipeline.py congestion_alert).
// This exists to directly answer "how do I know it's actually getting
// uploaded" -- it lights up exactly on that tick, not on a guess.

import { useEffect, useState, useRef } from 'react'

export default function AutoAlertBanner({ telemetry }) {
  const [visible, setVisible] = useState(false)
  const timeoutRef = useRef(null)

  useEffect(() => {
    if (telemetry?.congestion_alert) {
      setVisible(true)
      clearTimeout(timeoutRef.current)
      timeoutRef.current = setTimeout(() => setVisible(false), 4000)
    }
  }, [telemetry?.t, telemetry?.congestion_alert])

  if (!visible) return null

  return (
    <div className="auto-alert-banner">
      🚨 Repeated hard braking detected — jam auto-reported to the server
    </div>
  )
}
