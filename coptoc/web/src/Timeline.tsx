// §3.3 S3 as time, through NOW. The left of the strip is this watch so far — every logged event since the watch began,
// drawn as ticks in the lanes the brief uses; the right is the horizon, compressed: the next two days get room, the
// rest of the 90 days is squeezed so a summit in five weeks is still on the board. Spans that began before now cross the
// NOW line. The handover brief's "significant events this shift" is this left half, read out.
import { useEffect, useRef } from 'react'
import type { CopEvent, Selection, Snapshot, Trip, WatchLogEntry } from './types'

const LEG_ICON: Record<string, string> = { flight: '✈', ground: '🚗', lodging: '🏨' }
const DAY = 864e5, HOUR = 36e5
const MIN_DAYS = 21, MAX_DAYS = 90  // the horizon runs to the last planned thing (at least three weeks, at most 90 days)
const NEAR_H = 48
const BUCKET_COLOR: Record<string, string> = { posture: '#fbbf24', threats: '#ef4444', roll_calls: '#ef4444', movement: '#60a5fa', operations: '#c084fc', intel: '#f59e0b', personnel: '#22c55e', collection: '#94a3b8', logistics: '#f97316', signal: '#f97316', other: '#6b7c90' }
const BUCKET_LABEL: Record<string, string> = { posture: 'POSTURE', threats: 'THREAT', roll_calls: 'ROLL CALL', movement: 'MOVEMENT', operations: 'OPS', intel: 'INTEL', personnel: 'PERSONNEL', collection: 'COLLECT', logistics: 'S4', signal: 'S6', other: 'LOG' }
const hhmm = (t: number) => new Date(t).toISOString().slice(11, 16).replace(':', '') + 'Z'

type Span = { id: string; kind: 'event' | 'trip'; label: string; sub: string; start: number; end: number; sel: Selection; cls: string; title: string }

/** Where a subject on the ledger lives on the picture, if it does. */
function subjectSelection(snap: Snapshot, subject: string): Selection {
  if (snap.locations.some(l => l.id === subject)) return { type: 'location', id: subject }
  if (snap.people.some(p => p.id === subject)) return { type: 'person', id: subject }
  if (snap.events.some(e => e.id === subject)) return { type: 'event', id: subject }
  if (snap.threats.some(t => t.id === subject)) return { type: 'threat', id: subject }
  if (snap.incidents.some(i => i.id === subject)) return { type: 'incident', id: subject }
  const trip = snap.trips.find(t => t.id === subject); if (trip) return { type: 'person', id: trip.person_id }
  return null
}

export function Timeline({ snap, now, sel, onSelect, onOp, scrub, onScrub }: { snap: Snapshot | null; now: number; sel: Selection; onSelect: (s: Selection) => void; onOp: (id: string) => void; scrub?: number | null; onScrub?: (t: number | null, pinned?: boolean) => void }) {
  const scrollRef = useRef<HTMLDivElement>(null)

  const t0 = now
  const watchStart = snap?.watch ? +new Date(snap.watch.started_at) : t0 - 8 * HOUR
  const tBack = Math.min(watchStart, t0 - HOUR)   // never a zero-width left half at the top of a watch
  const lastEnd = Math.max(...(snap?.events.map(e => +new Date(e.end_at)) ?? []), ...(snap?.trips.filter(t => !t.event_id).map(t => +new Date(t.return_at)) ?? []), t0 + MIN_DAYS * DAY)
  const tFar = Math.min(t0 + MAX_DAYS * DAY, lastEnd + 2 * DAY)
  const tNear = Math.min(t0 + NEAR_H * HOUR, tFar)
  const days = Math.max(1, (tFar - t0) / DAY)

  // Pixel widths: ample space so future ops are readable and scrollable
  const wBack = 260
  const wNear = 320
  const dayPx = 80
  const wFar = Math.max(1200, Math.round(Math.max(1, days - 2) * dayPx))
  const totalWidth = wBack + wNear + wFar

  const px = (t: number): number => {
    const c = Math.max(tBack, Math.min(tFar, t))
    if (c <= t0) return ((c - tBack) / Math.max(1, t0 - tBack)) * wBack
    if (c <= tNear) return wBack + ((c - t0) / Math.max(1, tNear - t0)) * wNear
    return wBack + wNear + ((c - tNear) / Math.max(1, tFar - tNear)) * wFar
  }

  const tAtPx = (p: number): number => {
    const c = Math.max(0, Math.min(totalWidth, p))
    if (c <= wBack) return tBack + (c / Math.max(1, wBack)) * (t0 - tBack)
    if (c <= wBack + wNear) return t0 + ((c - wBack) / Math.max(1, wNear)) * (tNear - t0)
    return tNear + ((c - wBack - wNear) / Math.max(1, wFar)) * (tFar - tNear)
  }

  const tripsOf = (e: CopEvent) => snap?.trips.filter(t => t.event_id === e.id).length ?? 0
  const spans: Span[] = !snap ? [] : [
    ...snap.events.map((e: CopEvent): Span => ({ id: e.id, kind: 'event', label: `★ ${e.name}`, sub: e.venue_name, start: +new Date(e.start_at), end: +new Date(e.end_at), sel: { type: 'event', id: e.id },
      cls: `ev ${e.status === 'active' ? 'live' : ''} ${e.coverage && e.coverage.gap > 0 ? 'gap' : ''} ${e.threat_ids_in_area.length ? 'threat' : ''}`,
      title: `${e.name} · ${e.venue_name} · ${e.attendee_count} attending · ${e.vip_count} VIP · ${tripsOf(e)} trips` + (e.coverage ? ` · cover ${e.coverage.assigned}/${e.coverage.required}` : '') + (e.operation ? ` · OP ${e.operation.tasks_done}/${e.operation.tasks_total}` : '') })),
    ...snap.trips.filter(t => !t.event_id).map((t: Trip): Span => ({ id: t.id, kind: 'trip', label: `${t.is_vip ? '★ ' : ''}${t.person_short ?? t.person_name.split(' ')[0]} → ${t.dest_name.split(',')[0]}`, sub: t.current_leg ? `${LEG_ICON[t.current_leg.kind]} ${t.current_leg.label || t.current_leg.to_name}` : t.purpose, start: +new Date(t.depart_at), end: +new Date(t.return_at), sel: { type: 'person', id: t.person_id },
      cls: `tr ${t.status} ${t.is_vip ? 'vip' : ''}`, title: `${t.person_name} · ${t.origin_name} → ${t.dest_name} · ${t.purpose}` })),
  ].filter(s => s.end >= tBack && s.start <= tFar).sort((a, b) => a.start - b.start)

  // lanes: events on top, trips beneath; a span takes the first lane whose last span has ended
  const lanes: { kind: 'event' | 'trip' }[] = []
  const laneOf = new Map<string, number>()
  for (const kind of ['event', 'trip'] as const) {
    const ends: number[] = []
    for (const s of spans.filter(v => v.kind === kind)) { let i = ends.findIndex(e => e <= s.start); if (i < 0) { i = ends.length; ends.push(0) } ends[i] = s.end + DAY * 0.4; laneOf.set(s.id, lanes.length + i) }
    for (let i = 0; i < ends.length; i++) lanes.push({ kind })
  }
  const watchEnd = snap?.watch ? +new Date(snap.watch.ends_at) : null

  // ticks: hours on the left, hours through the near horizon, days beyond
  const ticks: { t: number; label: string; major: boolean }[] = []
  const backH = (t0 - tBack) / HOUR
  const hourEvery = backH <= 4 ? 1 : backH <= 9 ? 2 : backH <= 14 ? 3 : 4
  for (let t = Math.ceil(tBack / HOUR) * HOUR; t < t0; t += HOUR) { const hr = new Date(t).getUTCHours(); ticks.push({ t, label: backH > 2 && hr % hourEvery === 0 ? hhmm(t) : '', major: hr % (hourEvery * 2) === 0 }) }
  for (let h = 6; h <= NEAR_H && t0 + h * HOUR < tFar; h += 6) ticks.push({ t: t0 + h * HOUR, label: h % 12 === 0 ? `+${h}h` : '', major: h % 24 === 0 })
  for (let d = 3; d <= days; d += 1) {
    const t = t0 + d * DAY
    const dt = new Date(t)
    const isMon = dt.getUTCDay() === 1
    const dayStr = dt.toUTCString().slice(0, 3) + ' ' + dt.getUTCDate()
    ticks.push({ t, label: dayStr, major: isMon })
  }
  const eventLanes = lanes.filter(l => l.kind === 'event').length

  const getPixel = (e: React.MouseEvent<HTMLDivElement>): number => {
    const r = e.currentTarget.getBoundingClientRect()
    return Math.max(0, Math.min(totalWidth, e.clientX - r.left))
  }
  const scrubX = scrub != null ? px(scrub) : null
  const log: WatchLogEntry[] = (snap?.watch_log ?? []).filter(e => +new Date(e.at) >= tBack)

  const scrollTo = (left: number) => { scrollRef.current?.scrollTo({ left, behavior: 'smooth' }) }
  const scrollBy = (delta: number) => { scrollRef.current?.scrollBy({ left: delta, behavior: 'smooth' }) }
  const onWheel = (e: React.WheelEvent) => {
    if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) return
    if (scrollRef.current && e.deltaY !== 0) { scrollRef.current.scrollLeft += e.deltaY * 0.9 }
  }

  useEffect(() => {
    if (!sel || !scrollRef.current || !snap) return
    const target = spans.find(s => (sel.type === 'event' && s.id === sel.id) || (sel.type === 'person' && s.kind === 'trip' && snap.trips.find(t => t.id === s.id)?.person_id === sel.id))
    if (target) {
      const targetX = px(target.start)
      const curLeft = scrollRef.current.scrollLeft
      const curRight = curLeft + scrollRef.current.clientWidth
      if (targetX < curLeft || targetX > curRight - 120) {
        scrollRef.current.scrollTo({ left: Math.max(0, targetX - 160), behavior: 'smooth' })
      }
    }
  }, [sel?.type, sel?.id, snap])

  if (!snap) return <div className="tl" />

  return (
    <div className="tl-container">
      <div className="tl-nav">
        <div className="tl-nav-group">
          <button className="tl-btn" onClick={() => scrollTo(0)} title="Jump to start (Watch so far)">◀ SO FAR</button>
          <button className="tl-btn now" onClick={() => scrollTo(Math.max(0, wBack - 40))} title="Jump to NOW">● NOW</button>
          <button className="tl-btn" onClick={() => scrollTo(wBack + wNear - 40)} title="Jump to +48 hours">+48h</button>
          <button className="tl-btn" onClick={() => scrollTo(Math.max(0, px(t0 + 7 * DAY) - 40))} title="Jump to +7 days">+7d</button>
          <button className="tl-btn" onClick={() => scrollTo(Math.max(0, px(t0 + 14 * DAY) - 40))} title="Jump to +14 days">+14d</button>
          <button className="tl-btn" onClick={() => scrollTo(Math.max(0, px(t0 + 30 * DAY) - 40))} title="Jump to +30 days">+30d</button>
        </div>
        <div className="tl-nav-scroll">
          <button className="tl-btn arr" onClick={() => scrollBy(-350)} title="Scroll left">◀</button>
          <span className="tl-hint dim">SCROLL TO SEE FUTURE OPS ({Math.round(days)}d)</span>
          <button className="tl-btn arr" onClick={() => scrollBy(350)} title="Scroll right">▶</button>
        </div>
      </div>
      <div className="tl-scroll" ref={scrollRef} onWheel={onWheel}>
        <div className="tl" style={{ width: `${totalWidth}px` }} onMouseMove={e => onScrub?.(tAtPx(getPixel(e)))} onMouseLeave={() => onScrub?.(null)} onClick={e => onScrub?.(tAtPx(getPixel(e)), true)}>
          <div className="tl-axis">
            {scrubX != null && <div className="tl-scrub" style={{ left: `${scrubX}px` }}><span>{scrub! < t0 ? hhmm(scrub!) : scrub! < t0 + 2 * DAY ? `+${Math.round((scrub! - t0) / HOUR)}h` : new Date(scrub!).toUTCString().slice(5, 11)}</span></div>}
            <div className="tl-back" style={{ left: 0, width: `${wBack}px` }}><span>{snap.watch ? `${snap.watch.name.toUpperCase()} WATCH SO FAR` : 'SO FAR'} · {log.length} logged</span></div>
            {ticks.map(k => <div key={k.t} className={`tl-tick ${k.major ? 'major' : ''}`} style={{ left: `${px(k.t)}px` }}>{k.label && <span>{k.label}</span>}</div>)}
            <div className="tl-now" style={{ left: `${wBack}px` }}><span>NOW {hhmm(t0)}</span></div>
            <div className="tl-near" style={{ left: `${wBack + wNear}px` }}><span>+48h</span></div>
            <div className="tl-horizon" style={{ left: `${totalWidth - 90}px` }}><span>{Math.round(days)} days</span></div>
          </div>
          <div className="tl-log" style={{ width: `${wBack}px` }}>
            {log.map(e => { const s = subjectSelection(snap, e.subject); return <i key={e.id} className={`tl-ev b-${e.bucket} ${s ? 'jump' : ''}`} style={{ left: `${(px(+new Date(e.at)) / Math.max(1, wBack)) * 100}%`, background: BUCKET_COLOR[e.bucket] ?? BUCKET_COLOR.other }} title={`${hhmm(+new Date(e.at))} · ${BUCKET_LABEL[e.bucket] ?? e.bucket} · ${e.summary ?? e.type} — ${e.actor}`} onClick={() => s && onSelect(s)} /> })}
            {log.length === 0 && <span className="tl-quiet dim">nothing logged this watch</span>}
          </div>
          <div className="tl-body" style={{ height: `${Math.max(2, lanes.length) * 20 + 4}px` }}>
            <div className="tl-past" style={{ left: 0, width: `${wBack}px` }} />
            {watchEnd && watchEnd > t0 && <div className="tl-watch" style={{ left: `${wBack}px`, width: `${Math.max(0, px(watchEnd) - wBack)}px` }} title={`the ${snap.watch!.name} watch until ${hhmm(watchEnd)}`} />}
            {ticks.filter(k => k.major).map(k => <div key={k.t} className="tl-grid" style={{ left: `${px(k.t)}px` }} />)}
            <div className="tl-grid now" style={{ left: `${wBack}px` }} />
            {eventLanes > 0 && lanes.length > eventLanes && <div className="tl-sep" style={{ top: `${eventLanes * 20 + 2}px` }} />}
            {spans.map(s => { const l = laneOf.get(s.id) ?? 0; const left = px(s.start), right = px(s.end); const w = Math.max(right - left, 18)
              const active = (sel?.type === 'event' && sel.id === s.id) || (sel?.type === 'person' && s.kind === 'trip' && snap.trips.find(t => t.id === s.id)?.person_id === sel.id)
              return <div key={s.id} className={`tl-span ${s.cls} ${active ? 'active' : ''} ${s.start < tBack ? 'started' : ''}`} style={{ left: `${left}px`, width: `${w}px`, top: `${l * 20 + 2}px` }} title={s.title} onClick={() => onSelect(s.sel)}>
                <span className="tl-label">{s.label}</span>
                {s.kind === 'event' && w > 50 && (() => { const e = snap.events.find(v => v.id === s.id)!; return <>{tripsOf(e) > 0 && <i className="tl-flag dim">{tripsOf(e)} TRIPS</i>}{e.coverage && e.coverage.gap > 0 && <i className="tl-flag">COVER {e.coverage.assigned}/{e.coverage.required}</i>}{e.operation && <i className="tl-flag op" onClick={ev => { ev.stopPropagation(); onOp(e.operation!.id) }}>OP {e.operation.tasks_done}/{e.operation.tasks_total}</i>}</> })()}
              </div> })}
            {spans.length === 0 && <div className="dim small" style={{ padding: 8 }}>Nothing planned in the next 90 days.</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
