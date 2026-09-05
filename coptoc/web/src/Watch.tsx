import { useEffect, useState } from 'react'
import * as api from './api'
import type { Brief, Estimate, Role, Watch } from './types'

const OWNERS: Record<string, Role[]> = { S1: ['battle_captain', 'security'], S2: ['battle_captain', 'analyst'], S3: ['battle_captain', 'security', 'ea'], S4: ['battle_captain', 'logistics'], S6: ['battle_captain', 'signal'] }
const hm = (h: number) => `${Math.floor(Math.abs(h))}h${String(Math.round((Math.abs(h) % 1) * 60)).padStart(2, '0')}`

/** The watch chip in the posture bar: who has the floor, how far in, who's next. */
export function WatchChip({ w, onOpen }: { w: Watch | undefined; onOpen: () => void }) {
  if (!w) return null
  const cls = w.status === 'pending_ack' ? 'pending' : w.overdue ? 'overdue' : w.in_overlap ? 'overlap' : ''
  return (
    <button className={`watch-chip ${cls}`} onClick={onOpen} title="Open the shift change brief">
      <span className="wname">{w.name.toUpperCase()} WATCH</span>
      <span className="wbc">{w.battle_captain ? `BC ${w.battle_captain}` : 'UNASSIGNED'}</span>
      <span className="wtime">{w.status === 'pending_ack' ? 'HANDOVER PENDING' : w.overdue ? `OVERDUE ${hm(w.remaining_h)}` : `${hm(w.elapsed_h)} · → ${w.next_watch.split(' ')[0]} in ${hm(w.remaining_h)}`}</span>
    </button>)
}

/** The running-estimate line under a panel head. Editable by the section's owners. */
export function EstimateLine({ e, role, busy, act }: { e: Estimate | undefined; role: Role; busy: string | null; act: (l: string, f: () => Promise<unknown>) => void }) {
  const [editing, setEditing] = useState(false)
  const [a, setA] = useState(''); const [r, setR] = useState('')
  if (!e) return null
  const canEdit = (OWNERS[e.section] ?? ['battle_captain']).includes(role)
  if (editing) return (
    <div className="estimate editing">
      <textarea value={a} onChange={ev => setA(ev.target.value)} placeholder={`${e.section} assesses…`} rows={2} />
      <input value={r} onChange={ev => setR(ev.target.value)} placeholder="Recommendation (optional)" />
      <div className="row-btns"><button className="mini ok" disabled={!!busy || !a.trim()} onClick={() => { act('updating estimate', () => api.setEstimate(e.section, a, r)); setEditing(false) }}>SAVE</button><button className="mini" onClick={() => setEditing(false)}>CANCEL</button></div>
    </div>)
  return (
    <div className={`estimate ${e.assessment ? '' : 'empty'}`} onClick={() => { if (canEdit) { setA(e.assessment); setR(e.recommendation); setEditing(true) } }} title={canEdit ? 'Click to update — you own this estimate' : 'Owned by ' + (OWNERS[e.section] ?? ['battle_captain']).join(' / ')}>
      <b>{e.section} assesses:</b> {e.assessment || <span className="dim">no assessment on record{canEdit ? ' — click to add' : ''}</span>}
      {e.recommendation && <div className="rec">↳ {e.recommendation}</div>}
      {e.updated_by && <span className="who dim">— {e.updated_by}</span>}
    </div>)
}

/** The shift change brief: the running estimates read out at handover, in briefing order. */
export function BriefPanel({ role, busy, act, onClose, reload }: { role: Role; busy: string | null; act: (l: string, f: () => Promise<unknown>) => void; onClose: () => void; reload: number }) {
  const [b, setB] = useState<Brief | null>(null)
  const [notes, setNotes] = useState(''); const [nstr, setNstr] = useState(false)
  const [incoming, setIncoming] = useState(''); const [acked, setAcked] = useState<Set<string>>(new Set())
  useEffect(() => { api.getBrief().then(setB).catch(() => setB(null)) }, [reload])
  if (!b) return <div className="detail brief"><button className="close" onClick={onClose}>×</button><div className="loading-inline">Generating brief…</div></div>
  const w = b.watch, isBC = role === 'battle_captain', pending = w.status === 'pending_ack'
  const required = b.acknowledgement.required_item_ids, allAcked = required.every(id => acked.has(id))
  const sig = Object.entries(b.significant_events)
  return (
    <div className="detail brief" onClick={e => e.stopPropagation()}>
      <button className="close" onClick={onClose}>×</button>
      <div className="d-kicker">SHIFT CHANGE BRIEF · {w.name.toUpperCase()} WATCH · {new Date(b.window.from).toUTCString().slice(17, 22)}Z → {new Date(b.window.to).toUTCString().slice(17, 22)}Z{pending ? ' · FROZEN AT HANDOVER' : ' · LIVE'}</div>
      <div className="d-title">{w.battle_captain ?? 'Unassigned'} → {w.next_watch}</div>
      {b.nstr && <div className="nstr">NSTR — nothing significant to report · affirmed by {w.battle_captain}</div>}

      <div className="section-label">1 · SIGNIFICANT EVENTS THIS SHIFT <span className="dim">{b.event_count}</span></div>
      {sig.length === 0 ? <div className="dim small">None recorded.</div> : sig.map(([k, evs]) => (
        <div key={k} className="bgroup"><div className="bgroup-head">{k.replace('_', ' ').toUpperCase()} <span className="dim">{evs.length}</span></div>
          <ul>{evs.slice(-6).map(e => <li key={e.id} className={e.during_handover ? 'overlap' : ''}><span className="dim">{new Date(e.at).toUTCString().slice(17, 22)}Z</span> {e.summary}{e.during_handover && <span className="chip amber small">DURING HANDOVER</span>}</li>)}</ul></div>))}

      <div className="section-label">2 · CURRENT STATUS</div>
      <div className="bstatus">
        {b.current_status.estimates.map(e => <div key={e.section} className="bline"><b>{e.section}:</b> {e.assessment || <span className="dim">no assessment</span>}{e.recommendation && <span className="dim"> ↳ {e.recommendation}</span>}</div>)}
        <div className="bline"><b>Posture</b> <span className={`chip ${b.current_status.posture}`}>{b.current_status.posture.toUpperCase()}</span> · <b>{b.current_status.unaccounted}</b> unaccounted · <b>{b.current_status.travelers.length}</b> traveling ({b.current_status.travelers.filter(t => t.checkin).length} checked in) · <b>{b.current_status.open_pirs.length}</b> open PIRs · <b>{b.current_status.assessments_in_review.length}</b> assessments in review</div>
        {b.current_status.open_incidents.map(i => <div key={i.id} className="bline red">☎ {i.title} — {i.accounted}/{i.total} accounted</div>)}
        {b.current_status.stale_checkins.length > 0 && <div className="bline amber">Stale check-ins: {b.current_status.stale_checkins.map(p => p.name).join(', ')}</div>}
      </div>

      <div className="section-label">3 · NEXT SHIFT · {b.next_shift.watch.toUpperCase()}</div>
      <div className="bstatus">
        {b.next_shift.events_starting.map(e => <div key={e.id} className="bline">★ {e.name} starts — {e.venue}</div>)}
        {b.next_shift.trips_departing.map(t => <div key={t.id} className="bline">✈ {t.who} departs → {t.to}</div>)}
        {b.next_shift.trips_returning.map(t => <div key={t.id} className="bline">↩ {t.who} returns from {t.from}</div>)}
        {b.next_shift.pirs_expiring.map(p => <div key={p.id} className="bline amber">⏱ {p.id} expires</div>)}
        {!b.next_shift.events_starting.length && !b.next_shift.trips_departing.length && !b.next_shift.trips_returning.length && !b.next_shift.pirs_expiring.length && <div className="dim small">Nothing scheduled in the next watch.</div>}
      </div>

      <div className="section-label">4 · HANDOVER ITEMS <span className="dim">{b.handover_items.length}</span></div>
      <div className="bstatus">
        {b.handover_items.length === 0 && !b.outgoing_notes && <div className="dim small">None.</div>}
        {b.handover_items.map(h => h.kind === 'open_incident'
          ? <div key={h.id} className="bline red">☎ Open roll call: {h.title} ({h.accounted}/{h.total})</div>
          : <label key={h.id} className={`bline ack ${acked.has(h.id) ? 'done' : ''}`}>
              {pending && isBC && <input type="checkbox" checked={acked.has(h.id)} onChange={e => { const n = new Set(acked); e.target.checked ? n.add(h.id) : n.delete(h.id); setAcked(n) }} />}
              <span className="chip amber small">DURING HANDOVER</span> {h.summary}</label>)}
        {b.outgoing_notes && <div className="bline notes"><b>Outgoing BC:</b> {b.outgoing_notes}</div>}
      </div>

      <div className="section-label">5 · ACKNOWLEDGEMENT</div>
      {!isBC && <div className="dim small">Battle Captain only.</div>}
      {isBC && !w.battle_captain && w.status === 'open' && <div className="hand">
        <input placeholder="Your name" value={incoming} onChange={e => setIncoming(e.target.value)} />
        <button className="mini ok" disabled={!!busy || !incoming.trim()} onClick={() => act('taking the watch', () => api.takeWatch(incoming))}>TAKE THE WATCH</button>
        <span className="dim small">First watch of the slot — nothing to hand over.</span></div>}
      {isBC && w.battle_captain && w.status === 'open' && <div className="hand">
        <textarea placeholder="Things the next shift needs to be aware of — in your words" value={notes} onChange={e => setNotes(e.target.value)} rows={3} />
        <label className="nstr-check"><input type="checkbox" checked={nstr} onChange={e => setNstr(e.target.checked)} /> NSTR — I affirm nothing significant to report this watch</label>
        <button className="mini danger" disabled={!!busy} onClick={() => act('handing over', () => api.handover(notes, nstr))}>HAND OVER THE WATCH</button></div>}
      {isBC && pending && <div className="hand">
        <div className="small">Handed over by <b>{w.battle_captain}</b> {w.handed_over_at && new Date(w.handed_over_at).toUTCString().slice(17, 22) + 'Z'}. {required.length > 0 && <span className="amber">{required.length} item{required.length === 1 ? '' : 's'} arrived during the overlap — tick each one above.</span>}</div>
        <input placeholder="Incoming Battle Captain — your name" value={incoming} onChange={e => setIncoming(e.target.value)} />
        <button className="mini ok" disabled={!!busy || !incoming.trim() || !allAcked} onClick={() => act('acknowledging handover', () => api.acknowledge(incoming, Array.from(acked)))}>ACKNOWLEDGE & TAKE THE WATCH</button></div>}
      {w.acknowledged_by && <div className="small dim">Acknowledged by {w.acknowledged_by}.</div>}
    </div>)
}
