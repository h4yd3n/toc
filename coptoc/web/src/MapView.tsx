import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { Map as MLMap, Marker } from 'maplibre-gl'
import type { CopEvent, Draw, Layers, Location, Movement, Overlay, Person, Selection, Snapshot } from './types'
import { arc, circle } from './geo'

// Free, keyless vector basemap. Attribution is carried in the style JSON.
const STYLE = 'https://tiles.openfreemap.org/styles/dark'

// Where a wall that remembers nothing and cannot reach the API opens: the Bay Area.
const BAY_AREA = { center: [-122.16, 37.72] as [number, number], zoom: 8 }
const BOARD_KEY = 'toc.board.2'   // bumped when home station replaced the fixed defaults, so a browser remembering the old one starts over

/** The board this browser was left on. A wall that remembers is never pulled somewhere by the server's default. */
function savedBoard(): { center: [number, number]; zoom: number } | null {
  try {
    const raw = localStorage.getItem(BOARD_KEY); if (!raw) return null
    const b = JSON.parse(raw)
    if (typeof b?.zoom !== 'number' || !Array.isArray(b.center) || b.center.length !== 2) return null
    if (Math.abs(b.center[0]) > 180 || Math.abs(b.center[1]) > 90) return null
    return b
  } catch { return null }   // private mode, or someone else's key
}

const SEV_COLOR: Record<string, string> = { low: '#f59e0b', moderate: '#f97316', elevated: '#ef4444', critical: '#dc2626' }
const TYPE_GLYPH: Record<string, string> = { hq: '◆', office: '■', datacenter: '▣', residence: '⌂', venue: '★', airfield: '✈', cp: '▲', fob: '⬢', farp: '⛽', range: '◎' }

interface Point { kind: 'location' | 'person' | 'event'; id: string; lat: number; lon: number; loc?: Location; person?: Person; event?: CopEvent }
interface Cluster { x: number; y: number; lat: number; lon: number; members: Point[] }

interface Props {
  snapshot: Snapshot | null
  selection: Selection
  layers: Layers
  onSelect: (s: Selection) => void
  /** §3.4 which section's overlay is up. COP shows everything; a section brings its own things forward and dims the rest. */
  overlay: Overlay
  /** S2's time window in hours back from now for threats, or null for everything. */
  timeBack: number | null
  /** S3's scrub: a moment on the strip; what is not happening then dims. */
  scrub: number | null
  /** §3.4 what is being drawn, if anything: clicks add points, a double-click finishes. */
  draw: Draw | null
  onDrawPoint: (p: [number, number]) => void
  onDrawFinish: () => void
}
const HOUR = 36e5
// how far the other sections' things fade under each overlay: an overlay sits on the base, the base stays
const DIM = 0.28
/** A threat's ring fades with age: full at observation, a quarter after thirty days. */
const ageFactor = (iso: string, now: number) => { const d = (now - +new Date(iso)) / 864e5; return d <= 0 ? 1 : d >= 30 ? 0.25 : 1 - 0.75 * (d / 30) }
const HEALTH_COLOR: Record<string, string> = { green: '#22c55e', amber: '#f59e0b', red: '#ef4444' }
const RATING_LETTER: Record<string, string> = { green: 'G', amber: 'A', red: 'R', unknown: '?' }

export default function MapView({ snapshot, selection, layers, onSelect, overlay, timeBack, scrub, draw, onDrawPoint, onDrawFinish }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<MLMap | null>(null)
  const markers = useRef<Marker[]>([])
  const loaded = useRef(false)
  const framed = useRef(savedBoard() != null)   // applied once, and never over a board this browser remembers
  const waiting = useRef(false)                // an opening frame queued against a style that has not landed yet
  const propsRef = useRef({ snapshot, layers, onSelect, selection, overlay, timeBack, scrub, draw, onDrawPoint, onDrawFinish })
  propsRef.current = { snapshot, layers, onSelect, selection, overlay, timeBack, scrub, draw, onDrawPoint, onDrawFinish }

  // ---- init ----
  useEffect(() => {
    if (!el.current || map.current) return
    const m = new maplibregl.Map({
      container: el.current, style: STYLE, ...(savedBoard() ?? BAY_AREA),
      attributionControl: false, dragRotate: false, pitchWithRotate: false,
    })
    // Only once the board is real — the opening frame applied, or a remembered one restored. Saving before that
    // persists the placeholder we show while the first snapshot is in flight, and the wall would open there forever.
    m.on('moveend', () => {
      if (!framed.current) return
      try { localStorage.setItem(BOARD_KEY, JSON.stringify({ center: m.getCenter().toArray(), zoom: m.getZoom() })) } catch { /* private mode */ }
    })
    m.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
    m.on('load', () => {
      loaded.current = true
      m.resize()
      // §3.4 the S2 overlay: NAIs under everything, then threats (fading with age; solid when a link is confirmed, dashed when only suggested), then the links
      m.addSource('nais', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'nai-fill', type: 'fill', source: 'nais', paint: { 'fill-color': ['get', 'color'], 'fill-opacity': ['get', 'fo'] } })
      m.addLayer({ id: 'nai-line', type: 'line', source: 'nais', paint: { 'line-color': ['get', 'color'], 'line-width': ['get', 'lw'], 'line-opacity': ['get', 'lo'], 'line-dasharray': [4, 3] } })
      m.addSource('threats', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'threat-fill', type: 'fill', source: 'threats',
        paint: { 'fill-color': ['get', 'color'], 'fill-opacity': ['get', 'fo'] } })
      m.addLayer({ id: 'threat-line', type: 'line', source: 'threats', filter: ['!', ['get', 'confirmed']],
        paint: { 'line-color': ['get', 'color'], 'line-width': 1.5, 'line-opacity': ['get', 'lo'], 'line-dasharray': [2, 2] } })
      m.addLayer({ id: 'threat-line-confirmed', type: 'line', source: 'threats', filter: ['get', 'confirmed'],
        paint: { 'line-color': ['get', 'color'], 'line-width': 2.2, 'line-opacity': ['get', 'lo'] } })
      // §3.4 the graphics: what a section drew by hand — polygons filled faintly, lines by type, and the draft while drawing
      m.addSource('graphics', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'gfx-fill', type: 'fill', source: 'graphics', filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': ['get', 'color'], 'fill-opacity': ['get', 'fo'] } })
      m.addLayer({ id: 'gfx-line', type: 'line', source: 'graphics', filter: ['!', ['get', 'dash']], paint: { 'line-color': ['get', 'color'], 'line-width': ['get', 'lw'], 'line-opacity': ['get', 'lo'] } })
      m.addLayer({ id: 'gfx-line-dashed', type: 'line', source: 'graphics', filter: ['get', 'dash'], paint: { 'line-color': ['get', 'color'], 'line-width': ['get', 'lw'], 'line-opacity': ['get', 'lo'], 'line-dasharray': [4, 3] } })
      m.addSource('draft', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'draft-fill', type: 'fill', source: 'draft', filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': '#fbbf24', 'fill-opacity': 0.12 } })
      m.addLayer({ id: 'draft-line', type: 'line', source: 'draft', paint: { 'line-color': '#fbbf24', 'line-width': 2, 'line-dasharray': [2, 2] } })
      m.addLayer({ id: 'draft-pts', type: 'circle', source: 'draft', filter: ['==', ['geometry-type'], 'Point'], paint: { 'circle-color': '#fbbf24', 'circle-radius': 4 } })
      for (const id of ['gfx-fill', 'gfx-line', 'gfx-line-dashed']) {
        m.on('click', id, (e: maplibregl.MapLayerMouseEvent) => { if (propsRef.current.draw) return; const f = e.features?.[0]; if (f) propsRef.current.onSelect({ type: 'graphic', id: String(f.properties?.id) }) })
        m.on('mouseenter', id, () => { if (!propsRef.current.draw) m.getCanvas().style.cursor = 'pointer' })
        m.on('mouseleave', id, () => (m.getCanvas().style.cursor = propsRef.current.draw ? 'crosshair' : ''))
      }
      // drawing: a click adds a point, a double-click finishes; the map's own double-click zoom is off while drawing
      m.on('click', (e: maplibregl.MapMouseEvent) => { const d = propsRef.current.draw; if (!d) return; propsRef.current.onDrawPoint([+e.lngLat.lng.toFixed(5), +e.lngLat.lat.toFixed(5)]) })
      m.on('dblclick', (e: maplibregl.MapMouseEvent) => { if (!propsRef.current.draw) return; e.preventDefault(); propsRef.current.onDrawFinish() })
      m.addSource('links', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'link-line', type: 'line', source: 'links', paint: { 'line-color': '#ef4444', 'line-width': ['case', ['get', 'confirmed'], 2, 1], 'line-opacity': ['get', 'lo'], 'line-dasharray': ['case', ['get', 'confirmed'], ['literal', [1, 0]], ['literal', [2, 3]]] } })
      m.addSource('incidents', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'incident-fill', type: 'fill', source: 'incidents', paint: { 'fill-color': '#ef4444', 'fill-opacity': 0.10 } })
      m.addLayer({ id: 'incident-line', type: 'line', source: 'incidents', paint: { 'line-color': '#ef4444', 'line-width': 2.5, 'line-dasharray': [3, 2] } })
      // §3.4 the S3 overlay: movements drawn leg by leg — a flight as an arc, a ground leg on the ground, a shipment dashed orange
      m.addSource('routes', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'route-line', type: 'line', source: 'routes',
        paint: { 'line-color': ['get', 'color'], 'line-width': ['get', 'lw'], 'line-opacity': ['get', 'lo'],
                 'line-dasharray': ['case', ['==', ['get', 'dash'], 1], ['literal', [2, 3]], ['==', ['get', 'dash'], 2], ['literal', [4, 2]], ['literal', [1, 0]]] } })
      m.on('click', 'threat-fill', (e: maplibregl.MapLayerMouseEvent) => {
        const f = e.features?.[0]; if (f) propsRef.current.onSelect({ type: 'threat', id: String(f.properties?.id) })
      })
      m.on('mouseenter', 'threat-fill', () => (m.getCanvas().style.cursor = 'pointer'))
      m.on('mouseleave', 'threat-fill', () => (m.getCanvas().style.cursor = ''))
      renderData(m)
      renderMarkers(m)
    })
    m.on('move', () => renderMarkers(m))
    const ro = new ResizeObserver(() => m.resize())
    ro.observe(el.current)
    const onWin = () => m.resize()
    window.addEventListener('resize', onWin)
    map.current = m
    if (import.meta.env.DEV) (window as unknown as { __tocMap?: MLMap }).__tocMap = m
    m.on('error', e => console.error('[maplibre]', e.error?.message ?? e))
    return () => { ro.disconnect(); window.removeEventListener('resize', onWin); loaded.current = false; m.remove(); map.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ---- data layers ----
  function renderData(m: MLMap) {
    const { snapshot, layers, overlay, timeBack, scrub } = propsRef.current
    if (!snapshot || !m.getSource('threats')) return
    const now = Date.now()
    const s2 = overlay === 'S2', s3 = overlay === 'S3', cop = overlay === 'COP'
    const cut = timeBack != null ? now - timeBack * HOUR : null
    // threats: on the COP and the S2 overlay in full, faded with age; a quarter-strength context under the other sections
    const threats = m.getSource('threats') as maplibregl.GeoJSONSource
    const tWeight = cop || s2 ? 1 : DIM
    threats.setData({ type: 'FeatureCollection', features: layers.threats ? snapshot.threats.filter(t => cut == null || +new Date(t.observed_at) >= cut).map(t => { const a = ageFactor(t.observed_at, now) * tWeight; return {
      type: 'Feature', properties: { id: t.id, color: SEV_COLOR[t.severity], fo: 0.06 + 0.16 * a, lo: 0.3 + 0.65 * a, confirmed: t.confirmed_links.length > 0 },
      geometry: { type: 'Polygon', coordinates: [circle(t.lat, t.lon, t.radius_km)] },
    } }) : [] })
    // confirmed and suggested links, threat → site or person, on the S2 overlay
    const links = m.getSource('links') as maplibregl.GeoJSONSource
    const at = (type: string, id: string): [number, number] | null => { if (type === 'location') { const l = snapshot.locations.find(x => x.id === id); return l ? [l.lon, l.lat] : null } const p = snapshot.people.find(x => x.id === id); return p ? [p.lon, p.lat] : null }
    const linkFeatures: { type: 'Feature'; properties: Record<string, unknown>; geometry: { type: 'LineString'; coordinates: [number, number][] } }[] = []
    if (s2 || cop) for (const t of snapshot.threats) {
      if (cut != null && +new Date(t.observed_at) < cut) continue
      for (const l of t.confirmed_links) { const to = at(l.target_type, l.target_id); if (to) linkFeatures.push({ type: 'Feature', properties: { confirmed: true, lo: s2 ? 0.9 : 0.5 }, geometry: { type: 'LineString', coordinates: [[t.lon, t.lat], to] } }) }
      if (s2) for (const sg of t.suggested_targets) if (!t.confirmed_links.some(c => c.target_id === sg.target_id)) { const to = at(sg.target_type, sg.target_id); if (to) linkFeatures.push({ type: 'Feature', properties: { confirmed: false, lo: 0.45 }, geometry: { type: 'LineString', coordinates: [[t.lon, t.lat], to] } }) }
    }
    links.setData({ type: 'FeatureCollection', features: linkFeatures })
    // NAIs: every active requirement as a named area, colored by how well it is collected; full on S2, faint on the COP, gone elsewhere
    const nais = m.getSource('nais') as maplibregl.GeoJSONSource
    const nWeight = s2 ? 1 : cop ? 0.35 : 0
    nais.setData({ type: 'FeatureCollection', features: nWeight === 0 ? [] : (snapshot.nais ?? []).map(n => ({
      type: 'Feature', properties: { id: n.id, color: HEALTH_COLOR[n.health], fo: (n.priority === 1 ? 0.10 : 0.05) * nWeight, lo: (n.priority === 1 ? 0.9 : 0.55) * nWeight, lw: n.priority === 1 ? 1.8 : 1 },
      geometry: { type: 'Polygon', coordinates: [circle(n.lat, n.lon, n.radius_km)] },
    })) })
    // the graphics: the owning section's forward, the rest dimmed; a range is loud only in its window
    const gfx = m.getSource('graphics') as maplibregl.GeoJSONSource
    gfx.setData({ type: 'FeatureCollection', features: (snapshot.graphics ?? []).filter(g => g.kind !== 'point').map(g => {
      const w = (cop || overlay === g.section ? 1 : DIM) * (g.status === 'planned' ? 0.7 : 1) * (g.window_from && !g.in_window ? 0.45 : 1)
      const sel = selection?.type === 'graphic' && selection.id === g.id
      return { type: 'Feature' as const, properties: { id: g.id, color: g.color, dash: g.dash, fo: (g.type === 'range' && g.in_window ? 0.22 : 0.07) * w, lo: (sel ? 1 : 0.85) * w, lw: sel ? 3.5 : g.type === 'boundary' || g.type === 'phase_line' ? 1.5 : 2.5 },
        geometry: g.kind === 'polygon' ? { type: 'Polygon' as const, coordinates: [[...(g.geometry as [number, number][]), (g.geometry as [number, number][])[0]]] } : { type: 'LineString' as const, coordinates: g.geometry as [number, number][] } }
    }) })
    const draft = m.getSource('draft') as maplibregl.GeoJSONSource
    const d = propsRef.current.draw
    draft.setData({ type: 'FeatureCollection', features: !d ? [] : [
      ...d.points.map(p => ({ type: 'Feature' as const, properties: {}, geometry: { type: 'Point' as const, coordinates: p } })),
      ...(d.points.length >= 2 ? [{ type: 'Feature' as const, properties: {}, geometry: d.kind === 'polygon' && d.points.length >= 3 ? { type: 'Polygon' as const, coordinates: [[...d.points, d.points[0]]] } : { type: 'LineString' as const, coordinates: d.points } }] : []),
    ] })
    m.getCanvas().style.cursor = d ? 'crosshair' : ''
    if (d) m.doubleClickZoom.disable(); else m.doubleClickZoom.enable()
    const incidents = m.getSource('incidents') as maplibregl.GeoJSONSource
    incidents.setData({ type: 'FeatureCollection', features: snapshot.incidents.filter(i => i.status === 'open').map(i => ({
      type: 'Feature', properties: { id: i.id }, geometry: { type: 'Polygon', coordinates: [circle(i.lat, i.lon, i.radius_km)] },
    })) })
    // movements, leg by leg: what is not moving at the scrubbed moment dims; under other overlays everything that moves is context
    const routes = m.getSource('routes') as maplibregl.GeoJSONSource
    const mWeight = s3 || cop ? 1 : overlay === 'S4' ? 0.6 : DIM
    const activeAt = (mv: Movement, t: number) => (mv.depart_at ? +new Date(mv.depart_at) <= t : true) && +new Date(mv.return_at) >= t
    routes.setData({ type: 'FeatureCollection', features: layers.routes ? (snapshot.movements ?? []).flatMap(mv => {
      const w = (overlay === 'S4' ? (mv.kind === 'shipment' ? 1 : DIM) : mWeight) * (scrub != null && !activeAt(mv, scrub) ? 0.15 : 1)
      const color = mv.kind === 'shipment' ? (mv.health === 'red' ? '#ef4444' : '#f97316') : mv.is_vip ? '#fbbf24' : mv.status === 'active' ? '#60a5fa' : '#64748b'
      return mv.legs.filter(lg => lg.from_lat != null && lg.kind !== 'lodging').map(lg => ({
        type: 'Feature' as const, properties: { id: mv.id, color, lw: lg.status === 'current' ? (mv.pax >= 3 ? 3 : 2.2) : 1.4, lo: (lg.status === 'done' ? 0.35 : lg.status === 'current' ? 0.95 : 0.7) * w, dash: mv.kind === 'shipment' ? 2 : lg.status === 'planned' ? 1 : 0 },
        geometry: { type: 'LineString' as const, coordinates: lg.kind === 'flight' || lg.kind === 'route' ? arc(lg.from_lat!, lg.from_lon!, lg.to_lat, lg.to_lon) : [[lg.from_lon!, lg.from_lat!], [lg.to_lon, lg.to_lat]] },
      }))
    }) : [] })
  }
  useEffect(() => { if (map.current && loaded.current) { renderData(map.current); renderMarkers(map.current) } }, [snapshot, layers, overlay, timeBack, scrub, draw, selection])

  // ---- markers with screen-space clustering ----
  function renderMarkers(m: MLMap) {
    const { snapshot, layers, onSelect, selection, overlay, timeBack, scrub } = propsRef.current
    markers.current.forEach(mk => mk.remove()); markers.current = []
    if (!snapshot) return
    const now = Date.now()
    const s2 = overlay === 'S2', s3 = overlay === 'S3', cop = overlay === 'COP'
    const cut = timeBack != null ? now - timeBack * HOUR : null
    const movements = snapshot.movements ?? []
    const activeAt = (mv: Movement, t: number) => (mv.depart_at ? +new Date(mv.depart_at) <= t : true) && +new Date(mv.return_at) >= t
    const movementOf = (pid: string) => movements.find(mv => mv.person_ids.includes(pid))
    const inbound = (lid: string) => movements.filter(mv => mv.kind === 'shipment' && snapshot.locations.find(l => l.id === lid && l.name === mv.dest_name))
    // what dims under this overlay: a person is S1's and S3's, an event S3's, a site everyone's base
    const dimPerson = (p: Person) => (overlay === 'S2' || overlay === 'S4' || overlay === 'S6') || (scrub != null && (() => { const mv = movementOf(p.id); return mv ? !activeAt(mv, scrub) : false })())
    const dimEvent = (e: CopEvent) => (overlay !== 'COP' && overlay !== 'S3') || (scrub != null && !(+new Date(e.start_at) <= scrub && +new Date(e.end_at) >= scrub))
    const pts: Point[] = []
    if (layers.locations) for (const l of snapshot.locations) {
      if (l.sensitivity === 'restricted' && !layers.residences) continue
      pts.push({ kind: 'location', id: l.id, lat: l.lat, lon: l.lon, loc: l })
    }
    if (layers.travelers) for (const p of snapshot.people) if (p.status === 'traveling')
      pts.push({ kind: 'person', id: p.id, lat: p.lat, lon: p.lon, person: p })
    if (layers.events) for (const e of snapshot.events) if (!e.venue_location_id)
      pts.push({ kind: 'event', id: e.id, lat: e.venue_lat, lon: e.venue_lon, event: e })

    const clusters: Cluster[] = []
    const R = 44
    for (const p of pts) {
      const s = m.project([p.lon, p.lat])
      const c = clusters.find(c => Math.hypot(c.x - s.x, c.y - s.y) < R)
      if (c) { c.members.push(p) } else clusters.push({ x: s.x, y: s.y, lat: p.lat, lon: p.lon, members: [p] })
    }
    const eta = (h: number) => h < 0 ? `${Math.abs(Math.round(h))}h late` : h < 48 ? `ETA ${Math.round(h)}h` : `ETA ${Math.round(h / 24)}d`
    // MapLibre writes an inline opacity on every marker element, so the dim has to go through the marker, not the class
    const add = (div: HTMLElement, lon: number, lat: number, anchor: maplibregl.PositionAnchor = 'center', offset?: [number, number]) => markers.current.push(new maplibregl.Marker({ element: div, anchor, offset, opacity: div.classList.contains('dim') ? String(DIM) : '1' }).setLngLat([lon, lat]).addTo(m))

    for (const c of clusters) {
      const div = document.createElement('div')
      const locs = c.members.filter(x => x.kind === 'location')
      const ppl = c.members.filter(x => x.kind === 'person')
      const evs = c.members.filter(x => x.kind === 'event')
      const selected = c.members.some(x => selection && x.kind === selection.type && x.id === selection.id)
      if (c.members.length === 1 && locs.length === 1) {
        const l = locs[0].loc!
        // §3 the map-first sections: with the S4 or S6 layer on, the site wears that section's health; on S2 it wears the analyst's rating
        const sec = layers.s6 && l.s6_status ? `sec-${l.s6_status}` : layers.s4 && l.s4_status ? `sec-${l.s4_status}` : s2 && l.area ? `sec-${l.area.worst === 'unknown' ? 'none' : l.area.worst}` : ''
        div.className = `mk mk-loc mk-${l.type} posture-${l.effective_posture}${selected ? ' selected' : ''}${l.threat_ids_in_area.length ? ' in-area' : ''} ${sec}`
        const chips = (layers.s4 && l.s4_status ? `<span class="sec s4 ${l.s4_status}" title="S4 ${l.s4_status}">S4${l.s4_red ? ' ' + l.s4_red : ''}</span>` : '') +
                      (layers.s6 && l.s6_status ? `<span class="sec s6 ${l.s6_status}" title="S6 ${l.s6_status}${l.s6_in_use ? ' · on ' + l.s6_in_use : ''}">S6${l.s6_down ? ' ' + l.s6_down : ''}</span>` : '')
        const inb = (s3 || overlay === 'S4') ? inbound(l.id) : []
        const badge = s2 ? (l.area ? `<span class="badge rating ${l.area.worst}" title="${l.area.place}: ${l.area.counts.red} red · ${l.area.counts.amber} amber · ${l.area.counts.green} green">${RATING_LETTER[l.area.worst]}</span>` : '')
          : `<span class="badge">${l.present}</span>`
        div.innerHTML = `<span class="glyph">${TYPE_GLYPH[l.type]}</span>${badge}${l.vips_present && !s2 ? '<span class="vip">★</span>' : ''}${chips ? `<span class="secs">${chips}</span>` : ''}` +
          (inb.length ? `<span class="inb ${inb.some(x => x.health === 'red') ? 'red' : inb.some(x => x.health === 'amber') ? 'amber' : ''}" title="${inb.map(x => `${x.name} · ${eta(x.hours_to_eta ?? 0)}`).join('\n')}">⇣ ${inb.length} · ${eta(Math.min(...inb.map(x => x.hours_to_eta ?? 0)))}</span>` : '')
        div.title = `${l.name} — ${l.present} present / ${l.assigned} assigned${l.s4_status ? ` · S4 ${l.s4_status}` : ''}${l.s6_status ? ` · S6 ${l.s6_status}${l.s6_in_use ? ' on ' + l.s6_in_use.toUpperCase() : ''}` : ''}${l.area ? ` · rated ${l.area.worst.toUpperCase()}` : ''}`
        div.onclick = e => { e.stopPropagation(); onSelect({ type: 'location', id: l.id }) }
      } else if (c.members.length === 1 && ppl.length === 1) {
        const p = ppl[0].person!
        div.className = `mk mk-person${p.is_vip ? ' vip' : ''}${p.position_source === 'checkin' ? ' checked' : ''}${p.confirmed_threat_ids.length ? ' threatened' : ''}${selected ? ' selected' : ''}${dimPerson(p) ? ' dim' : ''}`
        div.innerHTML = `<span class="glyph">●</span><span class="label">${p.short_name ?? p.name.split(' ')[0]}</span>`
        div.title = `${p.name} — ${p.role}`
        div.onclick = e => { e.stopPropagation(); onSelect({ type: 'person', id: p.id }) }
      } else if (c.members.length === 1 && evs.length === 1) {
        const e = evs[0].event!
        div.className = `mk mk-event${selected ? ' selected' : ''}${e.coverage && e.coverage.gap > 0 && (s3 || cop) ? ' gap' : ''}${dimEvent(e) ? ' dim' : ''}`
        div.innerHTML = `<span class="glyph">★</span><span class="label">T-${e.days_until}d${s3 && e.coverage ? ` · ${e.coverage.assigned}/${e.coverage.required}` : ''}${s3 && e.operation ? ` · OP ${e.operation.pct}%` : ''}</span>`
        div.title = `${e.name} — ${e.venue_name}`
        div.onclick = ev => { ev.stopPropagation(); onSelect({ type: 'event', id: e.id }) }
      } else {
        const present = locs.reduce((a, x) => a + x.loc!.present, 0) + ppl.length
        const LEVELS = ['normal', 'guarded', 'elevated', 'high', 'critical']
        const worst = locs.reduce((a, x) => Math.max(a, LEVELS.indexOf(x.loc!.effective_posture)), 0)
        // a cluster wears the worst S4 / S6 health of its sites when that layer is on
        const RANK = { green: 0, amber: 1, red: 2 } as Record<string, number>
        const worstOf = (k: 's4_status' | 's6_status') => locs.map(x => x.loc![k]).filter(Boolean).sort((a, b) => RANK[b!] - RANK[a!])[0] ?? null
        const h4 = layers.s4 ? worstOf('s4_status') : null, h6 = layers.s6 ? worstOf('s6_status') : null
        const sec = h6 ? `sec-${h6}` : h4 ? `sec-${h4}` : ''
        const chips = (h4 ? `<span class="sec s4 ${h4}">S4 ${locs.reduce((a, x) => a + (x.loc!.s4_red ?? 0), 0) || ''}</span>` : '') + (h6 ? `<span class="sec s6 ${h6}">S6 ${locs.reduce((a, x) => a + (x.loc!.s6_down ?? 0), 0) || ''}</span>` : '')
        div.className = `mk mk-cluster posture-${LEVELS[worst]}${selected ? ' selected' : ''} ${sec}${locs.length === 0 && ppl.every(x => dimPerson(x.person!)) ? ' dim' : ''}`
        div.innerHTML = `<span class="count">${present}</span><span class="sub">${locs.length} site${locs.length === 1 ? '' : 's'}${ppl.length ? ` · ${ppl.length} tvl` : ''}${evs.length ? ` · ${evs.length} evt` : ''}</span>${chips ? `<span class="secs">${chips}</span>` : ''}`
        div.title = c.members.map(x => x.loc?.name ?? x.person?.name ?? x.event?.name).join('\n')
        div.onclick = e => { e.stopPropagation(); m.flyTo({ center: [c.lon, c.lat], zoom: Math.min(m.getZoom() + 2.5, 12), speed: 1.4 }) }
      }
      add(div, c.lon, c.lat)
    }
    // §3.4 S2: the NAI labels — number, subject, coverage — at the top of each ring
    if (s2) for (const n of snapshot.nais ?? []) {
      const div = document.createElement('div')
      div.className = `mk mk-nai ${n.health} p${n.priority}`
      div.innerHTML = `<b>${n.name}</b> ${n.subject_name.split(' — ')[0].split(' · ')[0]} <i>${n.coverage_pct}%</i>${n.pir_ids.length ? ` <u>PIR</u>` : ''}`
      div.title = `${n.name} · P${n.priority} · ${n.subject_name}\n${n.question}\n${n.coverage_pct}% covered · ${n.gaps} gap${n.gaps === 1 ? '' : 's'}${n.window_to ? ` · until ${n.window_to.slice(0, 10)}` : ''}`
      div.onclick = e => { e.stopPropagation(); if (n.subject_type === 'location' && n.subject_id) onSelect({ type: 'location', id: n.subject_id }); else if (n.subject_type === 'event' && n.subject_id) onSelect({ type: 'event', id: n.subject_id }) }
      const top = circle(n.lat, n.lon, n.radius_km, 4)[0]   // the northern point of the ring
      add(div, top[0], top[1], 'bottom', [0, -2])
    }
    // §3.4 S3: the head of every group movement — the unit or the delegation, its count, where it is on its route
    if (s3 || cop) for (const mv of movements) {
      if (mv.kind === 'individual') continue
      const dim = scrub != null && !activeAt(mv, scrub)
      const div = document.createElement('div')
      if (mv.kind === 'shipment') {
        if (!mv.legs.length) continue   // no origin on the wall: the site wears the inbound chip instead
        const lg = mv.legs[0]; const mid = arc(lg.from_lat!, lg.from_lon!, lg.to_lat, lg.to_lon, 2)[1]
        div.className = `mk mk-head shipment ${mv.health}${dim ? ' dim' : ''}`
        div.innerHTML = `<span class="glyph">⛽</span><span class="label">${mv.name.split(' → ')[0]} · ${eta(mv.hours_to_eta ?? 0)}</span>`
        div.title = `${mv.name} · ${mv.purpose} · ${mv.current_leg}`
        add(div, mid[0], mid[1])
      } else {
        if (mv.head_lat == null) continue
        div.className = `mk mk-head ${mv.kind} ${mv.status}${mv.is_vip ? ' vip' : ''}${dim ? ' dim' : ''}`
        div.innerHTML = `<span class="glyph">${mv.mode === 'air' ? '✈' : '▶'}</span><span class="label">${mv.unit ?? mv.name.split(' · ')[0]} · ${mv.pax} pax</span>`
        div.title = `${mv.name}\n${mv.purpose}${mv.current_leg ? `\nnow: ${mv.current_leg}` : ''}\n${mv.depart_at?.slice(0, 16).replace('T', ' ')}Z → ${mv.return_at.slice(0, 16).replace('T', ' ')}Z`
        div.onclick = e => { e.stopPropagation(); onSelect({ type: 'person', id: mv.person_ids[0] }) }
        add(div, mv.head_lon!, mv.head_lat, 'top', [0, 12])
      }
    }
    // §3.4 point graphics and the labels of lines and polygons: the glyph and the name, in the section's color
    for (const g of snapshot.graphics ?? []) {
      const w = cop || overlay === g.section
      const div = document.createElement('div')
      const sel = selection?.type === 'graphic' && selection.id === g.id
      div.className = `mk mk-gfx ${g.kind} ${g.status}${w ? '' : ' dim'}${sel ? ' selected' : ''}${g.window_from && !g.in_window ? ' outside' : ''}`
      div.style.borderColor = g.color; div.style.color = g.color
      div.innerHTML = `<span class="glyph">${g.glyph}</span><span class="label">${g.name}</span>`
      div.title = `${g.label} · ${g.section}${g.window_from ? ` · ${g.in_window ? 'in window' : 'outside its window'}` : ''}${g.note ? `\n${g.note}` : ''}\n${g.created_by}`
      div.onclick = e => { e.stopPropagation(); if (!propsRef.current.draw) onSelect({ type: 'graphic', id: g.id }) }
      const at = g.kind === 'point' ? (g.geometry as number[]) : g.center
      add(div, at[0], at[1], g.kind === 'point' ? 'center' : 'bottom', g.kind === 'point' ? undefined : [0, -4])
    }
    void cut
  }

  // ---- the opening frame (§3.1) ----
  // Only for a browser with no board of its own: the declared AO, else this deployment's home ground. Set once,
  // after which the map is the operator's to move and nothing takes it back.
  useEffect(() => {
    const m = map.current, v = snapshot?.view
    if (!m || !v || framed.current || waiting.current || v.center_lat == null || v.center_lon == null) return
    const r = v.radius_km ?? 250
    const dLat = r / 111, dLon = r / (111 * Math.max(Math.cos((v.center_lat * Math.PI) / 180), 0.01))
    const fit = () => {
      framed.current = true   // only once it has actually happened: a map that loads late still gets its frame
      m.fitBounds([[v.center_lon! - dLon, v.center_lat! - dLat], [v.center_lon! + dLon, v.center_lat! + dLat]], { padding: 48, duration: 0, maxZoom: 12 })
    }
    if (loaded.current) { fit(); return }
    waiting.current = true    // the style is still coming; frame it when it lands, and don't queue this twice
    m.once('load', () => { waiting.current = false; if (!framed.current) fit() })
  }, [snapshot?.view])

  // ---- fly on selection ----
  useEffect(() => {
    const m = map.current; if (!m || !snapshot || !selection) return
    let target: { lat: number; lon: number; zoom: number } | null = null
    if (selection.type === 'location') { const l = snapshot.locations.find(x => x.id === selection.id); if (l) target = { lat: l.lat, lon: l.lon, zoom: 11 } }
    if (selection.type === 'person') { const p = snapshot.people.find(x => x.id === selection.id); if (p) target = { lat: p.lat, lon: p.lon, zoom: 9 } }
    if (selection.type === 'incident') { const i = snapshot.incidents.find(x => x.id === selection.id); if (i) target = { lat: i.lat, lon: i.lon, zoom: 12 } }
    if (selection.type === 'event') { const e = snapshot.events.find(x => x.id === selection.id); if (e) target = { lat: e.venue_lat, lon: e.venue_lon, zoom: 11 } }
    if (selection.type === 'threat') { const t = snapshot.threats.find(x => x.id === selection.id); if (t) target = { lat: t.lat, lon: t.lon, zoom: Math.max(6, 11 - Math.log2(Math.max(t.radius_km, 1))) } }
    if (selection.type === 'graphic') { const g = snapshot.graphics?.find(x => x.id === selection.id); if (g) target = { lat: g.center[1], lon: g.center[0], zoom: g.kind === 'point' ? 12 : 10 } }
    if (target) m.flyTo({ center: [target.lon, target.lat], zoom: target.zoom, speed: 1.2, curve: 1.4 })
    if (loaded.current) renderMarkers(m)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selection])

  return <div ref={el} className="map" onClick={() => { if (!draw) onSelect(null) }} />
}
