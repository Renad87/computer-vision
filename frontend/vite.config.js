import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev: `npm run dev` on :5174 proxies /api to the FastAPI backend on :8010.
// Prod: `npm run build` -> dist/, served by the backend at http://127.0.0.1:8010/
export default defineConfig({
  plugins: [react()],
  server: { port: 5174, strictPort: true, proxy: { '/api': 'http://127.0.0.1:8010' } },
  preview: { port: 5174, strictPort: true, proxy: { '/api': 'http://127.0.0.1:8010' } },
  build: { outDir: 'dist', emptyOutDir: true },
})
