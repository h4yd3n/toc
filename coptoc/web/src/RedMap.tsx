import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { RedPicture } from './types'

const STYLE = 'https://tiles.openfreemap.org/styles/dark'

/** §5.10b Phase 4 — the graphic INTSUM: the red picture of the period on a small map. Sightings as red points
 *  (hollow when seed), an actor's move as a line from where it was to where it is, threat graphics drawn in the period. */
export function RedMap({ red }: { red: RedPicture }) {
  const el = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!el.current || !red.bounds) return
    const b = red.bounds
    const m = new maplibregl.Map({ container: el.current, style: STYLE, attributionControl: false, dragRotate: false, interactive: true,
      bounds: [[b.west, b.south], [b.east, b.north]], fitBoundsOptions: { padding: 40, maxZoom: 14 } })
    m.on('load', () => {
      const pts = { type: 'FeatureCollection' as const, features: red.sightings.map(s => ({ type: 'Feature' as const, properties: { seed: s.seed ? 1 : 0, label: `${s.actor_name} · ${s.at.slice(5, 16)}Z` }, geometry: { type: 'Point' as const, coordinates: [s.lon, s.lat] } })) }
      const lines = { type: 'FeatureCollection' as const, features: red.moves.filter(x => x.from).map(x => ({ type: 'Feature' as const, properties: { seed: x.seed ? 1 : 0 }, geometry: { type: 'LineString' as const, coordinates: [[x.from!.lon, x.from!.lat], [x.to.lon, x.to.lat]] } })) }
      const polys = { type: 'FeatureCollection' as const, features: red.graphics.filter(g => g.kind === 'polygon').map(g => ({ type: 'Feature' as const, properties: { name: g.name }, geometry: { type: 'Polygon' as const, coordinates: [[...g.geometry, g.geometry[0]]] } })) }
      const gpts = { type: 'FeatureCollection' as const, features: red.graphics.filter(g => g.kind !== 'polygon').map(g => ({ type: 'Feature' as const, properties: { name: g.name }, geometry: { type: 'Point' as const, coordinates: g.center } })) }
      m.addSource('polys', { type: 'geojson', data: polys }); m.addSource('gpts', { type: 'geojson', data: gpts }); m.addSource('lines', { type: 'geojson', data: lines }); m.addSource('pts', { type: 'geojson', data: pts })
      m.addLayer({ id: 'poly-fill', type: 'fill', source: 'polys', paint: { 'fill-color': '#ef4444', 'fill-opacity': 0.12 } })
      m.addLayer({ id: 'poly-line', type: 'line', source: 'polys', paint: { 'line-color': '#ef4444', 'line-width': 1.5, 'line-dasharray': [3, 2] } })
      m.addLayer({ id: 'gpt', type: 'circle', source: 'gpts', paint: { 'circle-radius': 6, 'circle-color': 'rgba(239,68,68,0)', 'circle-stroke-color': '#ef4444', 'circle-stroke-width': 1.5 } })
      m.addLayer({ id: 'mv', type: 'line', source: 'lines', paint: { 'line-color': '#f87171', 'line-width': 2, 'line-opacity': ['case', ['==', ['get', 'seed'], 1], 0.4, 0.9] } })
      m.addLayer({ id: 'pt', type: 'circle', source: 'pts', paint: { 'circle-radius': 5, 'circle-color': ['case', ['==', ['get', 'seed'], 1], 'rgba(239,68,68,0.15)', '#ef4444'], 'circle-stroke-color': '#fecaca', 'circle-stroke-width': 1 } })
      m.addLayer({ id: 'pt-label', type: 'symbol', source: 'pts', layout: { 'text-field': ['get', 'label'], 'text-size': 10, 'text-offset': [0, 1.1], 'text-anchor': 'top' }, paint: { 'text-color': '#fecaca', 'text-halo-color': '#0b1017', 'text-halo-width': 1 } })
    })
    return () => { m.remove() }
  }, [red])
  if (!red.bounds) return <div className="dim small">Nothing on the other side moved in the period; no map.</div>
  return <div ref={el} className="redmap" />
}
