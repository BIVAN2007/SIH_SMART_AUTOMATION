// config.js
// Central place for backend URLs. Override via .env (VITE_API_BASE / VITE_WS_BASE)
// when deploying the frontend separately from the backend (e.g. Vercel + Railway).

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
export const WS_BASE = import.meta.env.VITE_WS_BASE || 'ws://localhost:8000'
