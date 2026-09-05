import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { Map as MLMap, Marker } from 'maplibre-gl'
import type { CopEvent, Layers, Location, Person, Selection, Snapshot } from './types'
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
}

export default function MapView({ snapshot, selection, layers, onSelect }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<MLMap | null>(null)
  const markers = useRef<Marker[]>([])
  const loaded = useRef(false)
  const framed = useRef(savedBoard() != null)   // applied once, and never over a board this browser remembers
  const propsRef = useRef({ snapshot, layers, onSelect, selection })
  propsRef.current = { snapshot, layers, onSelect, selection }

  // ---- init ----
  useEffect(() => {
    if (!el.current || map.current) return
    const m = new maplibregl.Map({
      container: el.current, style: STYLE, ...(savedBoard() ?? BAY_AREA),
      attributionControl: false, dragRotate: false, pitchWithRotate: false,
    })
    m.on('moveend', () => { try { localStorage.setItem(BOARD_KEY, JSON.stringify({ center: m.getCenter().toArray(), zoom: m.getZoom() })) } catch { /* private mode */ } })
    m.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
    m.on('load', () => {
      loaded.current = true
      m.resize()
      m.addSource('threats', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'threat-fill', type: 'fill', source: 'threats',
        paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.18 } })
      m.addLayer({ id: 'threat-line', type: 'line', source: 'threats',
        paint: { 'line-color': ['get', 'color'], 'line-width': 1.5, 'line-opacity': 0.9, 'line-dasharray': [2, 2] } })
      m.addSource('incidents', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'incident-fill', type: 'fill', source: 'incidents', paint: { 'fill-color': '#ef4444', 'fill-opacity': 0.10 } })
      m.addLayer({ id: 'incident-line', type: 'line', source: 'incidents', paint: { 'line-color': '#ef4444', 'line-width': 2.5, 'line-dasharray': [3, 2] } })
      m.addSource('routes', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'route-line', type: 'line', source: 'routes',
        paint: { 'line-color': ['case', ['==', ['get', 'status'], 'active'], '#60a5fa', '#64748b'],
                 'line-width': ['case', ['==', ['get', 'status'], 'active'], 2, 1.5],
                 'line-opacity': 0.85, 'line-dasharray': ['case', ['==', ['get', 'status'], 'active'], ['literal', [1, 0]], ['literal', [2, 3]]] } })
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
    const { snapshot, layers } = propsRef.current
    if (!snapshot || !m.getSource('threats')) return
    const threats = m.getSource('threats') as maplibregl.GeoJSONSource
    threats.setData({ type: 'FeatureCollection', features: layers.threats ? snapshot.threats.map(t => ({
      type: 'Feature', properties: { id: t.id, color: SEV_COLOR[t.severity] },
      geometry: { type: 'Polygon', coordinates: [circle(t.lat, t.lon, t.radius_km)] },
    })) : [] })
    const incidents = m.getSource('incidents') as maplibregl.GeoJSONSource
    incidents.setData({ type: 'FeatureCollection', features: snapshot.incidents.filter(i => i.status === 'open').map(i => ({
      type: 'Feature', properties: { id: i.id }, geometry: { type: 'Polygon', coordinates: [circle(i.lat, i.lon, i.radius_km)] },
    })) })
    const routes = m.getSource('routes') as maplibregl.GeoJSONSource
    routes.setData({ type: 'FeatureCollection', features: layers.routes ? snapshot.trips.map(t => ({
      type: 'Feature', properties: { id: t.id, status: t.status },
      geometry: { type: 'LineString', coordinates: arc(t.origin_lat, t.origin_lon, t.dest_lat, t.dest_lon) },
    })) : [] })
  }
  useEffect(() => { if (map.current && loaded.current) { renderData(map.current); renderMarkers(map.current) } }, [snapshot, layers])

  // ---- markers with screen-space clustering ----
  function renderMarkers(m: MLMap) {
    const { snapshot, layers, onSelect, selection } = propsRef.current
    markers.current.forEach(mk => mk.remove()); markers.current = []
    if (!snapshot) return
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

    for (const c of clusters) {
      const div = document.createElement('div')
      const locs = c.members.filter(x => x.kind === 'location')
      const ppl = c.members.filter(x => x.kind === 'person')
      const evs = c.members.filter(x => x.kind === 'event')
      const selected = c.members.some(x => selection && x.kind === selection.type && x.id === selection.id)
      if (c.members.length === 1 && locs.length === 1) {
        const l = locs[0].loc!
        // §3 the map-first sections: with the S4 or S6 layer on, the site wears that section's health
        const sec = layers.s6 && l.s6_status ? `sec-${l.s6_status}` : layers.s4 && l.s4_status ? `sec-${l.s4_status}` : ''
        div.className = `mk mk-loc mk-${l.type} posture-${l.effective_posture}${selected ? ' selected' : ''}${l.threat_ids_in_area.length ? ' in-area' : ''} ${sec}`
        const chips = (layers.s4 && l.s4_status ? `<span class="sec s4 ${l.s4_status}" title="S4 ${l.s4_status}">S4${l.s4_red ? ' ' + l.s4_red : ''}</span>` : '') +
                      (layers.s6 && l.s6_status ? `<span class="sec s6 ${l.s6_status}" title="S6 ${l.s6_status}${l.s6_in_use ? ' · on ' + l.s6_in_use : ''}">S6${l.s6_down ? ' ' + l.s6_down : ''}</span>` : '')
        div.innerHTML = `<span class="glyph">${TYPE_GLYPH[l.type]}</span><span class="badge">${l.present}</span>${l.vips_present ? '<span class="vip">★</span>' : ''}${chips ? `<span class="secs">${chips}</span>` : ''}`
        div.title = `${l.name} — ${l.present} present / ${l.assigned} assigned${l.s4_status ? ` · S4 ${l.s4_status}` : ''}${l.s6_status ? ` · S6 ${l.s6_status}${l.s6_in_use ? ' on ' + l.s6_in_use.toUpperCase() : ''}` : ''}`
        div.onclick = e => { e.stopPropagation(); onSelect({ type: 'location', id: l.id }) }
      } else if (c.members.length === 1 && ppl.length === 1) {
        const p = ppl[0].person!
        div.className = `mk mk-person${p.is_vip ? ' vip' : ''}${p.position_source === 'checkin' ? ' checked' : ''}${p.confirmed_threat_ids.length ? ' threatened' : ''}${selected ? ' selected' : ''}`
        div.innerHTML = `<span class="glyph">●</span><span class="label">${p.short_name ?? p.name.split(' ')[0]}</span>`
        div.title = `${p.name} — ${p.role}`
        div.onclick = e => { e.stopPropagation(); onSelect({ type: 'person', id: p.id }) }
      } else if (c.members.length === 1 && evs.length === 1) {
        const e = evs[0].event!
        div.className = `mk mk-event${selected ? ' selected' : ''}`
        div.innerHTML = `<span class="glyph">★</span><span class="label">T-${e.days_until}d</span>`
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
        div.className = `mk mk-cluster posture-${LEVELS[worst]}${selected ? ' selected' : ''} ${sec}`
        div.innerHTML = `<span class="count">${present}</span><span class="sub">${locs.length} site${locs.length === 1 ? '' : 's'}${ppl.length ? ` · ${ppl.length} tvl` : ''}${evs.length ? ` · ${evs.length} evt` : ''}</span>${chips ? `<span class="secs">${chips}</span>` : ''}`
        div.title = c.members.map(x => x.loc?.name ?? x.person?.name ?? x.event?.name).join('\n')
        div.onclick = e => { e.stopPropagation(); m.flyTo({ center: [c.lon, c.lat], zoom: Math.min(m.getZoom() + 2.5, 12), speed: 1.4 }) }
      }
      markers.current.push(new maplibregl.Marker({ element: div, anchor: 'center' }).setLngLat([c.lon, c.lat]).addTo(m))
    }
  }

  // ---- the opening frame (§3.1) ----
  // Only for a browser with no board of its own: the declared AO, else this deployment's home ground. Set once,
  // after which the map is the operator's to move and nothing takes it back.
  useEffect(() => {
    const m = map.current, v = snapshot?.view
    if (!m || !v || framed.current || v.center_lat == null || v.center_lon == null) return
    framed.current = true
    const r = v.radius_km ?? 250
    const dLat = r / 111, dLon = r / (111 * Math.max(Math.cos((v.center_lat * Math.PI) / 180), 0.01))
    const fit = () => m.fitBounds([[v.center_lon! - dLon, v.center_lat! - dLat], [v.center_lon! + dLon, v.center_lat! + dLat]], { padding: 48, duration: 0, maxZoom: 12 })
    if (loaded.current) fit(); else m.once('load', fit)
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
    if (target) m.flyTo({ center: [target.lon, target.lat], zoom: target.zoom, speed: 1.2, curve: 1.4 })
    if (loaded.current) renderMarkers(m)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selection])

  return <div ref={el} className="map" onClick={() => onSelect(null)} />
}
