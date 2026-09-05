import { useEffect, useState } from 'react'
import * as api from './api'
import type { Planning, Role, Selection, Snapshot } from './types'

const DAY = 864e5

type Act = (l: string, f: () => Promise<unknown>) => void
const d = (iso: string) => new Date(iso).toUTCString().slice(5, 11)
const ROLES = ['lead', 'agent', 'advance', 'driver']

/** §6 — the long-range planning view: the next 90 days by week, coverage per event, gaps, and who is already committed. */
export function PlanningPanel({ role, busy, act, onClose, onSelect, reload, snap }: { role: Role; busy: string | null; act: Act; onClose: () => void; onSelect: (s: Selection) => void; reload: number; snap: Snapshot | null }) {
  const [p, setP] = useState<Planning | null>(null)
  const [view, setView] = useState<'weeks' | 'month'>('month')
  const [pick, setPick] = useState<Record<string, { person_id: string; role: string }>>({})
  const load = () => api.getPlanning(90).then(setP).catch(() => setP(null))
  useEffect(() => { load() }, [reload])
  if (!p) return <div className="detail brief plan"><button className="close" onClick={onClose}>×</button><div className="loading-inline">Loading…</div></div>
  const can = role === 'battle_captain' || role === 'security'
  return (
    <div className="detail brief plan" onClick={e => e.stopPropagation()}>
      <button className="close" onClick={onClose}>×</button>
      <div className="d-kicker">S3 · LONG-RANGE PLANNING · next 90 days</div>
      <div className="d-title">{p.summary.events} events · {p.summary.trips} trips · <span className={p.summary.events_with_gaps ? 'bad' : 'ok'}>{p.summary.events_with_gaps} with coverage gaps</span> · {p.summary.security_available} security available</div>
      <div className="row-btns" style={{ margin: '6px 0' }}>{(['month', 'weeks'] as const).map(v => <button key={v} className={`chip btn ${view === v ? 'on' : ''}`} onClick={() => setView(v)}>{v.toUpperCase()}</button>)}<span className="dim small">month: the calendar for the planning meeting · weeks: coverage assignments</span></div>
      {view === 'month' && snap && <MonthGrid snap={snap} onSelect={onSelect} />}
      {p.gaps.length > 0 && <div className="gaps"><div className="gaps-head">COVERAGE GAPS</div>{p.gaps.map(g => <div key={g.event_id} className="gap" onClick={() => onSelect({ type: 'event', id: g.event_id })} style={{ cursor: 'pointer' }}><span className="gap-n">{g.gap}</span><span className="gap-l">{g.name}</span><span className="gap-rec dim">week of {g.week} · needs {g.required}</span></div>)}</div>}
      {view === 'weeks' && p.weeks.map(w => <div key={w.week} className="pweek">
        <div className="section-label">WEEK OF {new Date(w.week).toUTCString().slice(5, 16).toUpperCase()} <span className="dim">{w.events.length} events · {w.trips.length} trips</span></div>
        {w.events.map(e => { const c = e.coverage; const sel = pick[e.id] ?? { person_id: '', role: 'agent' }
          return <div key={e.id} className="pevent">
            <div className="rq-head" onClick={() => onSelect({ type: 'event', id: e.id })} style={{ cursor: 'pointer' }}>
              <span className="chip event small">{e.status === 'active' ? 'LIVE' : `T-${e.days_until}d`}</span><span className="name">★ {e.name}</span>
              <span className={`chip small ${c.gap > 0 ? 'red' : 'green'}`}>COVER {c.assigned}/{c.required}</span>
              {e.operation && <span className="chip small op">OP {e.operation.tasks_done}/{e.operation.tasks_total}</span>}
              {e.threat_ids_in_area.length > 0 && <span className="tbadge">△{e.threat_ids_in_area.length}</span>}
            </div>
            <div className="rq-when dim">{e.venue_name} · {d(e.start_at)} → {d(e.end_at)} · {e.attendee_count} attending · {e.vip_count} VIP · rule: {c.rule}</div>
            <div className="pcover">{c.people.map(x => <span key={x.person_id} className="chip small green">{x.name} · {x.role}{can && <a onClick={() => act('removing coverage', () => api.removeCoverage(e.id, x.person_id).then(load))} title="remove"> ×</a>}</span>)}
              {can && <span className="row-btns"><select value={sel.person_id} onChange={ev => setPick({ ...pick, [e.id]: { ...sel, person_id: ev.target.value } })}><option value="">assign security…</option>
                {p.security.map(s => <option key={s.id} value={s.id}>{s.name} · {s.team_name}{s.commitments.length ? ` (${s.commitments.length} committed)` : ''}</option>)}</select>
                <select value={sel.role} onChange={ev => setPick({ ...pick, [e.id]: { ...sel, role: ev.target.value } })}>{ROLES.map(r => <option key={r}>{r}</option>)}</select>
                <button className="mini ok" disabled={!!busy || !sel.person_id} onClick={() => act('assigning coverage', () => api.assignCoverage(e.id, sel.person_id, sel.role).then(r => { if (r.overlaps.length) alert('Overlaps: ' + r.overlaps.join(', ')); load() }))}>ASSIGN</button>
                <input type="number" min={0} placeholder={`${c.required}`} style={{ width: 48 }} title="override the required number (Battle Captain)" onKeyDown={ev => { if (ev.key === 'Enter' && role === 'battle_captain') act('setting required coverage', () => api.setRequiredSecurity(e.id, +(ev.target as HTMLInputElement).value).then(load)) }} /></span>}
            </div>
          </div> })}
        {w.trips.map(t => <div key={t.id} className="ptrip dim">{t.is_vip ? '★ ' : ''}{t.person_name} → {t.dest_name} · {d(t.depart_at)}–{d(t.return_at)} · {t.purpose}{t.event_id ? ' · event' : ''}</div>)}
      </div>)}
    </div>)
}

/** §13 — paste an export: HRIS CSV, schedule CSV, travel CSV, or a calendar ICS. */
export function ImportDrawer({ busy, act, onDone }: { busy: string | null; act: Act; onDone: () => void }) {
  const [kind, setKind] = useState<'people' | 'shifts' | 'trips' | 'ics'>('people')
  const [text, setText] = useState('')
  const [result, setResult] = useState<import('./types').ImportResult | null>(null)
  const hint: Record<string, string> = { people: 'id,name,role,team_name,is_vip,phone,email', shifts: 'email,on_shift,shift_role', trips: 'email,origin_location_id,dest_location_id,dest_name,dest_lat,dest_lon,depart_at,return_at,purpose,booking_ref', ics: 'BEGIN:VCALENDAR … an export from Google/Outlook/Apple Calendar' }
  return (
    <div className="dform">
      <div className="dform-head">IMPORT <span className="dim">exports from the systems of record · rows carry their provenance</span></div>
      <div className="row-btns"><select value={kind} onChange={e => { setKind(e.target.value as typeof kind); setResult(null) }}><option value="people">People (HRIS CSV)</option><option value="shifts">Shifts (schedule CSV)</option><option value="trips">Trips (travel CSV)</option><option value="ics">Events (calendar ICS)</option></select></div>
      <textarea rows={5} placeholder={hint[kind]} value={text} onChange={e => setText(e.target.value)} />
      {result && <div className="small" style={{ color: result.errors.length ? 'var(--amber)' : 'var(--green)' }}>{Object.entries(result).filter(([k, v]) => typeof v === 'number').map(([k, v]) => `${k} ${v}`).join(' · ')}{result.errors.map((e, i) => <div key={i} className="dim">{e}</div>)}</div>}
      <div className="row-btns"><button className="mini ok" disabled={!!busy || text.trim().length < 5} onClick={() => act('importing', () => api.importText(kind, text).then(setResult))}>IMPORT</button><button className="mini" onClick={onDone}>CLOSE</button></div>
    </div>)
}


/** The month grid: weeks as rows, days as cells, events as spans across the cells with their coverage, trips as thin
 * lines. Three months from today, for the planning meeting rather than the shift. */
function MonthGrid({ snap, onSelect }: { snap: Snapshot; onSelect: (s: Selection) => void }) {
  const today = new Date(); today.setUTCHours(0, 0, 0, 0)
  const months: Date[] = [0, 1, 2].map(i => new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth() + i, 1)))
  type Item = { id: string; kind: 'event' | 'trip'; label: string; start: Date; end: Date; sel: Selection; cls: string; title: string }
  const items: Item[] = [
    ...snap.events.map(e => ({ id: e.id, kind: 'event' as const, label: `★ ${e.name}${e.coverage ? ` · ${e.coverage.assigned}/${e.coverage.required}` : ''}`, start: day(e.start_at), end: day(e.end_at), sel: { type: 'event', id: e.id } as Selection,
      cls: `ev ${e.coverage && e.coverage.gap > 0 ? 'gap' : ''}`, title: `${e.name} · ${e.venue_name}` + (e.coverage ? ` · cover ${e.coverage.assigned}/${e.coverage.required}` : '') })),
    ...snap.trips.filter(t => !t.event_id).map(t => ({ id: t.id, kind: 'trip' as const, label: `${t.is_vip ? '★ ' : ''}${t.person_name.split(' ')[0]} → ${t.dest_name.split(',')[0]}`, start: day(t.depart_at), end: day(t.return_at), sel: { type: 'person', id: t.person_id } as Selection, cls: `tr ${t.is_vip ? 'vip' : ''}`, title: `${t.person_name} → ${t.dest_name} · ${t.purpose}` })),
  ]
  return (<div className="mgrid">
    {months.map(m0 => {
      const first = new Date(m0); const offset = (first.getUTCDay() + 6) % 7  // Monday first
      const gridStart = new Date(+first - offset * DAY)
      const daysInMonth = new Date(Date.UTC(m0.getUTCFullYear(), m0.getUTCMonth() + 1, 0)).getUTCDate()
      const rows = Math.ceil((offset + daysInMonth) / 7)
      return <div key={+m0} className="month">
        <div className="mhead">{m0.toLocaleString('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' }).toUpperCase()}</div>
        <div className="mdays">{['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'].map(d => <span key={d}>{d}</span>)}</div>
        {Array.from({ length: rows }, (_, r) => {
          const wStart = new Date(+gridStart + r * 7 * DAY), wEnd = new Date(+wStart + 7 * DAY)
          const here = items.filter(i => i.end >= wStart && i.start < wEnd).sort((a, b) => +a.start - +b.start || (a.kind === 'event' ? -1 : 1))
          const lanes: Date[] = []; const laneOf = new Map<string, number>()
          for (const i of here) { let l = lanes.findIndex(e => e <= i.start); if (l < 0) { l = lanes.length; lanes.push(new Date(0)) } lanes[l] = new Date(+i.end + DAY); laneOf.set(i.id, l) }
          return <div key={r} className="mweek" style={{ minHeight: `${34 + lanes.length * 16}px` }}>
            {Array.from({ length: 7 }, (_, c) => { const d = new Date(+wStart + c * DAY); const inMonth = d.getUTCMonth() === m0.getUTCMonth(); const isToday = +d === +today
              return <div key={c} className={`mcell ${inMonth ? '' : 'out'} ${isToday ? 'today' : ''} ${d < today ? 'past' : ''}`}><span className="mnum">{d.getUTCDate()}</span></div> })}
            {here.map(i => { const s = Math.max(0, Math.round((+i.start - +wStart) / DAY)), e = Math.min(7, Math.round((+i.end - +wStart) / DAY) + 1)
              return <div key={i.id} className={`mspan ${i.cls} ${i.start < wStart ? 'cont' : ''} ${i.end >= wEnd ? 'more' : ''}`} style={{ left: `${(s / 7) * 100}%`, width: `${((e - s) / 7) * 100}%`, top: `${22 + (laneOf.get(i.id) ?? 0) * 16}px` }} title={i.title} onClick={() => onSelect(i.sel)}>{i.label}</div> })}
          </div> })}
      </div> })}
  </div>)
}
function day(iso: string) { const d = new Date(iso); d.setUTCHours(0, 0, 0, 0); return d }
