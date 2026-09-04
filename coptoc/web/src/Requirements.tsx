import { useEffect, useState } from 'react'
import * as api from './api'
import type { AreaAssessment, Coverage, Plan, Requirement, Selection, SourceInfo } from './types'

const rel = (iso: string | null) => { if (!iso) return ''; const d = (new Date(iso).getTime() - Date.now()) / 864e5; return d < 0 ? `${Math.round(-d)}d ago` : `in ${Math.round(d)}d` }

/** §5.2–5.3 — the S2 requirements list with coverage bars, the plan for one, and the four-field directed form. */
export function RequirementsPanel({ reload, busy, act, onSelect, role, onArea }: { reload: number; busy: string | null; act: (l: string, f: () => Promise<unknown>) => void; onSelect: (s: Selection) => void; role: string; onArea: (id: string) => void }) {
  const [reqs, setReqs] = useState<Requirement[]>([])
  const [cov, setCov] = useState<Coverage | null>(null)
  const [open, setOpen] = useState<string | null>(null)
  const [plan, setPlan] = useState<Plan | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [showSources, setShowSources] = useState(false)
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const [areas, setAreas] = useState<AreaAssessment[]>([])
  useEffect(() => { api.listRequirements().then(setReqs).catch(() => {}); api.getCoverage().then(setCov).catch(() => {}); api.listAreas().then(setAreas).catch(() => setAreas([])) }, [reload])
  useEffect(() => { if (open) api.getPlan(open).then(setPlan).catch(() => setPlan(null)); else setPlan(null) }, [open, reload])
  const canCreate = ['battle_captain', 'security', 'analyst', 'ea'].includes(role)
  const canAssess = ['battle_captain', 'analyst'].includes(role)
  const pick = (id: string) => setPicked(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n })
  const flyTo = (r: Requirement) => { if (r.subject_type === 'trip' && r.subject_id) { /* trip → its person is what the wall selects */ } onSelect(r.subject_type === 'location' ? { type: 'location', id: r.subject_id! } : r.subject_type === 'event' ? { type: 'event', id: r.subject_id! } : null) }
  return (<>
    <div className="section-label">REQUIREMENTS <span className="dim">{reqs.length} active · {cov ? `${cov.avg_coverage_pct}% avg coverage` : ''}</span>
      <span className="btns">
        {canAssess && picked.size > 0 && <button className="mini ok" disabled={!!busy} onClick={() => act('drafting area assessment', () => api.draftArea([...picked]).then(a => { setPicked(new Set()); onArea(a.id) }))}>ASSESS {picked.size}</button>}
        {canCreate && <button className="mini" onClick={() => setShowForm(v => !v)}>+ DIRECTED</button>}
        <button className="mini" onClick={() => setShowSources(v => !v)}>SOURCES</button></span></div>
    {showForm && <DirectedForm busy={busy} act={act} onDone={() => setShowForm(false)} />}
    {showSources && <SourcesDrawer busy={busy} act={act} reload={reload} />}
    {cov && cov.gaps.length > 0 && <div className="gaps">
      <div className="gaps-head">COLLECTION GAPS <span className="dim">{cov.fully_covered}/{cov.requirements} fully covered</span></div>
      {cov.gaps.slice(0, 4).map(g => <div key={g.indicator} className="gap"><span className="gap-n">{g.requirements_affected}</span> <span className="gap-l">{g.label}</span>
        <span className="gap-rec dim">→ {g.recommended_sources.slice(0, 3).map(s => s.name).join(' · ')}</span></div>)}
    </div>}
    {areas.length > 0 && <div className="gaps">
      <div className="gaps-head">AREA ASSESSMENTS <span className="dim">{areas.length}</span></div>
      {areas.slice(0, 4).map(a => <div key={a.id} className="gap" onClick={() => onArea(a.id)} style={{ cursor: 'pointer' }}><span className={`chip small ${a.status}`}>{a.status.toUpperCase()}</span> <span className="gap-l">{(a.places ?? []).join(' vs ')}</span><span className="gap-rec dim">{a.created_at.slice(5, 16).replace('T', ' ')}Z</span></div>)}
    </div>}
    <ul className="list">
      {reqs.map(r => (
        <li key={r.id} className={`row reqrow ${open === r.id ? 'active' : ''}`} onClick={() => { setOpen(open === r.id ? null : r.id); flyTo(r) }}>
          <div className="rq-head">
            {r.kind === 'directed' && canAssess && <input type="checkbox" className="pick" checked={picked.has(r.id)} onClick={e => e.stopPropagation()} onChange={() => pick(r.id)} title="compare in an Area Assessment" />}
            <span className={`prio p${r.priority}`}>P{r.priority}</span>
            <span className={`chip small ${r.kind}`}>{r.kind === 'directed' ? 'DIRECTED' : r.subject_type.toUpperCase()}</span>
            <span className="name">{r.subject_name}</span>
            <span className={`covpct ${r.coverage.pct === 100 ? 'ok' : r.coverage.pct === 0 ? 'bad' : ''}`}>{r.coverage.covered}/{r.coverage.total}</span>
          </div>
          <div className="bar"><span style={{ width: `${r.coverage.pct}%` }} className={r.coverage.pct === 100 ? 'ok' : 'amber'} /></div>
          {r.window_to && <div className="rq-when dim">{rel(r.window_from)} → {rel(r.window_to)}{r.kind === 'directed' && ` · ${r.owner}`}</div>}
          {open === r.id && plan && <div className="plan" onClick={e => e.stopPropagation()}>
            <div className="q">{r.question}</div>
            {plan.indicators.map(i => <div key={i.indicator} className={`pline ${i.covered ? 'ok' : 'gap'}`}>
              <span className="mark">{i.covered ? '✓' : '✗'}</span><span className="lbl">{i.label}</span>
              <span className="src dim">{i.covered ? i.sources.map(s => `${s.name} (${s.reliability})`).join(', ') : `→ ${i.recommended.slice(0, 2).map(s => s.name).join(' · ')}`}</span></div>)}
            <div className="row-btns">{r.status === 'active' && <button className="mini" disabled={!!busy} onClick={() => act('answering requirement', () => api.updateRequirement(r.id, { status: 'answered' }))}>MARK ANSWERED</button>}</div>
          </div>}
        </li>))}
    </ul>
  </>)
}

function DirectedForm({ busy, act, onDone }: { busy: string | null; act: (l: string, f: () => Promise<unknown>) => void; onDone: () => void }) {
  const [f, setF] = useState({ place: '', lat: '', lon: '', from: '', to: '', purpose: 'candidate offsite venue', priority: 2 })
  const ok = f.place && f.lat && f.lon
  return (
    <div className="dform">
      <div className="dform-head">DIRECTED REQUIREMENT <span className="dim">place · window · purpose · priority</span></div>
      <input placeholder="Place (e.g. Lisbon, Portugal)" value={f.place} onChange={e => setF({ ...f, place: e.target.value })} />
      <div className="two"><input placeholder="lat" value={f.lat} onChange={e => setF({ ...f, lat: e.target.value })} /><input placeholder="lon" value={f.lon} onChange={e => setF({ ...f, lon: e.target.value })} /></div>
      <div className="two"><input type="date" value={f.from} onChange={e => setF({ ...f, from: e.target.value })} /><input type="date" value={f.to} onChange={e => setF({ ...f, to: e.target.value })} /></div>
      <input placeholder="Purpose" value={f.purpose} onChange={e => setF({ ...f, purpose: e.target.value })} />
      <div className="row-btns"><select value={f.priority} onChange={e => setF({ ...f, priority: +e.target.value })}><option value={1}>P1</option><option value={2}>P2</option><option value={3}>P3</option></select>
        <button className="mini ok" disabled={!!busy || !ok} onClick={() => { act('creating requirement', () => api.createDirected({ place: f.place, lat: +f.lat, lon: +f.lon, window_from: f.from ? new Date(f.from).toISOString() : undefined, window_to: f.to ? new Date(f.to + 'T23:59:59').toISOString() : undefined, purpose: f.purpose, priority: f.priority })); onDone() }}>CREATE</button>
        <button className="mini" onClick={onDone}>CANCEL</button></div>
    </div>)
}

function SourcesDrawer({ busy, act, reload }: { busy: string | null; act: (l: string, f: () => Promise<unknown>) => void; reload: number }) {
  const [src, setSrc] = useState<SourceInfo[]>([])
  useEffect(() => { api.listSources().then(setSrc).catch(() => {}) }, [reload])
  return (
    <div className="sources">
      <div className="dform-head">SOURCES <span className="dim">operator-adjustable · reliability is yours to grade</span></div>
      {src.map(s => <div key={s.id} className={`srow ${s.configured ? 'live' : s.built ? 'unkeyed' : 'unbuilt'}`}>
        <input type="checkbox" checked={s.enabled} disabled={!!busy} onChange={e => act('updating source', () => api.updateSource(s.id, { enabled: e.target.checked }))} title="enabled" />
        <span className="sname">{s.name}</span>
        <span className={`chip small ${s.configured ? 'live' : ''}`}>{s.configured ? 'LIVE' : s.built ? 'NO KEY' : 'NOT BUILT'}</span>
        <select value={s.reliability} disabled={!!busy} onChange={e => act('grading source', () => api.updateSource(s.id, { reliability: e.target.value }))} title="source reliability (Admiralty A–F)">{['A', 'B', 'C', 'D', 'E', 'F'].map(g => <option key={g}>{g}</option>)}</select>
        <select value={s.cadence} disabled={!!busy} onChange={e => act('setting cadence', () => api.updateSource(s.id, { cadence: e.target.value }))} title="collection cadence">{s.cadences.map(c => <option key={c}>{c}</option>)}</select>
        <span className="dim small">{s.access}</span></div>)}
    </div>)
}
