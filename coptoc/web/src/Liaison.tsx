import { useEffect, useState } from 'react'
import * as api from './api'
import { Question } from './Headline'
import type { LiaisonSource, Role } from './types'

type Act = (l: string, f: () => Promise<unknown>) => void
const GRADES = ['A', 'B', 'C', 'D', 'E', 'F'] as const
const KINDS = ['host_nation', 'police', 'venue', 'partner', 'military', 'other'] as const
const GRADE_WORD: Record<string, string> = { A: 'reliable', B: 'usually reliable', C: 'fairly reliable', D: 'not usually reliable', E: 'unreliable', F: 'cannot be judged' }

/** §5.10b Phase 4 (LOE 5) — liaison sources: who reports to us from outside, graded by the analyst over time.
 *  The record (borne out / disposed) informs the grade; it never sets it. */
export function LiaisonPanel({ reload, busy, act, role }: { reload: number; busy: string | null; act: Act; role: Role }) {
  const [rows, setRows] = useState<LiaisonSource[]>([])
  const [adding, setAdding] = useState(false)
  const [f, setF] = useState({ name: '', kind: 'police', reliability: 'F', notes: '' })
  useEffect(() => { api.listLiaisonSources().then(setRows).catch(() => setRows([])) }, [reload])
  const staff = role === 'battle_captain' || role === 'analyst'
  return <>
    <Question q="Who else reports to us" count={`${rows.length} liaison source${rows.length === 1 ? '' : 's'}`}>
      {staff && <button className="mini" onClick={() => setAdding(a => !a)}>+ SOURCE</button>}
    </Question>
    {adding && <div className="dform">
      <div className="dform-head">LIAISON SOURCE <span className="dim">host-nation police, a venue desk, a partner guard force · starts at F unless you grade it</span></div>
      <input placeholder="Name (SFPD Southern Station)" value={f.name} onChange={e => setF({ ...f, name: e.target.value })} />
      <div className="two"><select value={f.kind} onChange={e => setF({ ...f, kind: e.target.value })}>{KINDS.map(k => <option key={k} value={k}>{k.replace('_', ' ')}</option>)}</select>
        <select value={f.reliability} onChange={e => setF({ ...f, reliability: e.target.value })}>{GRADES.map(g => <option key={g} value={g}>{g} · {GRADE_WORD[g]}</option>)}</select></div>
      <input placeholder="Notes (optional)" value={f.notes} onChange={e => setF({ ...f, notes: e.target.value })} />
      <div className="row-btns"><button className="mini ok" disabled={!!busy || !f.name.trim()} onClick={() => act('registering a liaison source', () => api.createLiaisonSource(f).then(() => { setAdding(false); setF({ name: '', kind: 'police', reliability: 'F', notes: '' }) }))}>REGISTER</button><button className="mini" onClick={() => setAdding(false)}>CANCEL</button></div>
    </div>}
    <ul className="list">
      {rows.map(s => <li key={s.id} className="row liaison" title={`${s.name} · ${s.kind.replace('_', ' ')}\n${GRADE_WORD[s.reliability]}${s.graded_by ? ` · graded by ${s.graded_by}` : ' · not yet graded'}\n${s.record.reports} reports · ${s.record.borne_out} borne out · ${s.record.dismissed} dismissed · ${s.record.filed} awaiting disposition${s.notes ? `\n${s.notes}` : ''}`}>
        <span className={`sev grade-${s.reliability}`}>{s.reliability}</span>
        <span className="name">{s.name} <span className="dim small">· {s.kind.replace('_', ' ')}</span></span>
        <span className="meta dim">{s.record.reports ? `${s.record.borne_out}/${s.record.disposed} of ${s.record.reports}` : 'no reports'}</span>
        {staff && <select className="grade" value={s.reliability} disabled={!!busy} onChange={e => { const note = window.prompt(`Grade ${s.name} ${e.target.value} — why?`, '') ?? ''; act('grading a liaison source', () => api.gradeLiaisonSource(s.id, { reliability: e.target.value, note })) }}>{GRADES.map(g => <option key={g} value={g}>{g}</option>)}</select>}
      </li>)}
      {rows.length === 0 && <li className="dim small" style={{ padding: '2px 14px 6px' }}>No liaison source yet. A LIAISON report names one; an unknown name becomes a source at F.</li>}
    </ul>
  </>
}
