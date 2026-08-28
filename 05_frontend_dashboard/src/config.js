// Central backend configuration.
// Vite injects VITE_API_BASE / VITE_WS_BASE at BUILD TIME.
//
// Production example:
// VITE_API_BASE=https://your-backend.up.railway.app
// VITE_WS_BASE=wss://your-backend.up.railway.app
//
// If VITE_WS_BASE is omitted, it is derived automatically from VITE_API_BASE.

function cleanBase(value) {
  return String(value || '').trim().replace(/\/+$/, '')
}

const apiEnv = import.meta.env.VITE_API_BASE
const wsEnv = import.meta.env.VITE_WS_BASE

export const API_BASE = cleanBase(apiEnv) || (
  import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin
)

export const WS_BASE = cleanBase(wsEnv) || API_BASE.replace(/^http:/i, 'ws:').replace(/^https:/i, 'wss:')

// Useful when debugging a deployment: these are visible in the browser console.
if (import.meta.env.DEV || import.meta.env.VITE_DEBUG === 'true') {
  console.info('[ADAS] API_BASE:', API_BASE)
  console.info('[ADAS] WS_BASE:', WS_BASE)
}
