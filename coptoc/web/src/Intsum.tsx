import { useEffect, useState } from 'react'
import * as api from './api'
import type { Intsum, IntsumHead, LogEv, Role } from './types'

type Act = (l: string, f: () => Promise<unknown>) => void
const hhmm = (iso: string) => new Date(iso).toUTCString().slice(5, 22) + 'Z'
const Ev = ({ e }: { e: LogEv }) => <li><span className="dim">{hhmm(e.at).slice(12)}</span> {e.summary}</li>

/** §5.6 — the INTSUM: a diff since the last one in fixed order; drafted at the fixed hour, released by the Battle Captain (Decision G). */
export function IntsumPanel({ role, busy, act, onClose, reload }: { role: Role; busy: string | null; act: Act; onClose: () => void; reload: number }) {
  const [list, setList] = useState<IntsumHead[]>([])
  const [d, setD] = useState<Intsum | null>(null)
  const [id, setId] = useState<string | null>(null)
  const [notes, setNotes] = useState('')
  useEffect(() => { api.listIntsums().then(l => { setList(l); if (!id && l[0]) setId(l[0].id) }).catch(() => setList([])) }, [reload])
  useEffect(() => { if (id) api.getIntsum(id).then(setD).catch(() => setD(null)) }, [id, reload])
  const isBC = role === 'battle_captain', canDraft = isBC || role === 'analyst'
  return (
    <div className="detail brief intsum" onClick={e => e.stopPropagation()}>
      <button className="close" onClick={onClose}>×</button>
      <div className="d-kicker">INTSUM · DAILY · {d ? <span className={`chip small ${d.status === 'released' ? 'approved' : 'draft'}`}>{d.status.toUpperCase()}</span> : ''}
        {canDraft && <button className="mini" style={{ marginLeft: 8 }} disabled={!!busy} onClick={() => act('drafting INTSUM', () => api.draftIntsum().then(x => { setId(x.id); setD(x) }))}>DRAFT NOW</button>}</div>
      {list.length > 1 && <div className="dim small">{list.slice(0, 7).map(h => <span key={h.id} className={`chip btn small ${h.id === id ? 'on' : ''}`} onClick={() => setId(h.id)} style={{ marginRight: 4 }}>{h.period.to.slice(5, 16).replace('T', ' ')}Z {h.status === 'released' ? '✓' : '·'}</span>)}</div>}
      {!d && <div className="dim small" style={{ marginTop: 8 }}>No INTSUM yet. One drafts itself at the fixed hour; the analyst or Battle Captain can draft now.</div>}
      {d && <>
        <div className="d-title">{hhmm(d.period.from)} → {hhmm(d.period.to)} <span className="dim small">· {d.period.hours} h · {d.event_count} ledger events</span></div>
        <div className={`bluf ${d.nstr ? 'nstr' : ''}`}>{d.headline}</div>

        <div className="section-label">1 · REQUIREMENTS <span className="dim">{d.requirements.active} active · {d.requirements.standing} standing · {d.requirements.directed} directed</span></div>
        <ul>{d.requirements.created.map(e => <Ev key={e.id} e={e} />)}{d.requirements.expired.map(x => <li key={x.id}><span className="dim">expired</span> {x.subject}</li>)}{d.requirements.answered.map(x => <li key={x.id}><span className="dim">answered</span> {x.subject}</li>)}
          {d.requirements.created.length + d.requirements.expired.length + d.requirements.answered.length === 0 && <li className="dim">No change.</li>}</ul>

        <div className="section-label">2 · NEW THREATS <span className="dim">{d.new_threats.length}</span></div>
        <ul>{d.new_threats.length === 0 && <li className="dim">None in the period.</li>}
          {d.new_threats.map(t => <li key={t.id}><span className={`sev ${t.severity}`}>{t.severity.slice(0, 3).toUpperCase()}</span> {t.title} <span className="dim">· {t.source}{t.synthetic ? ' · synthetic' : ''}</span>
            {t.requirements.length > 0 && <div className="dim small">→ {t.requirements.map(r => `P${r.priority} ${r.subject}`).join(' · ')}</div>}</li>)}</ul>

        <div className="section-label">3 · THE WALL <span className="dim">{d.wall.links.length} links · {d.wall.posture.length} posture · {d.wall.roll_calls.length} roll calls</span></div>
        <ul>{[...d.wall.posture, ...d.wall.links, ...d.wall.roll_calls].map(e => <Ev key={e.id} e={e} />)}{d.wall.posture.length + d.wall.links.length + d.wall.roll_calls.length === 0 && <li className="dim">No change.</li>}</ul>

        <div className="section-label">4 · ORGANIC REPORTS AND CASES <span className="dim">{d.reports.length} reports · {d.cases.open} open cases · {d.cases.decisions} decisions</span></div>
        <ul>{d.reports.map(r => <li key={r.id}><span className="chip small green">{r.grade}</span> {r.by}{r.place ? ` · ${r.place}` : ''}: {r.text}</li>)}{d.cases.opened.map(e => <Ev key={e.id} e={e} />)}{d.cases.closed.map(e => <Ev key={e.id} e={e} />)}
          {d.reports.length + d.cases.opened.length + d.cases.closed.length === 0 && <li className="dim">None.</li>}</ul>

        <div className="section-label">5 · PRODUCTS <span className="dim">{d.products.pending_area_assessments.length} area assessments pending</span></div>
        <ul>{[...d.products.assessments, ...d.products.area_assessments].map(e => <Ev key={e.id} e={e} />)}{d.products.pending_area_assessments.map(a => <li key={a.id}><span className="dim">{a.status}</span> {a.title}</li>)}
          {d.products.assessments.length + d.products.area_assessments.length + d.products.pending_area_assessments.length === 0 && <li className="dim">None.</li>}</ul>

        <div className="section-label">6 · COLLECTION <span className="dim">{d.collection.sources.length} live sources · {d.collection.gaps.length} gaps</span></div>
        <ul>{d.collection.sources.map(s => <li key={s.id}>{s.name} <span className="dim">· {s.last_collected_at ? `last ${hhmm(s.last_collected_at)}` : 'not yet run'}{s.last_result ? ` · ${s.last_result}` : ''}</span></li>)}
          {d.collection.runs.map(e => <Ev key={e.id} e={e} />)}
          {d.collection.gaps.slice(0, 5).map(g => <li key={g.indicator}><span className="gap-n">{g.requirements_affected}</span> <span className="dim">{g.label}</span></li>)}</ul>

        {d.status === 'released' ? <div className="dim small" style={{ marginTop: 8 }}>Released by {d.released_by} at {d.released_at && hhmm(d.released_at)}{d.notes ? ` — ${d.notes}` : ''}</div>
          : isBC ? <div className="row-btns" style={{ marginTop: 10 }}><input placeholder="Release note (optional)" value={notes} onChange={e => setNotes(e.target.value)} style={{ flex: 1 }} />
            <button className="mini ok" disabled={!!busy} onClick={() => act('releasing INTSUM', () => api.releaseIntsum(d.id, notes || undefined).then(setD))}>RELEASE</button></div>
          : <div className="dim small" style={{ marginTop: 8 }}>Draft — awaiting the Battle Captain's release (Decision G).</div>}
      </>}
    </div>)
}
