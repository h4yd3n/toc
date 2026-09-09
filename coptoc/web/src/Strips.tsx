// The strips under the header: the context row (where the board is, and the sun), and the roll call that takes the
// wall while it is open. Both sit above the map and below the posture bar, full width, never over S3 or the log.
import * as api from './api'
import { hhmmZ, sunState, sunTimes } from './solar'
import type { Incident, Role, RosterStatus, Selection, View } from './types'

type Act = (l: string, f: () => Promise<unknown>) => void
const fmtLat = (v: number) => `${Math.abs(v).toFixed(2)}°${v >= 0 ? 'N' : 'S'}`
const fmtLon = (v: number) => `${Math.abs(v).toFixed(2)}°${v >= 0 ? 'E' : 'W'}`

/** Where the board is cut and what the sun is doing there. BMNT and EENT are what an aviation brigade plans around. */
export function ContextRow({ view, now, label }: { view: View | undefined; now: number; label?: string }) {
  if (!view || view.center_lat == null || view.center_lon == null) return null
  const t = sunTimes(view.center_lat, view.center_lon, new Date(now))
  const state = sunState(t, new Date(now))
  return (
    <div className="ctx">
      <span className="ctx-k">{view.source === 'ao' ? 'AO' : 'BOARD'}</span>
      <span className="ctx-v">{label ?? (view.source === 'ao' ? 'declared' : 'home ground')} · {fmtLat(view.center_lat)} {fmtLon(view.center_lon)}{view.radius_km ? ` · ${Math.round(view.radius_km)} km` : ''}</span>
      <span className="ctx-sep" />
      <span className="ctx-k">BMNT</span><span className="ctx-v mono">{hhmmZ(t.bmnt)}</span>
      <span className="ctx-k">SR</span><span className="ctx-v mono">{hhmmZ(t.sunrise)}</span>
      <span className="ctx-k">SS</span><span className="ctx-v mono">{hhmmZ(t.sunset)}</span>
      <span className="ctx-k">EENT</span><span className="ctx-v mono">{hhmmZ(t.eent)}</span>
      <span className={`chip small sun-${state}`}>{state.toUpperCase()}</span>
    </div>)
}

const ROSTER_COLOR: Record<RosterStatus, string> = { unaccounted: 'dim', unreachable: 'amber', assist: 'red', injured: 'red', contacted: 'green', safe: 'green' }
const elapsed = (iso: string, now: number) => { const m = Math.max(0, Math.round((now - new Date(iso).getTime()) / 60000)); return m < 60 ? `${m}m` : `${Math.floor(m / 60)}h${String(m % 60).padStart(2, '0')}` }

/** An open roll call is the incident: it takes the wall — a bar across the top, the count, the clock, and the one action that matters. */
export function RollCallStrip({ incidents, now, role, busy, act, onSelect, selected }: { incidents: Incident[]; now: number; role: Role; busy: string | null; act: Act; onSelect: (s: Selection) => void; selected: Selection }) {
  const open = incidents.filter(i => i.status === 'open')
  if (open.length === 0) return null
  const isBC = role === 'battle_captain'
  return (
    <div className="rollcall-strip">
      {open.map(i => {
        const outstanding = i.counts.unaccounted + i.counts.unreachable
        const on = selected?.type === 'incident' && selected.id === i.id
        return (
          <div key={i.id} className={`rc ${on ? 'on' : ''}`} onClick={() => onSelect({ type: 'incident', id: i.id })}>
            <span className="rc-tag">☎ ROLL CALL</span>
            <span className="rc-title">{i.title}</span>
            <span className="rc-count"><b className={i.pct === 100 ? 'ok' : 'bad'}>{i.accounted}</b><span className="dim">/{i.total}</span></span>
            <span className="rc-bar bar big"><span className={i.pct === 100 ? 'ok' : ''} style={{ width: `${i.pct}%` }} /></span>
            <span className="rc-chips">{(['unaccounted', 'unreachable', 'assist', 'injured'] as RosterStatus[]).filter(k => i.counts[k] > 0).map(k => <span key={k} className={`chip small ${ROSTER_COLOR[k]}`}>{k.toUpperCase()} {i.counts[k]}</span>)}</span>
            <span className="rc-clock mono" title={`opened by ${i.opened_by}`}>{elapsed(i.opened_at, now)} open</span>
            <span className="rc-acts" onClick={e => e.stopPropagation()}>
              {isBC && outstanding > 0 && <button className="mini ok primary" disabled={!!busy} onClick={() => act('requesting check-ins', () => api.requestCheckins(i.id))}>📲 REQUEST CHECK-INS · {outstanding}</button>}
              <button className="mini" onClick={() => onSelect({ type: 'incident', id: i.id })}>ROSTER</button>
              {isBC && <button className="mini" disabled={!!busy} onClick={() => act('closing roll call', () => api.closeIncident(i.id))}>CLOSE</button>}
            </span>
          </div>)
      })}
    </div>)
}
