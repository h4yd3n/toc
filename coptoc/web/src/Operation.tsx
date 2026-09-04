import { useEffect, useState } from 'react'
import * as api from './api'
import type { Distribution, Operation, Role } from './types'

type Act = (l: string, f: () => Promise<unknown>) => void
const SECTIONS = ['S1', 'S2', 'S3', 'S4', 'S6']

/** §5.10 #3 — the operation against its subject: tasks by section, S4 asks, status. Opened from an approved product. */
export function OperationPanel({ id, role, busy, act, onClose, reload }: { id: string; role: Role; busy: string | null; act: Act; onClose: () => void; reload: number }) {
  const [op, setOp] = useState<Operation | null>(null)
  const [nt, setNt] = useState({ title: '', section: 'S3', owner: '' })
  const [nr, setNr] = useState({ item: '', qty: 1 })
  const load = () => api.getOperation(id).then(setOp).catch(() => setOp(null))
  useEffect(load, [id, reload])
  if (!op) return <div className="detail op"><button className="close" onClick={onClose}>×</button><div className="loading-inline">Loading…</div></div>
  const isBC = role === 'battle_captain'
  const next = (s: string) => s === 'todo' ? 'doing' : s === 'doing' ? 'done' : 'todo'
  return (
    <div className="detail op" onClick={e => e.stopPropagation()}>
      <button className="close" onClick={onClose}>×</button>
      <div className="d-kicker">S3 OPERATION · <span className={`chip small ${op.status}`}>{op.status.toUpperCase()}</span> · opened by {op.opened_by}{op.from_product_id && <> · from <b>{op.from_product_id}</b></>}</div>
      <div className="d-title">{op.title}</div>
      <div className="d-sub">{op.subject_type} · {op.subject_name}</div>
      <div className="d-stats"><span><b>{op.tasks_done}</b>/{op.tasks_total} tasks</span>{op.blocked > 0 && <span className="chip red">{op.blocked} BLOCKED</span>}<span><b>{op.resources_open}</b> S4 asks open</span></div>
      <div className="bar big"><span style={{ width: `${op.pct}%` }} className={op.pct === 100 ? 'ok' : ''} /></div>
      {op.notes && <div className="kv"><span>Notes</span>{op.notes}</div>}
      <div className="section-label">TASKS <span className="dim">by staff section · click a task to advance it</span></div>
      <ul className="tasks">
        {op.tasks.map(t => <li key={t.id} className={`task ${t.status}`}>
          <button className={`chip btn small ${t.status === 'done' ? 'green' : t.status === 'doing' ? 'amber' : t.status === 'blocked' ? 'red' : ''}`} disabled={!!busy || op.status === 'complete'} onClick={() => act('updating task', () => api.updateTask(op.id, t.id, { status: next(t.status) }).then(load))}>{t.status.toUpperCase()}</button>
          <span className="chip small">{t.section}</span>
          <span className="ttitle">{t.title}</span>
          <span className="dim small">{t.owner || 'unassigned'}{t.updated_by ? ` · ${t.updated_by}` : ''}</span>
          {t.status !== 'blocked' && t.status !== 'done' && <button className="mini danger" style={{ padding: '0 5px' }} disabled={!!busy} onClick={() => act('blocking task', () => api.updateTask(op.id, t.id, { status: 'blocked' }).then(load))} title="blocked">!</button>}
        </li>)}
      </ul>
      {op.status !== 'complete' && <div className="row-btns">
        <input placeholder="New task" value={nt.title} onChange={e => setNt({ ...nt, title: e.target.value })} style={{ flex: 1 }} />
        <select value={nt.section} onChange={e => setNt({ ...nt, section: e.target.value })}>{SECTIONS.map(s => <option key={s}>{s}</option>)}</select>
        <input placeholder="Owner" value={nt.owner} onChange={e => setNt({ ...nt, owner: e.target.value })} style={{ width: 90 }} />
        <button className="mini ok" disabled={!!busy || !nt.title} onClick={() => act('adding task', () => api.addTask(op.id, nt).then(() => { setNt({ title: '', section: 'S3', owner: '' }); load() }))}>ADD</button></div>}
      <div className="section-label">S4 · RESOURCES <span className="dim">asked by S3, answered by S4</span></div>
      <ul className="tasks">
        {op.resources.map(r => <li key={r.id} className="task">
          <span className={`chip small ${r.status === 'issued' ? 'green' : r.status === 'approved' ? 'amber' : r.status === 'denied' ? 'red' : ''}`}>{r.status.toUpperCase()}</span>
          <span className="ttitle">{r.qty} × {r.item}</span><span className="dim small">{r.note}{r.updated_by ? ` · ${r.updated_by}` : ''}</span>
          {r.status === 'requested' && <span className="qbtns"><button className="mini ok" disabled={!!busy} onClick={() => act('answering ask', () => api.answerResource(op.id, r.id, 'approved').then(load))}>APPROVE</button><button className="mini danger" disabled={!!busy} onClick={() => act('answering ask', () => api.answerResource(op.id, r.id, 'denied').then(load))}>DENY</button></span>}
          {r.status === 'approved' && <button className="mini" disabled={!!busy} onClick={() => act('issuing', () => api.answerResource(op.id, r.id, 'issued').then(load))}>ISSUED</button>}
        </li>)}
        {op.resources.length === 0 && <li className="dim small">No asks.</li>}
      </ul>
      {op.status !== 'complete' && <div className="row-btns">
        <input placeholder="Ask S4 for…" value={nr.item} onChange={e => setNr({ ...nr, item: e.target.value })} style={{ flex: 1 }} />
        <input type="number" min={1} value={nr.qty} onChange={e => setNr({ ...nr, qty: +e.target.value })} style={{ width: 56 }} />
        <button className="mini ok" disabled={!!busy || !nr.item} onClick={() => act('requesting resource', () => api.requestResource(op.id, nr).then(() => { setNr({ item: '', qty: 1 }); load() }))}>ASK</button></div>}
      {isBC && <div className="row-btns" style={{ marginTop: 10 }}>
        {op.status === 'planned' && <button className="mini ok" disabled={!!busy} onClick={() => act('activating', () => api.setOperationStatus(op.id, 'active').then(setOp))}>ACTIVATE</button>}
        {op.status !== 'complete' && op.status !== 'cancelled' && <><button className="mini" disabled={!!busy} onClick={() => act('completing', () => api.setOperationStatus(op.id, 'complete').then(setOp))}>COMPLETE</button>
          <button className="mini danger" disabled={!!busy} onClick={() => act('cancelling', () => api.setOperationStatus(op.id, 'cancelled').then(setOp))}>CANCEL OP</button></>}
      </div>}
    </div>)
}

/** §5.10 #4 — who a product went to, when, and whether they read it. */
export function DistributionBox({ ptype, pid, role, busy, act, releasable }: { ptype: string; pid: string; role: Role; busy: string | null; act: Act; releasable: boolean }) {
  const [d, setD] = useState<Distribution | null>(null)
  const [picked, setPicked] = useState<Set<string>>(new Set(['battle_captain', 'ep', 'security']))
  const load = () => api.getDistribution(ptype, pid).then(setD).catch(() => setD(null))
  useEffect(load, [ptype, pid])
  const can = role === 'battle_captain' || role === 'analyst'
  const toggle = (r: string) => setPicked(p => { const n = new Set(p); n.has(r) ? n.delete(r) : n.add(r); return n })
  const mine = d?.recipients.find(r => (r.recipient === role || r.recipient === api.session.actor) && !r.acknowledged_at)
  return (
    <div className="dist">
      <div className="gaps-head">DISSEMINATION <span className="dim">{d ? `${d.acknowledged}/${d.sent} acknowledged${d.stale.length ? ` · ${d.stale.length} unread > 2 h` : ''}` : ''}</span>
        {mine && <button className="mini ok" disabled={!!busy} onClick={() => act('acknowledging', () => api.ackProduct(ptype, pid).then(setD))}>ACKNOWLEDGE</button>}</div>
      {d && d.recipients.map(r => <div key={r.id} className={`pline ${r.acknowledged_at ? 'ok' : r.stale ? 'gap' : ''}`}><span className="mark">{r.acknowledged_at ? '✓' : r.stale ? '✗' : '…'}</span>
        <span className="lbl">{r.recipient}<span className="dim"> · {r.channel}{r.delivery !== 'recorded' ? ` (${r.delivery})` : ''}</span></span>
        <span className="src dim">{r.acknowledged_at ? `ack by ${r.acknowledged_by} in ${r.latency.sent_to_ack_min} min` : `unread ${r.latency.outstanding_min} min`}</span></div>)}
      {can && releasable && <div className="row-btns" style={{ flexWrap: 'wrap' }}>
        {['battle_captain', 'ep', 'security', 'analyst', 'ea'].map(r => <label key={r} className="dim small" style={{ display: 'flex', gap: 3, alignItems: 'center' }}><input type="checkbox" checked={picked.has(r)} onChange={() => toggle(r)} />{r}</label>)}
        <button className="mini" disabled={!!busy || picked.size === 0} onClick={() => act('disseminating', () => api.disseminate(ptype, pid, [...picked]).then(setD))}>SEND TO WALL</button>
        <button className="mini" disabled={!!busy || picked.size === 0} onClick={() => act('disseminating', () => api.disseminate(ptype, pid, [...picked], 'chat').then(setD))}>+ CHAT</button></div>}
      {!releasable && <div className="dim small">Approve or release first; drafts are not disseminated.</div>}
    </div>)
}
