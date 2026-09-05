const LEG_ICON: Record<string, string> = { flight: '✈', ground: '🚗', lodging: '🏨' }
import type { CopEvent, Selection, Snapshot, Trip } from './types'

const DAY = 864e5
const MIN_DAYS = 21, MAX_DAYS = 90  // one linear scale from now to the last planned thing (at least three weeks, at most 90 days)

type Span = { id: string; kind: 'event' | 'trip'; label: string; sub: string; start: number; end: number; sel: Selection; cls: string; title: string }

/** S3 as time, not cards: now at the left, the watch shaded, events and trips as spans against the next 90 days. */
export function Timeline({ snap, now, sel, onSelect, onOp }: { snap: Snapshot | null; now: number; sel: Selection; onSelect: (s: Selection) => void; onOp: (id: string) => void }) {
  if (!snap) return <div className="tl" />
  const t0 = now
  const lastEnd = Math.max(...snap.events.map(e => +new Date(e.end_at)), ...snap.trips.filter(t => !t.event_id).map(t => +new Date(t.return_at)), t0 + MIN_DAYS * DAY)
  const tFar = Math.min(t0 + MAX_DAYS * DAY, lastEnd + 2 * DAY)
  const days = (tFar - t0) / DAY
  const x = (t: number) => ((Math.max(t0, Math.min(tFar, t)) - t0) / (tFar - t0)) * 100
  const tripsOf = (e: CopEvent) => snap.trips.filter(t => t.event_id === e.id).length
  const spans: Span[] = [
    ...snap.events.map((e: CopEvent): Span => ({ id: e.id, kind: 'event', label: `★ ${e.name}`, sub: e.venue_name, start: +new Date(e.start_at), end: +new Date(e.end_at), sel: { type: 'event', id: e.id },
      cls: `ev ${e.status === 'active' ? 'live' : ''} ${e.coverage && e.coverage.gap > 0 ? 'gap' : ''} ${e.threat_ids_in_area.length ? 'threat' : ''}`,
      title: `${e.name} · ${e.venue_name} · ${e.attendee_count} attending · ${e.vip_count} VIP · ${tripsOf(e)} trips` + (e.coverage ? ` · cover ${e.coverage.assigned}/${e.coverage.required}` : '') + (e.operation ? ` · OP ${e.operation.tasks_done}/${e.operation.tasks_total}` : '') })),
    // trips an event generated are the event; they fold into its span
    ...snap.trips.filter(t => !t.event_id).map((t: Trip): Span => ({ id: t.id, kind: 'trip', label: `${t.is_vip ? '★ ' : ''}${t.person_short ?? t.person_name.split(' ')[0]} → ${t.dest_name.split(',')[0]}`, sub: t.current_leg ? `${LEG_ICON[t.current_leg.kind]} ${t.current_leg.label || t.current_leg.to_name}` : t.purpose, start: +new Date(t.depart_at), end: +new Date(t.return_at), sel: { type: 'person', id: t.person_id },
      cls: `tr ${t.status} ${t.is_vip ? 'vip' : ''}`, title: `${t.person_name} · ${t.origin_name} → ${t.dest_name} · ${t.purpose}` })),
  ].filter(s => s.end >= t0 && s.start <= tFar).sort((a, b) => a.start - b.start)
  // lanes: events on top, trips beneath; a span takes the first lane whose last span has ended
  const lanes: { kind: 'event' | 'trip'; ends: number[] }[] = []
  const laneOf = new Map<string, number>()
  for (const kind of ['event', 'trip'] as const) {
    const pool = spans.filter(s => s.kind === kind)
    const ends: number[] = []
    for (const s of pool) { let i = ends.findIndex(e => e <= s.start); if (i < 0) { i = ends.length; ends.push(0) } ends[i] = s.end + DAY * 0.4; laneOf.set(s.id, lanes.length + i) }
    for (const e of ends) lanes.push({ kind, ends: [e] })
  }
  const watchEnd = snap.watch ? +new Date(snap.watch.ends_at) : null
  const ticks: { t: number; label: string; major: boolean }[] = []
  const labelEvery = days <= 28 ? 2 : days <= 56 ? 7 : 14
  for (let d = 1; d <= days; d += 1) { const t = t0 + d * DAY; const major = d % 7 === 0; ticks.push({ t, label: d % labelEvery === 0 ? new Date(t).toUTCString().slice(5, 11) : '', major }) }
  const eventLanes = lanes.filter(l => l.kind === 'event').length
  return (
    <div className="tl" title="">
      <div className="tl-axis">
        {ticks.map(k => <div key={k.t} className={`tl-tick ${k.major ? 'major' : ''}`} style={{ left: `${x(k.t)}%` }}>{k.label && <span>{k.label}</span>}</div>)}
        <div className="tl-now" style={{ left: 0 }}><span>NOW</span></div>
        <div className="tl-horizon"><span>{Math.round(days)} days</span></div>
      </div>
      <div className="tl-body" style={{ height: `${Math.max(2, lanes.length) * 20 + 4}px` }}>
        {watchEnd && watchEnd > t0 && <div className="tl-watch" style={{ left: 0, width: `${x(watchEnd)}%` }} title={`the ${snap.watch!.name} watch until ${new Date(watchEnd).toUTCString().slice(17, 22)}Z`} />}
        {ticks.filter(k => k.major).map(k => <div key={k.t} className="tl-grid" style={{ left: `${x(k.t)}%` }} />)}
        {eventLanes > 0 && lanes.length > eventLanes && <div className="tl-sep" style={{ top: `${eventLanes * 20 + 2}px` }} />}
        {spans.map(s => { const l = laneOf.get(s.id) ?? 0; const left = x(s.start), right = x(s.end); const w = Math.max(right - left, 0.6)
          const active = (sel?.type === 'event' && sel.id === s.id) || (sel?.type === 'person' && s.kind === 'trip' && snap.trips.find(t => t.id === s.id)?.person_id === sel.id)
          return <div key={s.id} className={`tl-span ${s.cls} ${active ? 'active' : ''} ${s.start < t0 ? 'started' : ''}`} style={{ left: `${left}%`, width: `${w}%`, top: `${l * 20 + 2}px` }} title={s.title} onClick={() => onSelect(s.sel)}>
            <span className="tl-label">{s.label}</span>
            {s.kind === 'event' && w > 7 && (() => { const e = snap.events.find(v => v.id === s.id)!; return <>{tripsOf(e) > 0 && <i className="tl-flag dim">{tripsOf(e)} TRIPS</i>}{e.coverage && e.coverage.gap > 0 && <i className="tl-flag">COVER {e.coverage.assigned}/{e.coverage.required}</i>}{e.operation && <i className="tl-flag op" onClick={ev => { ev.stopPropagation(); onOp(e.operation!.id) }}>OP {e.operation.tasks_done}/{e.operation.tasks_total}</i>}</> })()}
          </div> })}
        {spans.length === 0 && <div className="dim small" style={{ padding: 8 }}>Nothing planned in the next 90 days.</div>}
      </div>
    </div>)
}
