import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // MapLibre 6 spawns its tile worker from a sibling module via import.meta.url;
  // Vite's pre-bundle flattens the package and the worker file goes missing. Serve it unbundled.
  optimizeDeps: { exclude: ['maplibre-gl'] },
  server: {
    port: 5173,
    proxy: { '/v1': 'http://localhost:8000' },
  },
})
