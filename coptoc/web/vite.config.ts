import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // MapLibre 6 spawns its tile worker from a sibling module via import.meta.url;
  // Vite's pre-bundle flattens the package and the worker file goes missing. Serve it unbundled.
  optimizeDeps: { exclude: ['maplibre-gl'] },
  // A second checkout may symlink node_modules to the first; the worker must still be served from inside this root.
  resolve: { preserveSymlinks: true },
  server: {
    port: 5173,
    proxy: { '/v1': process.env.TOC_API ?? 'http://localhost:8000' },  // a second checkout points at its own API
  },
})
