// §3.3 S3 as time, through NOW. The left of the strip is this watch so far — every logged event since the watch began,
// drawn as ticks in the lanes the brief uses; the right is the horizon, compressed: the next two days get room, the
// rest of the 90 days is squeezed so a summit in five weeks is still on the board. Spans that began before now cross the
// NOW line. The handover brief's "significant events this shift" is this left half, read out.
import type { CopEvent, Selection, Snapshot, Trip, WatchLogEntry } from './types'

const LEG_ICON: Record<string, string> = { flight: '✈', ground: '🚗', lodging: '🏨' }
const DAY = 864e5, HOUR = 36e5
const MIN_DAYS = 21, MAX_DAYS = 90  // the horizon runs to the last planned thing (at least three weeks, at most 90 days)
const LEFT = 24, NEAR = 24          // percent of the width for the watch so far, and for the next 48 hours
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

export function Timeline({ snap, now, sel, onSelect, onOp }: { snap: Snapshot | null; now: number; sel: Selection; onSelect: (s: Selection) => void; onOp: (id: string) => void }) {
  if (!snap) return <div className="tl" />
  const t0 = now
  const watchStart = snap.watch ? +new Date(snap.watch.started_at) : t0 - 8 * HOUR
  const tBack = Math.min(watchStart, t0 - HOUR)   // never a zero-width left half at the top of a watch
  const lastEnd = Math.max(...snap.events.map(e => +new Date(e.end_at)), ...snap.trips.filter(t => !t.event_id).map(t => +new Date(t.return_at)), t0 + MIN_DAYS * DAY)
  const tFar = Math.min(t0 + MAX_DAYS * DAY, lastEnd + 2 * DAY)
  const tNear = Math.min(t0 + NEAR_H * HOUR, tFar)
  const days = (tFar - t0) / DAY
  // the piecewise scale: [tBack, now] → 0..LEFT · [now, +48h] → LEFT..LEFT+NEAR · [+48h, tFar] → the rest
  const x = (t: number): number => {
    const c = Math.max(tBack, Math.min(tFar, t))
    if (c <= t0) return (LEFT * (c - tBack)) / (t0 - tBack)
    if (c <= tNear) return LEFT + (NEAR * (c - t0)) / Math.max(1, tNear - t0)
    return LEFT + NEAR + ((100 - LEFT - NEAR) * (c - tNear)) / Math.max(1, tFar - tNear)
  }
  const tripsOf = (e: CopEvent) => snap.trips.filter(t => t.event_id === e.id).length
  const spans: Span[] = [
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
  const watchEnd = snap.watch ? +new Date(snap.watch.ends_at) : null
  // ticks: hours on the left, hours through the near horizon, days beyond
  const ticks: { t: number; label: string; major: boolean }[] = []
  const backH = (t0 - tBack) / HOUR
  const hourEvery = backH <= 4 ? 1 : backH <= 9 ? 2 : backH <= 14 ? 3 : 4
  for (let h = Math.ceil((tBack - Math.floor(tBack / HOUR) * HOUR) / HOUR), t = Math.ceil(tBack / HOUR) * HOUR; t < t0; t += HOUR, h++) { const hr = new Date(t).getUTCHours(); ticks.push({ t, label: hr % hourEvery === 0 ? hhmm(t) : '', major: hr % (hourEvery * 2) === 0 }) }
  for (let h = 6; h <= NEAR_H && t0 + h * HOUR < tFar; h += 6) ticks.push({ t: t0 + h * HOUR, label: h % 12 === 0 ? `+${h}h` : '', major: h % 24 === 0 })
  const labelEvery = days <= 28 ? 2 : days <= 56 ? 7 : 14
  for (let d = 3; d <= days; d += 1) { const t = t0 + d * DAY; ticks.push({ t, label: d % labelEvery === 0 ? new Date(t).toUTCString().slice(5, 11) : '', major: d % 7 === 0 }) }
  const eventLanes = lanes.filter(l => l.kind === 'event').length
  // this watch so far: the log as ticks, one lane, bucket-colored; the summary on hover; the subject on click
  const log: WatchLogEntry[] = (snap.watch_log ?? []).filter(e => +new Date(e.at) >= tBack)
  return (
    <div className="tl" title="">
      <div className="tl-axis">
        <div className="tl-back" style={{ left: 0, width: `${LEFT}%` }}><span>{snap.watch ? `${snap.watch.name.toUpperCase()} WATCH SO FAR` : 'SO FAR'} · {log.length} logged</span></div>
        {ticks.map(k => <div key={k.t} className={`tl-tick ${k.major ? 'major' : ''}`} style={{ left: `${x(k.t)}%` }}>{k.label && <span>{k.label}</span>}</div>)}
        <div className="tl-now" style={{ left: `${LEFT}%` }}><span>NOW {hhmm(t0)}</span></div>
        <div className="tl-near" style={{ left: `${LEFT + NEAR}%` }}><span>+48h</span></div>
        <div className="tl-horizon"><span>{Math.round(days)} days</span></div>
      </div>
      <div className="tl-log" style={{ width: `${LEFT}%` }}>
        {log.map(e => { const s = subjectSelection(snap, e.subject); return <i key={e.id} className={`tl-ev b-${e.bucket} ${s ? 'jump' : ''}`} style={{ left: `${(x(+new Date(e.at)) / LEFT) * 100}%`, background: BUCKET_COLOR[e.bucket] ?? BUCKET_COLOR.other }} title={`${hhmm(+new Date(e.at))} · ${BUCKET_LABEL[e.bucket] ?? e.bucket} · ${e.summary ?? e.type} — ${e.actor}`} onClick={() => s && onSelect(s)} /> })}
        {log.length === 0 && <span className="tl-quiet dim">nothing logged this watch</span>}
      </div>
      <div className="tl-body" style={{ height: `${Math.max(2, lanes.length) * 20 + 4}px` }}>
        <div className="tl-past" style={{ left: 0, width: `${LEFT}%` }} />
        {watchEnd && watchEnd > t0 && <div className="tl-watch" style={{ left: `${LEFT}%`, width: `${x(watchEnd) - LEFT}%` }} title={`the ${snap.watch!.name} watch until ${hhmm(watchEnd)}`} />}
        {ticks.filter(k => k.major).map(k => <div key={k.t} className="tl-grid" style={{ left: `${x(k.t)}%` }} />)}
        <div className="tl-grid now" style={{ left: `${LEFT}%` }} />
        {eventLanes > 0 && lanes.length > eventLanes && <div className="tl-sep" style={{ top: `${eventLanes * 20 + 2}px` }} />}
        {spans.map(s => { const l = laneOf.get(s.id) ?? 0; const left = x(s.start), right = x(s.end); const w = Math.max(right - left, 0.6)
          const active = (sel?.type === 'event' && sel.id === s.id) || (sel?.type === 'person' && s.kind === 'trip' && snap.trips.find(t => t.id === s.id)?.person_id === sel.id)
          return <div key={s.id} className={`tl-span ${s.cls} ${active ? 'active' : ''} ${s.start < tBack ? 'started' : ''}`} style={{ left: `${left}%`, width: `${w}%`, top: `${l * 20 + 2}px` }} title={s.title} onClick={() => onSelect(s.sel)}>
            <span className="tl-label">{s.label}</span>
            {s.kind === 'event' && w > 7 && (() => { const e = snap.events.find(v => v.id === s.id)!; return <>{tripsOf(e) > 0 && <i className="tl-flag dim">{tripsOf(e)} TRIPS</i>}{e.coverage && e.coverage.gap > 0 && <i className="tl-flag">COVER {e.coverage.assigned}/{e.coverage.required}</i>}{e.operation && <i className="tl-flag op" onClick={ev => { ev.stopPropagation(); onOp(e.operation!.id) }}>OP {e.operation.tasks_done}/{e.operation.tasks_total}</i>}</> })()}
          </div> })}
        {spans.length === 0 && <div className="dim small" style={{ padding: 8 }}>Nothing planned in the next 90 days.</div>}
      </div>
    </div>)
}
