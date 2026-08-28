import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  preview: {
    allowedHosts: ['sihadascomplete-production-96cc.up.railway.app']
  },
  plugins: [react()],
  server: {
    port: 5173,
  },
})
