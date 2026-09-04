import { useEffect, useState } from 'react'
import * as api from './api'
import type { AreaAssessment, AreaCell, Role } from './types'

type Act = (l: string, f: () => Promise<unknown>) => void
const APPROVERS = ['battle_captain', 'analyst']

/** §5.6 — the Area Assessment: candidates as columns, indicators as rows, three cell states, no composite. */
export function AreaPanel({ id, role, busy, act, onClose, reload }: { id: string; role: Role; busy: string | null; act: Act; onClose: () => void; reload: number }) {
  const [a, setA] = useState<AreaAssessment | null>(null)
  const [open, setOpen] = useState<{ c: number; i: string } | null>(null)
  useEffect(() => { api.getArea(id).then(setA).catch(() => setA(null)) }, [id, reload])
  if (!a) return <div className="detail area"><button className="close" onClick={onClose}>×</button><div className="loading-inline">Loading…</div></div>
  const can = APPROVERS.includes(role)
  const cell = (ci: number, ind: string): AreaCell | undefined => a.candidates[ci].cells.find(c => c.indicator === ind)
  const sel = open ? cell(open.c, open.i) : undefined
  return (
    <div className="detail area" onClick={e => e.stopPropagation()}>
      <button className="close" onClick={onClose}>×</button>
      <div className="d-kicker">AREA ASSESSMENT · <span className={`chip small ${a.status}`}>{a.status.toUpperCase()}</span> · {a.author}</div>
      <div className="d-title">{a.title}</div>
      <div className="dim small">{a.purpose} · {a.candidates[0]?.window_from ? `${a.candidates[0].window_from.slice(0, 10)} → ${a.candidates[0].window_to?.slice(0, 10)}` : 'no window'}</div>
      {a.refusal && <div className="refusal">{a.refusal}</div>}
      <div className="matrix-wrap"><table className="matrix">
        <thead><tr><th className="ind">INDICATOR</th>{a.candidates.map(c => <th key={c.requirement_id}>{c.place}<div className="dim small">{c.counts.reported} reported · {c.counts.quiet} quiet · {c.counts.gap} gaps</div></th>)}</tr></thead>
        <tbody>
          {a.indicators.map(i => <tr key={i.id}>
            <td className="ind" title={i.label}>{i.label}</td>
            {a.candidates.map((c, ci) => { const x = cell(ci, i.id); if (!x) return <td key={c.requirement_id} />
              const on = open?.c === ci && open.i === i.id
              return <td key={c.requirement_id} className={`cell st-${x.state} ${on ? 'on' : ''}`} onClick={() => setOpen(on ? null : { c: ci, i: i.id })}>
                {x.state === 'reported' && <><div className="term">{x.likelihood}</div><div className="dim small">{x.band} · {x.confidence} conf</div></>}
                {x.state === 'quiet' && <><div className="term quiet">quiet</div><div className="dim small">{x.sources.join(', ')} watching</div></>}
                {x.state === 'gap' && <><div className="term gap">not collected</div><div className="dim small">→ {(x.recommended ?? []).slice(0, 2).join(' · ') || 'no source'}</div></>}
              </td> })}
          </tr>)}
        </tbody>
      </table></div>
      {sel && open && <div className="cellview">
        <div className="gaps-head">{a.candidates[open.c].place.toUpperCase()} · {sel.label}</div>
        {sel.state === 'reported' && <>
          <div className="bluf">Adverse impact is <b>{sel.likelihood}</b> ({sel.band}), <b>{sel.confidence}</b> confidence.</div>
          <div className="dim small">{sel.confidence_basis.join(' · ')}</div>
          {sel.evidence.map(e => <div key={e.threat_id} className="pline"><span className={`sev ${e.severity}`}>{e.severity.slice(0, 3).toUpperCase()}</span><span className="lbl">{e.title}</span><span className="src dim">{e.source} · {e.distance_km} km · {e.observed_at.slice(0, 10)}{e.synthetic ? ' · synthetic' : ''}</span></div>)}
        </>}
        {sel.state === 'quiet' && <div className="bluf">{sel.confidence_basis[0]}. Not a finding of safety: a tasked source has reported nothing, and its reliability caps what that is worth.</div>}
        {sel.state === 'gap' && <div className="bluf">Nobody is collecting this. Recommended: {(sel.recommended ?? []).join(', ') || 'none in the catalog'}. Connect a source and re-draft.</div>}
      </div>}
      <div className="section-label">BLUF PER CANDIDATE</div>
      {a.candidates.map(c => <div key={c.requirement_id} className="bluf">{c.bluf}</div>)}
      {a.gaps.length > 0 && <div className="dim small" style={{ marginTop: 6 }}>Not collected for any candidate: {a.gaps.join('; ')}.</div>}
      <div className="dim small" style={{ marginTop: 6 }}>{a.note}</div>
      {can && <div className="row-btns" style={{ marginTop: 10 }}>
        {a.status === 'draft' && <button className="mini" disabled={!!busy} onClick={() => act('sending to review', () => api.setAreaStatus(a.id, 'review').then(setA))}>SEND TO REVIEW</button>}
        {a.status !== 'approved' && <button className="mini ok" disabled={!!busy || !a.approvable} title={a.approvable ? '' : 'no qualifying evidence — cannot be approved'} onClick={() => act('approving', () => api.setAreaStatus(a.id, 'approved').then(setA))}>APPROVE</button>}
        {a.status === 'approved' && <span className="dim small">approved by {a.decided_by}</span>}
      </div>}
    </div>)
}
