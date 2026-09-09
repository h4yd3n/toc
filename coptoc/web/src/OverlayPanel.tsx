// §3 Acetate overlay panel — toggle, solo, opacity, and outline controls for each map overlay sheet
import { useState } from 'react'
import type { OverlayItem, OverlayId, OverlayPresetId, OverlayState } from './types'

export const OVERLAY_DEFAULTS: OverlayItem[] = [
  { id: 'blue_force', label: 'BLUE FORCE', icon: '◆', enabled: true, opacity: 1, outlineOnly: false },
  { id: 'threat',     label: 'THREAT',     icon: '◎', enabled: true, opacity: 1, outlineOnly: false },
  { id: 'sigacts',    label: 'SIGACTS',    icon: '☎', enabled: true, opacity: 1, outlineOnly: false },
  { id: 'routes',     label: 'ROUTES',     icon: '↗', enabled: true, opacity: 1, outlineOnly: false },
  { id: 'events',     label: 'EVENTS',     icon: '★', enabled: true, opacity: 1, outlineOnly: false },
  { id: 's4',         label: 'S4 LOG',     icon: '▦', enabled: false, opacity: 1, outlineOnly: false },
  { id: 's6',         label: 'S6 SIG',     icon: '⚡', enabled: false, opacity: 1, outlineOnly: false },
  { id: 'restricted', label: 'RESTRICTED', icon: '⚿', enabled: false, opacity: 1, outlineOnly: false },
]

export const PRESETS: { id: OverlayPresetId; label: string; hint: string; apply: (base: OverlayItem[]) => { overlays: OverlayItem[]; soloId: OverlayId | null } }[] = [
  { id: 'cop', label: 'COP', hint: 'All overlays at full', apply: base => ({
    overlays: base.map(o => ({ ...o, enabled: o.id !== 's4' && o.id !== 's6' && o.id !== 'restricted', opacity: 1, outlineOnly: false })), soloId: null }) },
  { id: 's2_sittemp', label: 'S2 SITTEMP', hint: 'Threat picture only', apply: base => ({
    overlays: base.map(o => ({ ...o, enabled: true, opacity: (o.id === 'threat' || o.id === 'sigacts') ? 1 : 0.15, outlineOnly: false })), soloId: null }) },
  { id: 's2_light', label: 'S2 LIGHT', hint: 'Threat outlines + blue force', apply: base => ({
    overlays: base.map(o => ({ ...o, enabled: o.id !== 's4' && o.id !== 's6' && o.id !== 'restricted',
      opacity: (o.id === 'threat') ? 1 : (o.id === 'blue_force') ? 0.5 : 0.1,
      outlineOnly: o.id === 'threat' })), soloId: null }) },
  { id: 's3_maneuver', label: 'S3 MANEUVER', hint: 'Units + routes + events', apply: base => ({
    overlays: base.map(o => ({ ...o, enabled: true,
      opacity: (o.id === 'blue_force' || o.id === 'routes' || o.id === 'events') ? 1 : 0.12,
      outlineOnly: o.id === 'threat' })), soloId: null }) },
  { id: 's4_sustain', label: 'S4 SUST', hint: 'Blue force + logistics', apply: base => ({
    overlays: base.map(o => ({ ...o, enabled: true,
      opacity: (o.id === 'blue_force' || o.id === 's4' || o.id === 'routes') ? 1 : 0.1, outlineOnly: false })), soloId: null }) },
  { id: 's6_comms', label: 'S6 COMMS', hint: 'Blue force + signal', apply: base => ({
    overlays: base.map(o => ({ ...o, enabled: true,
      opacity: (o.id === 'blue_force' || o.id === 's6') ? 1 : 0.1, outlineOnly: false })), soloId: null }) },
  { id: 'clean', label: 'CLEAN', hint: 'Basemap only', apply: base => ({
    overlays: base.map(o => ({ ...o, enabled: false })), soloId: null }) },
]

/** Resolve the effective opacity for an overlay, accounting for solo mode. */
export function effectiveOpacity(ov: OverlayItem, soloId: OverlayId | null): number {
  if (!ov.enabled) return 0
  if (soloId && soloId !== ov.id) return 0.08
  return ov.opacity
}

/** Derive the legacy Layers boolean bag from the new OverlayState for backward-compat code paths. */
export function toLayers(state: OverlayState): import('./types').Layers {
  const get = (id: OverlayId) => state.overlays.find(o => o.id === id)
  return {
    locations: (get('blue_force')?.enabled ?? true),
    travelers: (get('blue_force')?.enabled ?? true),
    threats: (get('threat')?.enabled ?? true),
    routes: (get('routes')?.enabled ?? true),
    events: (get('events')?.enabled ?? true),
    residences: (get('restricted')?.enabled ?? false),
    s4: (get('s4')?.enabled ?? false),
    s6: (get('s6')?.enabled ?? false),
  }
}

interface Props {
  state: OverlayState
  onChange: (s: OverlayState) => void
  activePreset: OverlayPresetId | null
  onPreset: (id: OverlayPresetId) => void
  restrictedDenied?: boolean
}

export default function OverlayPanel({ state, onChange, activePreset, onPreset, restrictedDenied }: Props) {
  const [collapsed, setCollapsed] = useState(false)

  const toggle = (id: OverlayId) => {
    if (id === 'restricted' && restrictedDenied) return
    onChange({ ...state, overlays: state.overlays.map(o => o.id === id ? { ...o, enabled: !o.enabled } : o) })
  }

  const solo = (id: OverlayId) => {
    onChange({ ...state, soloId: state.soloId === id ? null : id })
  }

  const setOpacity = (id: OverlayId, opacity: number) => {
    onChange({ ...state, overlays: state.overlays.map(o => o.id === id ? { ...o, opacity } : o) })
  }

  const toggleOutline = (id: OverlayId) => {
    onChange({ ...state, overlays: state.overlays.map(o => o.id === id ? { ...o, outlineOnly: !o.outlineOnly } : o) })
  }

  if (collapsed) return (
    <div className="overlay-panel collapsed">
      <button className="ov-toggle-btn" onClick={() => setCollapsed(false)} title="Overlays">▣</button>
    </div>
  )

  const hasFill = (id: OverlayId) => id === 'threat' || id === 'sigacts'

  return (
    <div className="overlay-panel">
      <button className="ov-toggle-btn" onClick={() => setCollapsed(true)} title="Collapse">✕</button>
      <div className="ov-head" onClick={() => setCollapsed(true)}>OVERLAYS</div>
      <div className="ov-preset">
        {PRESETS.map(p => (
          <button key={p.id} className={activePreset === p.id ? 'active' : ''} onClick={() => onPreset(p.id)} title={p.hint}>{p.label}</button>
        ))}
      </div>
      {state.soloId && <div className="solo-indicator">SOLO: {state.overlays.find(o => o.id === state.soloId)?.label} — click again to un-solo</div>}
      {state.overlays.map(ov => {
        const dimmed = state.soloId != null && state.soloId !== ov.id
        const denied = ov.id === 'restricted' && restrictedDenied
        return (
          <div key={ov.id} className={`ov-row${dimmed ? ' dimmed' : ''}${denied ? ' denied' : ''}`}>
            <span className={`ov-dot${ov.enabled ? '' : ' off'}`} onClick={() => toggle(ov.id)} title={ov.enabled ? 'Hide' : 'Show'} />
            <span className="ov-label" onClick={() => toggle(ov.id)}>{ov.icon} {ov.label}{denied ? ' · DENIED' : ''}</span>
            {ov.enabled && !denied && <>
              <input type="range" className="ov-slider" min={0} max={100} value={Math.round(ov.opacity * 100)}
                onChange={e => setOpacity(ov.id, +e.target.value / 100)} title={`Opacity: ${Math.round(ov.opacity * 100)}%`} />
              {hasFill(ov.id) && <button className={`ov-outline${ov.outlineOnly ? ' on' : ''}`} onClick={() => toggleOutline(ov.id)} title="Outline only">○</button>}
              <button className={`ov-outline${state.soloId === ov.id ? ' on' : ''}`} onClick={() => solo(ov.id)} title="Solo this overlay">S</button>
            </>}
          </div>
        )
      })}
    </div>
  )
}
