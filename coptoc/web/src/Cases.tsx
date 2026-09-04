import { useEffect, useState } from 'react'
import * as api from './api'
import type { Case, CaseDetail, CaseEntity, CaseRel, Evidence, Queue, Role } from './types'

const CASE_OPENERS = ['battle_captain', 'analyst']
const REPORT_FILERS = ['battle_captain', 'security', 'analyst', 'ea', 'ep']
type Act = (l: string, f: () => Promise<unknown>) => void
const when = (iso: string | null) => iso ? new Date(iso).toISOString().slice(5, 16).replace('T', ' ') + 'Z' : ''

/** §5.10 #1–2 and §5.11 — cases that live for months, the SPOTREP form, and the officer's review queue. */
export function CasesPanel({ reload, busy, act, role, onChanged }: { reload: number; busy: string | null; act: Act; role: Role; onChanged: () => void }) {
  const [cases, setCases] = useState<Case[]>([])
  const [open, setOpen] = useState<string | null>(null)
  const [showReport, setShowReport] = useState(false)
  const [showCase, setShowCase] = useState(false)
  useEffect(() => { api.listCases().then(setCases).catch(() => setCases([])) }, [reload, role])
  const pending = cases.reduce((n, c) => n + (c.pending_review ?? 0), 0)
  return (<>
    <div className="section-label">CASES <span className="dim">{cases.filter(c => c.status === 'open').length} open{pending ? ` · ${pending} to review` : ''}</span>
      <span className="btns">
        {REPORT_FILERS.includes(role) && <button className="mini" onClick={() => { setShowReport(v => !v); setShowCase(false) }}>+ SPOTREP</button>}
        {CASE_OPENERS.includes(role) && <button className="mini" onClick={() => { setShowCase(v => !v); setShowReport(false) }}>+ CASE</button>}</span></div>
    {showReport && <ReportForm busy={busy} act={act} cases={cases} role={role} defaultCase={open} onDone={() => { setShowReport(false); onChanged() }} />}
    {showCase && <CaseForm busy={busy} act={act} onDone={() => { setShowCase(false); onChanged() }} />}
    {cases.length === 0 && <div className="dim small" style={{ padding: '4px 14px' }}>{CASE_OPENERS.includes(role) ? 'No cases you can read. Open one, then file reports into it.' : 'No cases readable by this role.'}</div>}
    <ul className="list">
      {cases.map(c => (
        <li key={c.id} className={`row reqrow ${open === c.id ? 'active' : ''}`} onClick={() => setOpen(open === c.id ? null : c.id)}>
          <div className="rq-head">
            <span className={`chip small ${c.kind === 'person' ? 'amber' : ''}`}>{c.kind.toUpperCase()}</span>
            <span className="name">{c.title}</span>
            {c.status === 'closed' ? <span className="chip small dim">CLOSED</span> : (c.pending_review ?? 0) > 0 ? <span className="chip small review">{c.pending_review} TO REVIEW</span> : <span className="chip small green">REVIEWED</span>}
          </div>
          <div className="rq-when dim">{c.entities ?? 0} entities · {c.relationships ?? 0} links · {c.events ?? 0} events · opened {when(c.opened_at)} by {c.opened_by}</div>
          {open === c.id && <CaseView id={c.id} busy={busy} act={act} role={role} reload={reload} onChanged={onChanged} />}
        </li>))}
    </ul>
  </>)
}

function Cite({ ev }: { ev: Evidence[] }) {
  const e = ev[0]
  if (!e) return null
  return <span className="cite dim" title={ev.map(x => `${x.report_id} [${x.reliability}${x.credibility}]: “${x.quote}”`).join('\n')}>[{e.reliability}{e.credibility}] “{e.quote.length > 70 ? e.quote.slice(0, 70) + '…' : e.quote}”{ev.length > 1 && ` +${ev.length - 1}`}</span>
}

/** The review queue is the v1 workbench (§5.11): every suggested fact with its citation, and the three views' findings as sentences. */
function CaseView({ id, busy, act, role, reload, onChanged }: { id: string; busy: string | null; act: Act; role: Role; reload: number; onChanged: () => void }) {
  const [d, setD] = useState<CaseDetail | null>(null)
  const [q, setQ] = useState<Queue | null>(null)
  const [tab, setTab] = useState<'queue' | 'graph' | 'reports'>('queue')
  const [mergeFrom, setMergeFrom] = useState<CaseEntity | null>(null)
  const load = () => { api.getCase(id).then(setD).catch(() => setD(null)); api.getQueue(id).then(setQ).catch(() => setQ(null)) }
  useEffect(load, [id, reload])
  const can = CASE_OPENERS.includes(role)
  const decideThen = (kind: 'entity' | 'relationship' | 'event', item: string, decision: 'confirm' | 'reject') => act(`${decision}ing`, () => api.decide(id, kind, item, decision).then(() => { load(); onChanged() }))
  if (!d) return <div className="plan dim">loading…</div>
  const confirmed = d.graph.entities.filter(e => e.status === 'confirmed')
  const names = Object.fromEntries(d.graph.entities.map(e => [e.id, e.name]))
  return (
    <div className="plan casev" onClick={e => e.stopPropagation()}>
      <div className="tabs">
        {(['queue', 'graph', 'reports'] as const).map(t => <button key={t} className={`chip btn ${tab === t ? 'on' : ''}`} onClick={() => setTab(t)}>{t.toUpperCase()}{t === 'queue' && q ? ` ${q.total}` : ''}</button>)}
        {can && d.status === 'open' && <button className="mini" disabled={!!busy} onClick={() => act('closing case', () => api.closeCase(id).then(onChanged))}>CLOSE CASE</button>}
      </div>
      {tab === 'queue' && q && <>
        {q.total === 0 && <div className="dim small">Nothing waiting. File a SPOTREP into this case and the extraction will suggest what it finds.</div>}
        {q.entities.map(e => <div key={e.id} className="qitem">
          <span className="chip small">{e.type.toUpperCase()}</span><span className="qname">{e.name}</span><Cite ev={e.evidence} />
          {can && <span className="qbtns">
            <button className="mini ok" disabled={!!busy} onClick={() => decideThen('entity', e.id, 'confirm')}>✓</button>
            <button className="mini danger" disabled={!!busy} onClick={() => decideThen('entity', e.id, 'reject')}>✗</button>
            {confirmed.length > 0 && e.type === 'person' && <button className="mini" disabled={!!busy} onClick={() => setMergeFrom(mergeFrom?.id === e.id ? null : e)} title="same person as a confirmed entity (alias)">=</button>}
          </span>}
          {mergeFrom?.id === e.id && <div className="merge">alias of: {confirmed.filter(c => c.type === 'person').map(c => <button key={c.id} className="chip btn" onClick={() => act('merging', () => api.mergeEntity(id, e.id, c.id).then(() => { setMergeFrom(null); load(); onChanged() }))}>{c.name}</button>)}</div>}
        </div>)}
        {q.relationships.map(r => <div key={r.id} className="qitem">
          <span className="chip small">LINK</span><span className="qname">{r.from_name} — {r.type} — {r.to_name}</span><Cite ev={r.evidence} />
          {can && <span className="qbtns"><button className="mini ok" disabled={!!busy} onClick={() => decideThen('relationship', r.id, 'confirm')}>✓</button><button className="mini danger" disabled={!!busy} onClick={() => decideThen('relationship', r.id, 'reject')}>✗</button></span>}
        </div>)}
        {q.events.map(v => <div key={v.id} className="qitem">
          <span className="chip small">EVENT</span><span className="qname">{when(v.at)} {v.place ? `· ${v.place} ` : ''}— {v.summary}</span>
          {can && <span className="qbtns"><button className="mini ok" disabled={!!busy} onClick={() => decideThen('event', v.id, 'confirm')}>✓</button><button className="mini danger" disabled={!!busy} onClick={() => decideThen('event', v.id, 'reject')}>✗</button></span>}
        </div>)}
      </>}
      {tab === 'graph' && <>
        <div className="gaps-head">WHAT THE LINK CHART WOULD SHOW</div>
        {d.analysis.links.length === 0 && <div className="dim small">No links yet.</div>}
        {d.analysis.links.map((s, i) => <div key={i} className="pline"><span className="lbl">{s}</span></div>)}
        <div className="gaps-head">PATTERN OF LIFE <span className="dim">time wheel</span></div>
        <div className="pline"><span className="lbl">{d.analysis.pattern}</span></div>
        <div className="gaps-head">ENTITIES <span className="dim">{confirmed.length} confirmed · {d.graph.entities.length - confirmed.length} suggested</span></div>
        {d.graph.entities.map(e => <div key={e.id} className={`pline ${e.status === 'confirmed' ? 'ok' : ''}`}><span className="mark">{e.status === 'confirmed' ? '✓' : '?'}</span><span className="lbl">{e.name}{e.aliases.length > 0 && <span className="dim"> aka {e.aliases.join(', ')}</span>}</span><span className="src dim">{e.type} · {e.evidence.length} cite{e.evidence.length === 1 ? '' : 's'}</span></div>)}
        {d.graph.relationships.map((r: CaseRel) => <div key={r.id} className={`pline ${r.status === 'confirmed' ? 'ok' : ''}`}><span className="mark">{r.status === 'confirmed' ? '—' : '┄'}</span><span className="lbl">{names[r.from]} → {names[r.to]}</span><span className="src dim">{r.type} [{r.grade}]</span></div>)}
        <div className="gaps-head">TIMELINE</div>
        {d.graph.events.map(v => <div key={v.id} className={`pline ${v.status === 'confirmed' ? 'ok' : ''}`}><span className="mark">{v.status === 'confirmed' ? '✓' : '?'}</span><span className="lbl">{when(v.at)} {v.summary}</span></div>)}
      </>}
      {tab === 'reports' && <>
        {d.reports.length === 0 && <div className="dim small">No reports filed into this case.</div>}
        {d.reports.map(r => <div key={r.id} className="rpt"><div className="rpt-head"><span className="chip small">{r.kind.toUpperCase()}</span> <span>{r.reported_by}{r.reporter_role && <span className="dim"> · {r.reporter_role}</span>}</span> <span className="chip small green">{r.grade}</span> <span className="dim">{when(r.at)}{r.place ? ` · ${r.place}` : ''}</span></div><div className="rpt-text">{r.text}</div></div>)}
      </>}
    </div>)
}

function ReportForm({ busy, act, cases, role, defaultCase, onDone }: { busy: string | null; act: Act; cases: Case[]; role: Role; defaultCase: string | null; onDone: () => void }) {
  const [f, setF] = useState({ text: '', kind: 'spot', reported_by: '', reporter_role: role === 'security' ? 'site security' : role === 'ep' ? 'EP detail' : '', place: '', case_id: defaultCase ?? '' })
  const ok = f.text.trim().length > 10 && f.reported_by
  return (
    <div className="dform">
      <div className="dform-head">SPOTREP <span className="dim">our own people · graded A2 until corroborated · extraction only suggests</span></div>
      <textarea rows={4} placeholder="Who, what, where, when — as observed. Names, handles, plates, and numbers will be suggested to the analyst with this text as the citation." value={f.text} onChange={e => setF({ ...f, text: e.target.value })} />
      <div className="two"><input placeholder="Reported by" value={f.reported_by} onChange={e => setF({ ...f, reported_by: e.target.value })} /><input placeholder="Role (e.g. site security)" value={f.reporter_role} onChange={e => setF({ ...f, reporter_role: e.target.value })} /></div>
      <div className="two"><input placeholder="Place" value={f.place} onChange={e => setF({ ...f, place: e.target.value })} />
        <select value={f.case_id} onChange={e => setF({ ...f, case_id: e.target.value })}><option value="">no case (log only)</option>{cases.filter(c => c.status === 'open').map(c => <option key={c.id} value={c.id}>{c.title}</option>)}</select></div>
      <div className="row-btns"><select value={f.kind} onChange={e => setF({ ...f, kind: e.target.value })}><option value="spot">SPOTREP</option><option value="sitrep">SITREP</option><option value="note">NOTE</option></select>
        <button className="mini ok" disabled={!!busy || !ok} onClick={() => { act('filing report', () => api.fileReport({ text: f.text, kind: f.kind, reported_by: f.reported_by, reporter_role: f.reporter_role || undefined, place: f.place || undefined, case_id: f.case_id || undefined })); onDone() }}>FILE</button>
        <button className="mini" onClick={onDone}>CANCEL</button></div>
    </div>)
}

function CaseForm({ busy, act, onDone }: { busy: string | null; act: Act; onDone: () => void }) {
  const [f, setF] = useState({ title: '', kind: 'general', summary: '' })
  return (
    <div className="dform">
      <div className="dform-head">OPEN CASE <span className="dim">person cases: Battle Captain or S2 only · every read is logged</span></div>
      <input placeholder="Title (e.g. North gate loiterer)" value={f.title} onChange={e => setF({ ...f, title: e.target.value })} />
      <input placeholder="What this case is about" value={f.summary} onChange={e => setF({ ...f, summary: e.target.value })} />
      <div className="row-btns"><select value={f.kind} onChange={e => setF({ ...f, kind: e.target.value })}>{['general', 'person', 'site', 'actor'].map(k => <option key={k} value={k}>{k}</option>)}</select>
        <button className="mini ok" disabled={!!busy || !f.title} onClick={() => { act('opening case', () => api.openCase(f)); onDone() }}>OPEN</button>
        <button className="mini" onClick={onDone}>CANCEL</button></div>
    </div>)
}
