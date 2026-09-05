// §5.10 — taskings: the work moving between sections. Each panel shows what it owes (inbox), what it is waiting on (outbox), and can raise one.
import { useState } from 'react'
import * as api from './api'
import type { SectionCode, Tasking, TaskingBoard } from './types'

const SEC_TITLE: Record<SectionCode, string> = { S1: 'Personnel', S2: 'Intelligence', S3: 'Operations', S4: 'Logistics', S6: 'Signal' }
const KIND_ICON: Record<string, string> = { collection: '◎', comms: '((·))', supply: '⛽', movement: '➜', coverage: '⛨', other: '·' }
const fmt = (iso: string | null) => iso ? new Date(iso).toUTCString().slice(5, 22) + 'Z' : ''

export function TaskingBox({ section, board, canEdit, busy, act, enabled, onSelect }: { section: SectionCode; board: TaskingBoard | undefined; canEdit: boolean; busy: string | null; act: (l: string, f: () => Promise<unknown>) => void; enabled: SectionCode[]; onSelect?: (t: Tasking) => void }) {
  const [raise, setRaise] = useState(false)
  const [showDone, setShowDone] = useState(false)
  const [f, setF] = useState({ to_section: (enabled.find(s => s !== section) ?? 'S3') as SectionCode, kind: 'other' as Tasking['kind'], title: '', asset: '', priority: 'routine' as Tasking['priority'], window_from: '', window_to: '', notes: '' })
  if (!board) return null
  const inbox = board.items.filter(t => t.to_section === section && (t.open || showDone))
  const outbox = board.items.filter(t => t.from_section === section && (t.open || showDone))
  const set = (t: Tasking, status: Tasking['status']) => {
    const result = status === 'declined' ? (window.prompt('Why?', '') ?? '') : status === 'complete' ? (window.prompt('What was done?', t.result) ?? '') : ''
    if (status === 'declined' && !result) return
    act(`${status} · ${t.title}`, () => api.updateTasking(t.id, { status, ...(result ? { result } : {}) }))
  }
  const submit = () => { if (!f.title.trim()) return; act(`raising a tasking on ${f.to_section}`, async () => { await api.raiseTasking({ ...f, from_section: section, title: f.title.trim(), window_from: f.window_from ? new Date(f.window_from).toISOString() : null, window_to: f.window_to ? new Date(f.window_to).toISOString() : null }); setRaise(false); setF({ ...f, title: '', asset: '', notes: '' }) }) }
  const row = (t: Tasking, mine: boolean) => (
    <li key={t.id} className={`row two tasking ${t.health} ${t.open ? '' : 'done'}`} onClick={() => onSelect?.(t)}>
      <div className="l1">
        <span className={`sev ${t.health === 'green' ? 'ok' : t.health === 'amber' ? 'low' : 'critical'}`} title={t.priority}>{t.priority === 'urgent' ? 'URG' : t.priority === 'priority' ? 'PRI' : 'RTN'}</span>
        <span className="name"><span className="dim mono">{KIND_ICON[t.kind]} {mine ? `${t.from_section} →` : `→ ${t.to_section}`}</span> {t.title}</span>
        <span className={`chip ${t.status === 'requested' ? 'open' : t.status === 'complete' ? 'green' : t.status === 'declined' ? 'dim' : 'active'}`}>{t.status.toUpperCase()}{t.overdue ? ' · LATE' : ''}</span>
      </div>
      <div className="l2">
        <span className="dim small">{t.asset}{t.subject_name ? ` · ${t.subject_name}` : ''}{t.window_from ? ` · ${fmt(t.window_from)}${t.window_to ? ' → ' + fmt(t.window_to) : ''}` : ''}{t.result ? ` · ${t.result}` : ''}</span>
        {mine && canEdit && t.open && <span className="acts">
          {t.status === 'requested' && <button className="mini" disabled={!!busy} onClick={e => { e.stopPropagation(); set(t, 'accepted') }}>ACCEPT</button>}
          {t.status !== 'scheduled' && <button className="mini" disabled={!!busy} onClick={e => { e.stopPropagation(); set(t, 'scheduled') }}>SCHEDULE</button>}
          <button className="mini ok" disabled={!!busy} onClick={e => { e.stopPropagation(); set(t, 'complete') }}>COMPLETE</button>
          <button className="mini danger" disabled={!!busy} onClick={e => { e.stopPropagation(); set(t, 'declined') }}>DECLINE</button>
        </span>}
      </div>
    </li>)
  return (<>
    <div className="section-label">TASKINGS <span className="dim">{inbox.filter(t => t.open).length} to do · {outbox.filter(t => t.open).length} waiting</span>
      <span className="grp"><button className={`chip btn ${showDone ? 'on' : ''}`} onClick={() => setShowDone(v => !v)}>DONE</button>{canEdit && <button className={`chip btn ${raise ? 'on' : ''}`} onClick={() => setRaise(v => !v)}>RAISE</button>}</span></div>
    {raise && <div className="dform">
      <div className="dform-head">RAISE A TASKING <span className="dim">from {section} · what you need, from whom, by when</span></div>
      <div className="row-btns">
        <select value={f.to_section} onChange={e => setF({ ...f, to_section: e.target.value as SectionCode })}>{enabled.filter(s => s !== section).map(s => <option key={s} value={s}>{s} · {SEC_TITLE[s]}</option>)}</select>
        <select value={f.kind} onChange={e => setF({ ...f, kind: e.target.value as Tasking['kind'] })}>{(['collection', 'comms', 'supply', 'movement', 'coverage', 'other'] as const).map(k => <option key={k}>{k}</option>)}</select>
        <select value={f.priority} onChange={e => setF({ ...f, priority: e.target.value as Tasking['priority'] })}>{(['routine', 'priority', 'urgent'] as const).map(k => <option key={k}>{k}</option>)}</select>
      </div>
      <input placeholder="What (title)" value={f.title} onChange={e => setF({ ...f, title: e.target.value })} />
      <input placeholder="Asset or capability wanted" value={f.asset} onChange={e => setF({ ...f, asset: e.target.value })} />
      <div className="row-btns"><input type="datetime-local" value={f.window_from} onChange={e => setF({ ...f, window_from: e.target.value })} /><input type="datetime-local" value={f.window_to} onChange={e => setF({ ...f, window_to: e.target.value })} /></div>
      <div className="row-btns"><button className="mini ok" disabled={!!busy || !f.title.trim()} onClick={submit}>RAISE</button><button className="mini" onClick={() => setRaise(false)}>CANCEL</button></div>
    </div>}
    {inbox.length > 0 && <><div className="section-label sub">OWED BY {section}</div><ul className="list">{inbox.map(t => row(t, true))}</ul></>}
    {outbox.length > 0 && <><div className="section-label sub">WAITING ON OTHERS</div><ul className="list">{outbox.map(t => row(t, false))}</ul></>}
    {inbox.length === 0 && outbox.length === 0 && <div className="dim small" style={{ padding: '2px 14px 8px' }}>Nothing open.</div>}
  </>)
}
