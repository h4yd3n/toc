import { useEffect, useState } from 'react'
import * as api from './api'
import { Question } from './Headline'
import type { Distribution, Role, Selection, Warning } from './types'

type Act = (l: string, f: () => Promise<unknown>) => void
const sel = (w: Warning): Selection => w.subject_type === 'location' ? { type: 'location', id: w.subject_id } : w.subject_type === 'person' ? { type: 'person', id: w.subject_id } : { type: 'event', id: w.subject_id }

/** The red strip under the header: every released warning, with the reader's acknowledgement (§5.6, S6 alerting). */
export function FlashStrip({ warnings, role, busy, act, onSelect, reload }: { warnings: Warning[]; role: Role; busy: string | null; act: Act; onSelect: (s: Selection) => void; reload: number }) {
  const live = warnings.filter(w => w.status === 'released')
  if (live.length === 0) return null
  return (
    <div className="flash">
      {live.map(w => <FlashItem key={w.id} w={w} role={role} busy={busy} act={act} onSelect={onSelect} reload={reload} />)}
    </div>)
}

function FlashItem({ w, role, busy, act, onSelect, reload }: { w: Warning; role: Role; busy: string | null; act: Act; onSelect: (s: Selection) => void; reload: number }) {
  const [d, setD] = useState<Distribution | null>(null)
  useEffect(() => { api.getDistribution('warning', w.id).then(setD).catch(() => setD(null)) }, [w.id, reload])
  const mine = d?.recipients.find(r => r.recipient === role && !r.acknowledged_at)
  return (
    <div className="flash-item" onClick={() => onSelect(sel(w))}>
      <span className="flash-tag">FLASH</span>
      <span className="flash-title">{w.title.replace('FLASH — ', '')}</span>
      <span className="dim small">{w.released_by} · {w.age_min} min ago · SMS {w.dispatch.people ?? 0}{w.dispatch.simulated ? ' (simulated)' : ''} · {d ? `${d.acknowledged}/${d.sent} acknowledged` : ''}</span>
      {mine && <button className="mini ok" disabled={!!busy} onClick={e => { e.stopPropagation(); act('acknowledging', () => api.ackProduct('warning', w.id).then(setD)) }}>ACKNOWLEDGE</button>}
    </div>)
}

/** The S2 panel's warnings section: suggestions from the rule and human drafts, waiting for the Battle Captain. */
export function WarningsSection({ warnings, role, busy, act, onSelect }: { warnings: Warning[]; role: Role; busy: string | null; act: Act; onSelect: (s: Selection) => void }) {
  const pending = warnings.filter(w => w.status === 'suggested' || w.status === 'draft')
  const isBC = role === 'battle_captain'
  return (<>
    <Question q="What we have warned, or should" count={`${pending.length} awaiting release${warnings.some(w => w.status === 'released') ? ` · ${warnings.filter(w => w.status === 'released').length} FLASH live` : ''}`}>
      <span className="btns"><button className="mini" disabled={!!busy} onClick={() => act('running the warning rule', api.suggestWarnings)} title="critical inside a radius, or elevated with a confirmed link">RUN RULE</button></span></Question>
    {pending.length === 0 && <div className="dim small" style={{ padding: '2px 14px' }}>Nothing suggested. Confirm a link on an elevated threat, or collect a critical one, and the rule proposes a FLASH.</div>}
    <ul className="list">
      {pending.map(w => <li key={w.id} className="row reqrow warn" onClick={() => onSelect(sel(w))}>
        <div className="rq-head"><span className={`chip small ${w.severity === 'critical' ? 'red' : 'amber'}`}>{w.severity.toUpperCase()}</span><span className={`chip small ${w.status === 'suggested' ? 'review' : 'draft'}`}>{w.status.toUpperCase()}</span><span className="name">{w.title.replace('FLASH — ', '')}</span></div>
        <div className="rq-when dim">{w.suggested_by} · {w.subject_type} {w.subject_name}</div>
        <div className="row-btns" onClick={e => e.stopPropagation()}>
          {isBC ? <button className="mini danger" disabled={!!busy} onClick={() => act('releasing FLASH', () => api.releaseWarning(w.id))}>RELEASE · SMS + CHAT</button> : <span className="dim small">Battle Captain releases</span>}
          {(isBC || role === 'analyst') && <button className="mini" disabled={!!busy} onClick={() => act('cancelling warning', () => api.cancelWarning(w.id))}>CANCEL</button>}
        </div>
      </li>)}
    </ul>
  </>)
}
