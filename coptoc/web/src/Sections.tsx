// §7 S4 Logistics and §8 S6 Signal — the background boards. Mostly green; the wall shows the roll-up, the panel shows the detail.
import { useState } from 'react'
import * as api from './api'
import { Headline, Question, Tiles, toneFor } from './Headline'
import type { Location, Role, S4Board, S6Board, Shipment, SupplyLine, SystemLine } from './types'

const STATUS_CLASS: Record<string, string> = { green: 'green', amber: 'elevated', red: 'critical' }
export const healthTone = toneFor

/** §3.2 the S4 headline: how many supply lines are at or above the required level, then the exceptions as tiles. */
export function S4Headline({ board, owed }: { board: S4Board | undefined; owed: number }) {
  if (!board) return null
  const okLines = board.supplies.filter(x => x.status === 'green').length
  return (<>
    <Headline big={`${okLines}/${board.supplies.length}`} label="supply lines at or above required" sub={`${board.counts.red} red · ${board.counts.amber} amber · ${board.counts.inbound} inbound${board.counts.late ? ` · ${board.counts.late} late` : ''}`} pct={board.supplies.length ? (100 * okLines) / board.supplies.length : 100} tone={board.status} />
    <Tiles items={[{ v: board.counts.red, l: 'RED', tone: 'red', hide: board.counts.red === 0 }, { v: board.counts.amber, l: 'AMBER', tone: 'amber', hide: board.counts.amber === 0 }, { v: board.counts.inbound, l: 'INBOUND', tone: 'blue' }, { v: board.counts.late, l: 'LATE', tone: 'red', hide: board.counts.late === 0 }, { v: owed, l: 'OWED', tone: 'amber', hide: owed === 0, title: 'taskings S4 owes' }]} />
  </>)
}

/** §3.2 the S6 headline: systems up, then what is down, degraded, or off its primary net. */
export function S6Headline({ board, owed }: { board: S6Board | undefined; owed: number }) {
  if (!board) return null
  const up = board.counts.total - board.counts.down - board.counts.degraded
  const pace = Object.values(board.pace)
  return (<>
    <Headline big={`${up}/${board.counts.total}`} label="systems up" sub={`${board.counts.down} down · ${board.counts.degraded} degraded · ${pace.filter(p => p.in_use === 'primary').length}/${pace.length} sites on PRIMARY`} pct={board.counts.total ? (100 * up) / board.counts.total : 100} tone={board.status} />
    <Tiles items={[{ v: board.counts.down, l: 'DOWN', tone: 'red', hide: board.counts.down === 0 }, { v: board.counts.degraded, l: 'DEGRADED', tone: 'amber', hide: board.counts.degraded === 0 }, { v: pace.filter(p => !p.in_use).length, l: 'NO NET', tone: 'red', hide: !pace.some(p => !p.in_use) }, { v: pace.filter(p => p.in_use && p.in_use !== 'primary').length, l: 'OFF PRIMARY', tone: 'amber', hide: !pace.some(p => p.in_use && p.in_use !== 'primary') }, { v: owed, l: 'OWED', tone: 'amber', hide: owed === 0, title: 'taskings S6 owes' }]} />
  </>)
}
export const statusChip = (s: string, label?: string) => <span className={`chip ${STATUS_CLASS[s] ?? ''}`}>{(label ?? s).toUpperCase()}</span>
const S4_ROLES: Role[] = ['battle_captain', 'logistics']
const S6_ROLES: Role[] = ['battle_captain', 'signal']

export function S4Panel({ board, role, busy, act, site, onClearSite, onMap, toggleMap }: { board: S4Board | undefined; role: Role; busy: string | null; act: (l: string, f: () => Promise<unknown>) => void; site?: Location; onClearSite?: () => void; onMap?: boolean; toggleMap?: () => void }) {
  const [group, setGroup] = useState<'exceptions' | 'all'>('exceptions')
  const canEdit = S4_ROLES.includes(role)
  if (!board) return <div className="dim small" style={{ padding: 14 }}>No logistics board yet.</div>
  const atSite = (id: string | null) => !site || id === site.id
  const supplies = (group === 'all' ? board.supplies : board.supplies.filter(x => x.status !== 'green')).filter(x => atSite(x.location_id))
  const inbound = board.shipments.filter(x => !['arrived', 'cancelled'].includes(x.status)).filter(x => atSite(x.to_location_id))
  const setOnHand = (x: SupplyLine) => {
    const v = window.prompt(`${x.item} at ${x.location_name} — on hand (${x.unit}):`, String(x.on_hand)); if (v === null || v.trim() === '' || isNaN(+v)) return
    const note = window.prompt('Note (optional):', '') ?? ''
    act('updating the supply line', () => api.updateSupply(x.id, { on_hand: +v, ...(note ? { note } : {}) }))
  }
  return (<>
    <div className="s4-summary">
      {statusChip(board.status, `S4 ${board.status}`)}
      <span className="grp">{(['exceptions', 'all'] as const).map(g => <button key={g} className={`chip btn ${group === g ? 'on' : ''}`} onClick={() => setGroup(g)}>{g.toUpperCase()}</button>)}{toggleMap && <button className={`chip btn ${onMap ? 'on' : ''}`} onClick={toggleMap} title="S4 health on every site of the picture">ON MAP</button>}</span>
    </div>
    {site && <div className="site-filter">AT <b>{site.name}</b>{site.s4_status && statusChip(site.s4_status)}<button className="mini" onClick={onClearSite}>ALL SITES</button></div>}
    <Question q={group === 'exceptions' ? 'What is below the line' : 'Every line'} count={`${supplies.length}${group === 'exceptions' ? ` of ${board.supplies.length}` : ''}`} />
    <ul className="list">
      {supplies.length === 0 && <li className="row dim small">All lines at or above required.</li>}
      {supplies.map(x => (
        <li key={x.id} className={`row supply ${x.status}`} onClick={() => canEdit && setOnHand(x)} title={x.note || `${x.category} · updated by ${x.updated_by}`}>
          <span className={`sev ${x.status === 'green' ? 'ok' : x.status === 'amber' ? 'low' : 'critical'}`}>{x.status === 'green' ? 'OK' : x.status.slice(0, 3).toUpperCase()}</span>
          <span className="name">{x.item}<span className="dim"> · {x.location_name}</span></span>
          <span className="qty mono">{x.on_hand.toLocaleString()}<span className="dim">/{x.required.toLocaleString()} {x.unit}</span></span>
          <span className="bar small"><span style={{ width: `${Math.min(100, x.pct)}%` }} className={x.status === 'green' ? 'ok' : x.status} /></span>
        </li>))}
    </ul>
    <Question q="What is on its way" count={inbound.length} />
    <ul className="list">
      {inbound.length === 0 && <li className="row dim small">Nothing inbound.</li>}
      {inbound.map(x => <ShipmentRow key={x.id} x={x} canEdit={canEdit} busy={busy} act={act} />)}
    </ul>
  </>)
}

function ShipmentRow({ x, canEdit, busy, act }: { x: Shipment; canEdit: boolean; busy: string | null; act: (l: string, f: () => Promise<unknown>) => void }) {
  const eta = x.hours_to_eta < 0 ? `${Math.abs(Math.round(x.hours_to_eta))}h late` : x.hours_to_eta < 48 ? `ETA ${Math.round(x.hours_to_eta)}h` : `ETA ${new Date(x.eta).toUTCString().slice(5, 11)}`
  const set = (status: Shipment['status']) => act(`marking ${x.description} ${status.replace('_', ' ')}`, () => api.updateShipment(x.id, { status }))
  return (
    <li className={`row shipment two ${x.health}`} title={x.note || `${x.carrier} ${x.ref ?? ''}`}>
      <div className="l1">
        <span className={`sev ${x.health === 'green' ? 'ok' : x.health === 'amber' ? 'low' : 'critical'}`}>{x.priority === 'urgent' ? 'URG' : x.priority === 'priority' ? 'PRI' : 'RTN'}</span>
        <span className="name">{x.description}</span>
        <span className={`meta mono ${x.health !== 'green' ? 'bad' : 'dim'}`}>{x.status.replace('_', ' ').toUpperCase()} · {eta}</span>
      </div>
      <div className="l2">
        <span className="dim small">{x.quantity} → {x.to_name}{x.note && ` · ${x.note}`}</span>
        {canEdit && <span className="acts">
          {x.status !== 'in_transit' && <button className="mini" disabled={!!busy} onClick={() => set('in_transit')}>MOVING</button>}
          {x.status !== 'delayed' && <button className="mini warn" disabled={!!busy} onClick={() => set('delayed')}>DELAYED</button>}
          <button className="mini ok" disabled={!!busy} onClick={() => set('arrived')}>ARRIVED</button>
        </span>}
      </div>
    </li>)
}

export function S6Panel({ board, role, busy, act, site, onClearSite, onMap, toggleMap }: { board: S6Board | undefined; role: Role; busy: string | null; act: (l: string, f: () => Promise<unknown>) => void; site?: Location; onClearSite?: () => void; onMap?: boolean; toggleMap?: () => void }) {
  const [group, setGroup] = useState<'exceptions' | 'all'>('exceptions')
  const canEdit = S6_ROLES.includes(role)
  if (!board) return <div className="dim small" style={{ padding: 14 }}>No signal board yet.</div>
  const systems = (group === 'all' ? board.systems : board.systems.filter(x => x.health !== 'green')).filter(x => !site || x.location_id === site.id)
  const paceSites = Object.entries(board.pace).filter(([id]) => !site || id === site.id)
  const set = (x: SystemLine, status: SystemLine['status']) => {
    const note = status === 'up' ? '' : (window.prompt(`${x.name}: what is wrong?`, x.note) ?? '')
    act(`marking ${x.name} ${status}`, () => api.updateSystem(x.id, { status, ...(note ? { note } : {}) }))
  }
  return (<>
    <div className="s4-summary">
      {statusChip(board.status, `S6 ${board.status}`)}
      <span className="grp">{(['exceptions', 'all'] as const).map(g => <button key={g} className={`chip btn ${group === g ? 'on' : ''}`} onClick={() => setGroup(g)}>{g.toUpperCase()}</button>)}{toggleMap && <button className={`chip btn ${onMap ? 'on' : ''}`} onClick={toggleMap} title="S6 health on every site of the picture">ON MAP</button>}</span>
    </div>
    {site && <div className="site-filter">AT <b>{site.name}</b>{site.s6_status && statusChip(site.s6_status)}<button className="mini" onClick={onClearSite}>ALL SITES</button></div>}
    <Question q="How to reach each site" count="PACE" />
    <ul className="list pace">
      {paceSites.map(([site, p]) => (
        <li key={site} className="row">
          <span className="name">{p.location_name}</span>
          <span className="nets">{(['primary', 'alternate', 'contingency', 'emergency'] as const).map(r => (
            <span key={r} className={`net ${p.nets[r] ?? 'none'} ${p.in_use === r ? 'inuse' : ''}`} title={`${r}: ${p.nets[r] ?? 'not defined'}`}>{r[0].toUpperCase()}</span>))}</span>
          <span className="meta dim">{p.in_use ? `on ${p.in_use.toUpperCase()}` : 'NO NET'}</span>
        </li>))}
    </ul>
    <Question q={group === 'exceptions' ? 'What is down or degraded' : 'Every system'} count={`${systems.length}${group === 'exceptions' ? ` of ${board.systems.length}` : ''}`} />
    <ul className="list">
      {systems.length === 0 && <li className="row dim small">Everything up.</li>}
      {systems.map(x => (
        <li key={x.id} className={`row system ${x.health}`} title={x.note || `${x.category} · updated by ${x.updated_by}`}>
          <span className={`sev ${x.status === 'up' ? 'ok' : x.status === 'degraded' ? 'low' : 'critical'}`}>{x.status === 'up' ? 'UP' : x.status === 'degraded' ? 'DEG' : 'DOWN'}</span>
          <span className="name">{x.name}<span className="dim"> · {x.location_name}{x.pace ? ` · ${x.pace[0].toUpperCase()}` : ''}</span>{x.note && x.status !== 'up' && <div className="sub dim">{x.note}</div>}</span>
          <span className="meta mono dim">{x.hours < 48 ? `${Math.round(x.hours)}h` : `${Math.round(x.hours / 24)}d`}</span>
          {canEdit && <span className="acts">
            {x.status !== 'up' && <button className="mini ok" disabled={!!busy} onClick={() => set(x, 'up')}>UP</button>}
            {x.status !== 'degraded' && <button className="mini warn" disabled={!!busy} onClick={() => set(x, 'degraded')}>DEG</button>}
            {x.status !== 'down' && <button className="mini danger" disabled={!!busy} onClick={() => set(x, 'down')}>DOWN</button>}
          </span>}
        </li>))}
    </ul>
  </>)
}
