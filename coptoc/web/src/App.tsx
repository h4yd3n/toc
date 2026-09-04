import { useCallback, useEffect, useMemo, useState } from 'react'
import MapView from './MapView'
import { BriefPanel, EstimateLine, WatchChip } from './Watch'
import { RequirementsPanel } from './Requirements'
import { CasesPanel } from './Cases'
import { AreaPanel } from './Area'
import { IntsumPanel } from './Intsum'
import { DistributionBox, OperationPanel } from './Operation'
import { FlashStrip, WarningsSection } from './Warnings'
import { ImportDrawer, PlanningPanel } from './Planning'
import * as api from './api'
import type { Assessment, CopEvent, Incident, Layers, Location, Person, Role, RosterStatus, Selection, Snapshot, Threat, Trip } from './types'

const TYPE_LABEL: Record<string, string> = { hq: 'HQ', office: 'OFFICE', datacenter: 'DATA CENTER', residence: 'RESIDENCE', venue: 'VENUE' }
const LOG_LABEL: Record<string, string> = {
  'cop.trip.created': 'TRIP', 'cop.trip.updated': 'TRIP', 'cop.trip.cancelled': 'TRIP', 'cop.event.created': 'EVENT', 'cop.event.updated': 'EVENT',
  'cop.event.attendees_added': 'EVENT', 'cop.event.attendee_removed': 'EVENT', 'cop.event.cancelled': 'EVENT', 'cop.person.checkin': 'CHECK-IN',
  'cop.person.shift': 'SHIFT', 'cop.location.posture': 'POSTURE', 'cop.threat.link_confirmed': 'S2 LINK', 'cop.threat.link_removed': 'S2 LINK',
  's2.requirement.created': 'S2 REQ', 's2.requirement.updated': 'S2 REQ', 's2.requirements.synced': 'S2 SYNC', 's2.source.updated': 'SOURCE',
  'cop.watch.taken': 'WATCH', 'cop.watch.handover': 'HANDOVER', 'cop.watch.acknowledged': 'HANDOVER', 'cop.watch.estimate': 'ESTIMATE', 'cop.watch.config': 'WATCH',
  'cop.pir.created': 'PIR', 'cop.pir.updated': 'PIR', 'cop.incident.opened': 'ROLL CALL', 'cop.incident.contact': 'CONTACT', 'cop.incident.closed': 'ROLL CALL', 'cop.incident.checkins_requested': 'CHECK-IN REQ', 'cop.incident.escalated': 'ESCALATED', 'cop.incident.roster_added': 'ROSTER +', 'cop.comms.inbound': 'SMS IN', 's2.warning.suggested': 'WARN?', 's2.warning.drafted': 'WARN', 's2.warning.released': 'FLASH', 's2.warning.cancelled': 'WARN ✗', 's2.product.disseminated': 'SENT', 's2.product.acknowledged': 'ACK', 'cop.comms.inbound_unmatched': 'SMS ?', 'cop.assessment.drafted': 'S2 DRAFT', 'cop.assessment.status': 'S2', 'cop.intel.refresh': 'COLLECT', 'cop.intel.refresh_failed': 'COLLECT ✗',
}

function rel(iso: string | null, now: number): string {
  if (!iso) return '—'
  const d = (new Date(iso).getTime() - now) / 1000
  const a = Math.abs(d), s = d < 0 ? ' ago' : '', p = d < 0 ? '' : 'in '
  if (a < 3600) return `${p}${Math.round(a / 60)}m${s}`
  if (a < 86400) return `${p}${Math.round(a / 3600)}h${s}`
  return `${p}${Math.round(a / 86400)}d${s}`
}
const clock = (d: Date) => d.toISOString().slice(11, 19) + 'Z'
const short = (s: string) => s.split(',')[0]

type ById = { loc: Map<string, Location>; person: Map<string, Person>; threat: Map<string, Threat>; trip: Map<string, Trip>; event: Map<string, CopEvent>; incident: Map<string, Incident> }
const ROSTER_COLOR: Record<RosterStatus, string> = { unaccounted: 'dim', unreachable: 'amber', assist: 'red', injured: 'red', contacted: 'green', safe: 'green' }

type UiPrefs = { labels: 'full' | 'lean'; header: 'counters' | 'posture' }
const UI_DEFAULTS: UiPrefs = { labels: 'lean', header: 'posture' }

export default function App() {
  const [snap, setSnap] = useState<Snapshot | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [sel, setSel] = useState<Selection>(null)
  // Decision 1: restricted layer is OFF by default. Toggling it re-fetches with restricted=true.
  // The wall: the map has the room; S1 and S2 live on rails and slide out over the map, never over S3 or the log.
  // Labels and the header are toggles under DISPLAY, persisted per browser.
  const [ui, setUi] = useState<UiPrefs>(() => { try { return { ...UI_DEFAULTS, ...JSON.parse(localStorage.getItem('toc.ui') || '{}') } } catch { return UI_DEFAULTS } })
  const [openPanel, setOpenPanel] = useState<'left' | 'right' | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  useEffect(() => { try { localStorage.setItem('toc.ui', JSON.stringify(ui)) } catch { /* private mode */ } }, [ui])
  const [layers, setLayers] = useState<Layers>({ locations: true, travelers: true, threats: true, routes: true, events: true, residences: false })
  const [now, setNow] = useState(Date.now())
  const [role, setRole] = useState<Role>(api.session.role)
  const [showBrief, setShowBrief] = useState(false)
  const [areaId, setAreaId] = useState<string | null>(null)
  const [showIntsum, setShowIntsum] = useState(false)
  const [opId, setOpId] = useState<string | null>(null)
  const [showPlan, setShowPlan] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [briefReload, setBriefReload] = useState(0)

  const load = useCallback(() => api.fetchSnapshot(layers.residences).then(s => { setSnap(s); setErr(null) }).catch(e => setErr(String(e))), [layers.residences])
  useEffect(() => { api.session.role = role; load() }, [role, load])
  useEffect(() => { load(); const t = setInterval(load, 30_000); return () => clearInterval(t) }, [load])
  useEffect(() => { const c = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(c) }, [])

  const byId = useMemo<ById>(() => ({
    loc: new Map(snap?.locations.map(l => [l.id, l]) ?? []), person: new Map(snap?.people.map(p => [p.id, p]) ?? []),
    threat: new Map(snap?.threats.map(t => [t.id, t]) ?? []), trip: new Map(snap?.trips.map(t => [t.id, t]) ?? []),
    event: new Map(snap?.events.map(e => [e.id, e]) ?? []), incident: new Map(snap?.incidents.map(i => [i.id, i]) ?? []),
  }), [snap])

  const act = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(label)
    try { await fn(); await load(); setBriefReload(n => n + 1) } catch (e) { setErr(String(e)) } finally { setBusy(null) }
  }
  const toggle = (k: keyof Layers) => setLayers(l => ({ ...l, [k]: !l[k] }))
  const s = snap?.summary
  const travelers = snap?.people.filter(p => p.status === 'traveling') ?? []

  return (
    <div className={`wall posture-${s?.posture ?? 'normal'} ${(s?.flash ?? 0) > 0 ? 'has-flash' : ''} labels-${ui.labels} header-${ui.header} ${openPanel ? 'panel-' + openPanel : ''}`}>
      <header className="top">
        <div className="brand"><img className="glyph" src="/mark.svg" alt="" /><span className="mark">TOC</span><span className="sub">COMMON OPERATING PICTURE</span></div>
        <div className={`posture-chip ${s?.posture ?? ''}`}>POSTURE · {(s?.posture ?? '—').toUpperCase()}</div>
        <WatchChip w={snap?.watch} onOpen={() => setShowBrief(v => !v)} />
        <div className="stats">
          <Stat label="PERSONNEL" v={s?.total_people} /><Stat label="PRESENT" v={s?.present} />
          <Stat label="TRAVELING" v={s?.traveling} accent="blue" /><Stat label="VIP OUT" v={s?.vips_traveling} accent="gold" />
          <Stat label="CHECKED IN" v={s?.checked_in_fresh} accent="green" /><Stat label="SEC ON SHIFT" v={s?.security_on_shift} accent="green" />
          <Stat label="THREATS" v={s?.active_threats} accent="red" /><Stat label="CONFIRMED" v={s?.confirmed_links} accent="red" />
          {(s?.unaccounted ?? 0) > 0 && <Stat label="UNACCOUNTED" v={s?.unaccounted} accent="red" />}
          {(s?.flash ?? 0) > 0 && <Stat label="FLASH" v={s?.flash} accent="red" />}
          {(s?.unreachable ?? 0) > 0 && <Stat label="UNREACHABLE" v={s?.unreachable} accent="red" />}
          <Stat label="OPEN PIRs" v={s?.open_pirs} accent="amber" /><Stat label="EVENTS" v={s?.upcoming_events} />
        </div>
        <select className="role" value={role} onChange={e => setRole(e.target.value as Role)} title="Demo identity — production uses the session">
          <option value="battle_captain">Battle Captain</option><option value="ep">Executive Protection</option><option value="security">Security</option><option value="analyst">S2 Analyst</option><option value="ea">Executive Assistant</option>
        </select>
        <button className="gear" title="Labels and header options" onClick={() => setShowSettings(v => !v)}>DISPLAY ▾</button>
        <div className="clock">{clock(new Date(now))}</div>
        {showSettings && <div className="settings" onClick={e => e.stopPropagation()}>
          <div className="s-row"><span>LABELS</span>{(['full', 'lean'] as const).map(m => <button key={m} className={`chip btn ${ui.labels === m ? 'on' : ''}`} onClick={() => setUi({ ...ui, labels: m })}>{m.toUpperCase()}</button>)}<span className="dim small">LEAN drops hints, empty lines, second lines</span></div>
          <div className="s-row"><span>HEADER</span>{(['counters', 'posture'] as const).map(m => <button key={m} className={`chip btn ${ui.header === m ? 'on' : ''}`} onClick={() => setUi({ ...ui, header: m })}>{m.toUpperCase()}</button>)}<span className="dim small">POSTURE: one big posture tile, five counters</span></div>
        </div>}
      </header>
      <FlashStrip warnings={snap?.warnings ?? []} role={role} busy={busy} act={act} onSelect={setSel} reload={briefReload} />

      <nav className="rail rail-left">
        <button className={`rail-btn ${openPanel === 'left' ? 'on' : ''}`} onClick={() => setOpenPanel(openPanel === 'left' ? null : 'left')} title="S1 Personnel">S1</button>
        {snap && snap.incidents.some(i => i.status === 'open') && <button className="rail-btn alert" onClick={() => setOpenPanel('left')} title="open roll calls">S6</button>}
      </nav>
      <nav className="rail rail-right">
        <button className={`rail-btn ${openPanel === 'right' ? 'on' : ''}`} onClick={() => setOpenPanel(openPanel === 'right' ? null : 'right')} title="S2 Intelligence">S2{(s?.warnings_pending ?? 0) > 0 && <i className="badge">{s?.warnings_pending}</i>}</button>
      </nav>
      <aside className={`left ${openPanel === 'left' ? 'open' : ''}`}>
        <PanelHead code="S1" title="PERSONNEL" hint="Blue Force">{['battle_captain', 'ea', 'security', 'analyst'].includes(role) && <button className="mini" onClick={() => setShowImport(v => !v)} title="paste an export from the systems of record">IMPORT</button>}</PanelHead>
        {showImport && <ImportDrawer busy={busy} act={act} onDone={() => setShowImport(false)} />}
        <EstimateLine e={snap?.estimates.find(e => e.section === 'S1')} role={role} busy={busy} act={act} />
        <div className="layer-toggles">
          {(['locations', 'travelers', 'routes', 'threats', 'events'] as (keyof Layers)[]).map(k => (
            <button key={k} className={`tog ${layers[k] ? 'on' : ''}`} onClick={() => toggle(k)}>{k}</button>))}
          <button className={`tog restricted ${layers.residences ? (snap?.restricted_denied ? 'denied' : 'on') : ''}`} onClick={() => toggle('residences')} title={snap?.restricted_denied ? 'Restricted layer — your role is not cleared (Battle Captain / EP only)' : 'Restricted layer — off by default'}>⚿ residences{layers.residences && snap?.restricted_denied ? ' · DENIED' : ''}</button>
        </div>
        {snap && snap.incidents.filter(i => i.status === 'open').length > 0 && <>
          <SectionLabel><span className="s6">S6 · ROLL CALLS</span></SectionLabel>
          <EstimateLine e={snap?.estimates.find(e => e.section === 'S6')} role={role} busy={busy} act={act} />
          <ul className="list">
            {snap.incidents.filter(i => i.status === 'open').map(i => (
              <li key={i.id} className={`row rollcall ${sel?.type === 'incident' && sel.id === i.id ? 'active' : ''}`} onClick={() => setSel({ type: 'incident', id: i.id })}>
                <div className="rc-head"><span className="name">☎ {i.title}</span><span className={`meta ${i.pct === 100 ? 'ok' : 'bad'}`}>{i.accounted}/{i.total}</span></div>
                <div className="bar"><span style={{ width: `${i.pct}%` }} className={i.pct === 100 ? 'ok' : ''} /></div>
              </li>))}
          </ul>
        </>}
        <SectionLabel>LOCATIONS</SectionLabel>
        <ul className="list">
          {snap?.locations.map(l => (
            <li key={l.id} className={`row ${sel?.type === 'location' && sel.id === l.id ? 'active' : ''}`} onClick={() => setSel({ type: 'location', id: l.id })}>
              <span className={`dot posture-${l.effective_posture}`} />
              <span className="name">{l.name}{l.sensitivity === 'restricted' && <span className="lock">⚿</span>}</span>
              {l.confirmed_threat_ids.length > 0 ? <span className="tbadge confirmed" title="confirmed threat link">▲{l.confirmed_threat_ids.length}</span>
                : l.threat_ids_in_area.length > 0 ? <span className="tbadge" title="threat in area — unconfirmed">△{l.threat_ids_in_area.length}</span> : null}
              <span className="meta">{l.present}<span className="dim">/{l.assigned}</span>{l.security_on_shift ? <span className="sec"> ·{l.security_on_shift}⛨</span> : null}</span>
            </li>))}
        </ul>
        <SectionLabel>TRAVELING <span className="dim">{travelers.length}</span></SectionLabel>
        <ul className="list">
          {travelers.map(p => (
            <li key={p.id} className={`row ${sel?.type === 'person' && sel.id === p.id ? 'active' : ''}`} onClick={() => setSel({ type: 'person', id: p.id })}>
              <span className={`dot ${p.confirmed_threat_ids.length ? 'red' : 'blue'}`} />
              <span className="name">{p.is_vip && <span className="vipstar">★</span>}{p.name}</span>
              <Presence p={p} />
              <span className="meta dim">{short(byId.trip.get(p.trip_id ?? '')?.dest_name ?? '')}</span>
            </li>))}
        </ul>
      </aside>

      <main className="center" onClick={() => { setOpenPanel(null); setShowSettings(false) }}>
        <MapView snapshot={snap} selection={sel} layers={layers} onSelect={setSel} />
        {showPlan && <PlanningPanel role={role} busy={busy} act={act} onClose={() => setShowPlan(false)} onSelect={s => { setSel(s); setShowPlan(false) }} reload={briefReload} />}
        {opId && !showPlan && <OperationPanel id={opId} role={role} busy={busy} act={act} onClose={() => setOpId(null)} reload={briefReload} />}
        {showIntsum && !opId && <IntsumPanel role={role} busy={busy} act={act} onClose={() => setShowIntsum(false)} reload={briefReload} />}
        {areaId && !showIntsum && !opId && <AreaPanel id={areaId} role={role} busy={busy} act={act} onClose={() => setAreaId(null)} reload={briefReload} />}
        {sel && snap && !showBrief && !areaId && !showIntsum && !opId && !showPlan && <Detail sel={sel} snap={snap} byId={byId} now={now} busy={busy} act={act} onClose={() => setSel(null)} onSelect={setSel} onOp={setOpId} role={role} />}
        {showBrief && <BriefPanel role={role} busy={busy} act={act} onClose={() => setShowBrief(false)} reload={briefReload} />}
        {err && <div className="error" onClick={() => setErr(null)}>{err}</div>}
        {!snap && !err && <div className="loading">LOADING PICTURE…</div>}
        {busy && <div className="loading">{busy.toUpperCase()}…</div>}
      </main>

      <aside className={`right ${openPanel === 'right' ? 'open' : ''}`}>
        <PanelHead code="S2" title="INTELLIGENCE" hint="Sigtoc">
          <button className="mini" onClick={() => { setShowIntsum(v => !v); setAreaId(null); setShowBrief(false) }} title="The daily INTSUM (Decision G)">INTSUM</button>
          <button className="mini" disabled={!!busy} onClick={() => act('collecting from every live source', api.refreshIntel)} title="Run every enabled, configured collector">⟳ COLLECT</button>
        </PanelHead>
        <EstimateLine e={snap?.estimates.find(e => e.section === 'S2')} role={role} busy={busy} act={act} />
        <WarningsSection warnings={snap?.warnings ?? []} role={role} busy={busy} act={act} onSelect={setSel} />
        <RequirementsPanel reload={briefReload} busy={busy} act={act} onSelect={setSel} role={role} onArea={id => { setAreaId(id); setShowBrief(false) }} />
        <CasesPanel reload={briefReload} busy={busy} act={act} role={role} onChanged={() => setBriefReload(n => n + 1)} />
        <SectionLabel>THREATS <span className="dim">{snap?.threats.length ?? 0} · {s?.real_threats ?? 0} live</span></SectionLabel>
        <ul className="list">
          {snap?.threats.map(t => (
            <li key={t.id} className={`row ${sel?.type === 'threat' && sel.id === t.id ? 'active' : ''}`} onClick={() => setSel({ type: 'threat', id: t.id })}>
              <span className={`sev ${t.severity}`}>{t.severity.slice(0, 3).toUpperCase()}</span>
              <span className="name">{t.title}</span>
              {!t.synthetic && <span className="chip live">LIVE</span>}
              {t.confirmed_links.length > 0 && <span className="tbadge confirmed">▲{t.confirmed_links.length}</span>}
              <span className="meta dim">{rel(t.observed_at, now)}</span>
            </li>))}
        </ul>
        <SectionLabel>ASSESSMENTS</SectionLabel>
        <ul className="list cards">
          {snap?.assessments.map(a => (
            <li key={a.id} className={`card ${a.confidence === 'insufficient' ? 'gap' : ''}`}>
              <div className="card-head"><span className="id">{a.id}</span><span className="name">{a.title}</span><span className={`chip ${a.status}`}>{a.status.toUpperCase()}</span></div>
              {a.confidence === 'insufficient'
                ? <div className="est"><b className="gapword">COLLECTION GAP</b> · <span className="dim">refused to assess</span></div>
                : <div className="est"><b>{a.likelihood}</b> <span className="dim">({a.band})</span> · <span className={`conf ${a.confidence}`}>{a.confidence} confidence</span></div>}
              <div className="bluf">{a.bluf}</div>
              <AssessmentActions a={a} busy={busy} act={act} />
            </li>))}
        </ul>
        <SectionLabel>PIRs <span className="dim">{s?.open_pirs ?? 0} open</span></SectionLabel>
        <ul className="list cards">
          {snap?.pirs.map(p => (
            <li key={p.id} className="card pir" onClick={() => p.subject_type && p.subject_id && byId[p.subject_type === 'trip' ? 'trip' : p.subject_type === 'event' ? 'event' : p.subject_type === 'location' ? 'loc' : 'person'].has(p.subject_id) && setSel(p.subject_type === 'trip' ? { type: 'person', id: byId.trip.get(p.subject_id)!.person_id } : { type: p.subject_type as 'event' | 'location' | 'person', id: p.subject_id })}>
              <div className="card-head"><span className="id">{p.id}</span><span className="prio">P{p.priority}</span><span className={`chip ${p.status.toLowerCase()}`}>{p.status}</span></div>
              <div className="q">{p.question}</div>
            </li>))}
        </ul>
      </aside>

      <footer className="bottom">
        <div className="s3">
          <PanelHead code="S3" title="OPERATIONS" hint="Events · Travel" inline><button className="mini" onClick={() => { setShowPlan(v => !v); setOpId(null); setShowBrief(false) }} title="the next 90 days by week, coverage per event">PLAN 90d</button></PanelHead>
          <EstimateLine e={snap?.estimates.find(e => e.section === 'S3')} role={role} busy={busy} act={act} />
          <div className="timeline">
            {snap?.events.map(e => (
              <div key={e.id} className={`trip event ${sel?.type === 'event' && sel.id === e.id ? 'active' : ''}`} onClick={() => setSel({ type: 'event', id: e.id })}>
                <div className="trip-head"><span className="chip event">{e.status === 'active' ? 'LIVE' : `T-${e.days_until}d`}</span><span className="who">★ {e.name}</span>
                  {e.threat_ids_in_area.length > 0 && <span className="tbadge">△{e.threat_ids_in_area.length}</span>}
                  {e.operation && <span className={`chip small op ${e.operation.status}`} title={e.operation.title} onClick={ev => { ev.stopPropagation(); setOpId(e.operation!.id) }}>OP {e.operation.tasks_done}/{e.operation.tasks_total}</span>}</div>
                <div className="route">{short(e.venue_name)}</div>
                <div className="when dim">{new Date(e.start_at).toUTCString().slice(5, 16)} → {new Date(e.end_at).toUTCString().slice(5, 16)}</div>
                <div className="purpose">{e.attendee_count} attending · {e.vip_count} VIP · {e.security_count} sec · {e.trips_generated} trips</div>
              </div>))}
            {snap?.trips.map(t => (
              <div key={t.id} className={`trip ${t.status} ${sel?.type === 'person' && sel.id === t.person_id ? 'active' : ''}`} onClick={() => setSel({ type: 'person', id: t.person_id })}>
                <div className="trip-head"><span className={`chip ${t.status}`}>{t.status.toUpperCase()}</span><span className="who">{t.is_vip && <span className="vipstar">★</span>}{t.person_name}</span>
                  {t.event_id && <span className="chip event small">EVT</span>}
                  {t.operation && <span className={`chip small op ${t.operation.status}`} title={t.operation.title} onClick={ev => { ev.stopPropagation(); setOpId(t.operation!.id) }}>OP {t.operation.tasks_done}/{t.operation.tasks_total}</span>}</div>
                <div className="route">{t.origin_name.split(' ')[0]} <span className="arrow">→</span> {short(t.dest_name)}</div>
                <div className="when dim">dep {rel(t.depart_at, now)} · ret {rel(t.return_at, now)}</div>
                <div className="purpose">{t.purpose}</div>
              </div>))}
          </div>
        </div>
        <div className="oplog">
          <PanelHead code="LOG" title="BATTLE LOG" hint="hash-chained" inline />
          <ul className="logs">
            {snap?.log.map(e => (
              <li key={e.id} className={`log ${e.actor_type}`}>
                <span className="lt dim">{rel(e.at, now)}</span><span className="lk">{LOG_LABEL[e.type] ?? e.type}</span>
                <span className="ls">{e.summary}</span><span className="la dim">{e.actor}</span>
              </li>))}
            {snap && snap.log.length === 0 && <li className="log"><span className="ls dim">No actions recorded yet.</span></li>}
          </ul>
        </div>
      </footer>
    </div>
  )
}

function Presence({ p }: { p: Person }) {
  if (p.position_source === 'checkin') return <span className="chk fresh" title={p.last_checkin_note ?? ''}>✓{p.checkin_age_h !== null && p.checkin_age_h < 1 ? '<1h' : `${Math.round(p.checkin_age_h ?? 0)}h`}</span>
  if (p.checkin_stale) return <span className="chk stale" title="last check-in older than 12h">stale</span>
  return null
}
function AssessmentActions({ a, busy, act }: { a: Assessment; busy: string | null; act: (l: string, f: () => Promise<unknown>) => void }) {
  if (a.status === 'approved' || a.status === 'superseded') return <div className="card-foot dim">{a.status === 'approved' ? `approved by ${a.approved_by}` : 'superseded'} · {a.author}</div>
  return (
    <div className="card-foot">
      <span className="dim">{a.author}</span>
      {a.status === 'draft' && <button className="mini" disabled={!!busy} onClick={e => { e.stopPropagation(); act('sending to review', () => api.setAssessmentStatus(a.id, 'review')) }}>→ REVIEW</button>}
      {a.status === 'review' && a.confidence !== 'insufficient' && <button className="mini ok" disabled={!!busy} onClick={e => { e.stopPropagation(); act('approving', () => api.setAssessmentStatus(a.id, 'approved')) }}>✓ APPROVE</button>}
      {a.confidence === 'insufficient' && <span className="dim">cannot be approved</span>}
    </div>)
}
function Stat({ label, v, accent }: { label: string; v?: number; accent?: string }) {
  // data-k lets the header toggle keep five counters without changing the markup order
  return <div className={`stat ${accent ?? ''}`} data-k={label}><span className="v">{v ?? '—'}</span><span className="l">{label}</span></div>
}
function PanelHead({ code, title, hint, inline, children }: { code: string; title: string; hint?: string; inline?: boolean; children?: React.ReactNode }) {
  return <div className={`panel-head ${inline ? 'inline' : ''}`}><span className="code">{code}</span><span className="title">{title}</span>{children}{hint && <span className="hint">{hint}</span>}</div>
}
function SectionLabel({ children }: { children: React.ReactNode }) { return <div className="section-label">{children}</div> }

function Detail({ sel, snap, byId, now, busy, act, onClose, onSelect }: {
  sel: NonNullable<Selection>; snap: Snapshot; byId: ById; now: number; busy: string | null
  act: (l: string, f: () => Promise<unknown>) => void; onClose: () => void; onSelect: (s: Selection) => void
}) {
  const [addOpen, setAddOpen] = useState(false)
  const threatRows = (ids: string[], confirmed: string[], target: { type: 'location' | 'person'; id: string }) => ids.map(id => byId.threat.get(id)).filter(Boolean).map(t => (
    <li key={t!.id} className="tline" onClick={e => { e.stopPropagation(); onSelect({ type: 'threat', id: t!.id }) }}>
      <span className={`sev ${t!.severity}`}>{t!.severity.slice(0, 3).toUpperCase()}</span><span className="pname">{t!.title}</span>
      {confirmed.includes(t!.id) ? <span className="tbadge confirmed">CONFIRMED</span>
        : <button className="mini" disabled={!!busy} onClick={e => { e.stopPropagation(); act('confirming link', () => api.confirmLink(t!.id, target.type, target.id)) }}>CONFIRM</button>}
    </li>))
  const rollCallBtn = (target: { location_id?: string; threat_id?: string }) => api.session.role === 'battle_captain'
    ? <button className="mini danger" disabled={!!busy} onClick={e => { e.stopPropagation(); act('opening roll call', () => api.openRollCall(target)) }}>☎ OPEN ROLL CALL</button>
    : <span className="dim" title="Battle Captain only">☎ roll call · Battle Captain only</span>
  if (sel.type === 'incident') {
    const i = byId.incident.get(sel.id); if (!i) return null
    const open = i.status === 'open'
    return (
      <div className="detail incident" onClick={e => e.stopPropagation()}>
        <button className="close" onClick={onClose}>×</button>
        <div className="d-kicker">S6 ACCOUNTABILITY · {i.kind.toUpperCase()} · opened {rel(i.opened_at, now)} by {i.opened_by}</div>
        <div className="d-title">{i.title}</div>
        <div className="d-stats">
          <b className={i.pct === 100 ? 'ok' : 'bad'}>{i.accounted}/{i.total} accounted</b>
          {(['unaccounted', 'unreachable', 'assist', 'injured', 'safe'] as RosterStatus[]).filter(k => i.counts[k] > 0).map(k => <span key={k} className={`chip ${ROSTER_COLOR[k]}`}>{k.toUpperCase()} {i.counts[k]}</span>)}
        </div>
        <div className="bar big"><span style={{ width: `${i.pct}%` }} className={i.pct === 100 ? 'ok' : ''} /></div>
        {i.notes && <div className="kv"><span>Notes</span>{i.notes}</div>}
        <div className="d-actions">{open ? <>
            <button className="mini ok" disabled={!!busy || i.counts.unaccounted + i.counts.unreachable === 0} onClick={() => act('requesting check-ins', () => api.requestCheckins(i.id))}>📲 REQUEST CHECK-INS · SMS + CHAT ({i.counts.unaccounted + i.counts.unreachable})</button>
            <button className="mini" disabled={!!busy} onClick={() => act('closing roll call', () => api.closeIncident(i.id))}>CLOSE ROLL CALL</button>
            {i.checkins_requested > 0 && <span className="dim">{i.checkins_requested} requested · work by exception{(i.delivery_summary.sms?.simulated || i.delivery_summary.chat?.simulated) ? <span className="chip amber small" title="No Twilio / Slack credentials configured — nothing actually left the building">SIMULATED</span> : null}</span>}</>
          : <span className="chip">CLOSED {rel(i.closed_at, now)}</span>}</div>
        <div className="section-label">ROSTER <span className="dim">call every name — each attempt is logged</span>{open && <button className="mini" onClick={() => setAddOpen(v => !v)} title="Decision N: anyone on the floor may add a missed name">+ NAME</button>}</div>
        {open && addOpen && <RosterAddForm busy={busy} act={act} incidentId={i.id} people={[...byId.person.values()].filter(p => !i.roster.some(r => r.person_id === p.id))} onDone={() => setAddOpen(false)} />}
        <ul className="roster">
          {i.roster.map(r => (
            <li key={r.person_id} className={`rrow ${r.status}`}>
              <div className="rline">
                <span className={`pdot ${ROSTER_COLOR[r.status]}`} />
                <a className="pname" onClick={() => onSelect({ type: 'person', id: r.person_id })}>{r.is_vip && <span className="vipstar">★</span>}{r.name}</a>
                <span className="prole dim">{r.role}</span>
                {r.basis === 'assigned' && <span className="chip amber" title="assigned to this site but elsewhere right now">ASSIGNED · AWAY</span>}
                {r.basis === 'in_area' && <span className="chip" title="not assigned here — inside the radius">NEARBY</span>}
                {r.basis === 'manual' && <span className="chip amber" title="added by hand on the floor (Decision N)">ADDED</span>}
                {r.updated_by === 'rule:escalation-15m' && r.status === 'unreachable' && <span className="chip red small" title="no response in 15 minutes — flagged by rule (Decision M)">AUTO · 15m</span>}
                <span className={`chip ${ROSTER_COLOR[r.status]}`}>{r.status.toUpperCase()}</span>
              </div>
              <div className="rline sub">
                {r.phone && <a href={`tel:${r.phone.replace(/\s/g, '')}`} className="phone">{r.phone}</a>}
                {r.attempts > 0 && <span className="dim">{r.attempts} attempt{r.attempts === 1 ? '' : 's'} · {rel(r.last_attempt_at, now)}{r.method === 'app' ? ' · via app' : ''}</span>}
                {r.checkin_requested_at && (r.status === 'unaccounted' || r.status === 'unreachable') && <span className="chip green small">📲 requested {rel(r.checkin_requested_at, now)}</span>}
                {r.deliveries.map((d, k) => <span key={k} className={`chip small dl-${d.status}`} title={d.error ?? `${d.channel} ${d.status}`}>{d.channel === 'sms' ? '📱' : '💬'} {d.status === 'sent' ? '✓' : d.status === 'simulated' ? 'sim' : '✗'}</span>)}
                {r.note && <span className="dim note">{r.note}</span>}
              </div>
              {open && <div className="rline btns">
                {([['safe', 'SAFE', 'ok'], ['unreachable', 'NO ANSWER', 'warn'], ['assist', 'ASSIST', 'danger'], ['injured', 'INJURED', 'danger']] as const).map(([st, label, cls]) => (
                  <button key={st} className={`mini ${cls}`} disabled={!!busy} onClick={() => act('logging contact', () => api.updateRoster(i.id, r.person_id, st))}>{label}</button>))}
              </div>}
            </li>))}
        </ul>
      </div>)
  }
  const draftBtn = (subject_type: string, subject_id: string) => (
    <button className="mini s2" disabled={!!busy} onClick={e => { e.stopPropagation(); act('drafting S2 assessment', () => api.draftAssessment(subject_type, subject_id)) }}>✎ DRAFT S2 ASSESSMENT</button>)

  if (sel.type === 'location') {
    const l = byId.loc.get(sel.id); if (!l) return null
    const teams = snap.teams.filter(t => t.location_id === l.id)
    const visiting = snap.people.filter(p => p.location_id === l.id && p.home_location_id !== l.id)
    return (
      <div className="detail" onClick={e => e.stopPropagation()}>
        <button className="close" onClick={onClose}>×</button>
        <div className="d-kicker">{TYPE_LABEL[l.type]} · {l.city}, {l.country}{l.sensitivity === 'restricted' && <span className="lock"> ⚿ RESTRICTED</span>}</div>
        <div className="d-title">{l.name}</div>
        <div className="d-stats">
          <span><b>{l.present}</b> present</span><span><b>{l.assigned}</b> assigned</span><span><b>{l.security_on_shift}</b> sec on shift</span><span><b>{l.vips_present}</b> VIP</span>
        </div>
        <div className="d-stats">
          <span className="dim">posture</span>
          {(['normal', 'elevated', 'critical'] as const).map(p => (
            <button key={p} className={`chip btn ${p} ${l.posture === p ? 'on' : ''}`} disabled={!!busy} onClick={() => act('setting posture', () => api.setPosture(l.id, p, 'Set from the wall'))}>{p.toUpperCase()}</button>))}
          {l.effective_posture !== l.posture && <span className={`chip ${l.effective_posture}`} title="raised by a confirmed threat link">EFFECTIVE {l.effective_posture.toUpperCase()}</span>}
        </div>
        {(l.threat_ids_in_area.length > 0 || l.confirmed_threat_ids.length > 0) && <>
          <div className="section-label">THREATS IN AREA <span className="dim">proximity suggests · analyst confirms</span></div>
          <ul className="people">{threatRows(Array.from(new Set([...l.confirmed_threat_ids, ...l.threat_ids_in_area])), l.confirmed_threat_ids, { type: 'location', id: l.id })}</ul>
        </>}
        <div className="d-actions">{draftBtn('location', l.id)} {rollCallBtn({ location_id: l.id })}</div>
        {visiting.length > 0 && <><div className="section-label">VISITING</div>
          <ul className="people">{visiting.map(p => <PersonRow key={p.id} p={p} onClick={() => onSelect({ type: 'person', id: p.id })} />)}</ul></>}
        {teams.map(t => {
          const members = snap.people.filter(p => p.team_id === t.id); const away = members.filter(p => p.status === 'traveling').length
          return (<div key={t.id} className="team">
            <div className="team-head">{t.is_security && <span className="shield">⛨</span>}{t.name}<span className="dim"> · {members.length - away}/{members.length}{t.is_security ? ` · ${members.filter(p => p.on_shift && p.status !== 'traveling').length} on shift` : ''}</span></div>
            <ul className="people">{members.map(p => <PersonRow key={p.id} p={p} onClick={() => onSelect({ type: 'person', id: p.id })} />)}</ul>
          </div>)
        })}
      </div>)
  }
  if (sel.type === 'person') {
    const p = byId.person.get(sel.id); if (!p) return null
    const trip = p.trip_id ? byId.trip.get(p.trip_id) : undefined
    const home = byId.loc.get(p.home_location_id)
    const ev = trip?.event_id ? byId.event.get(trip.event_id) : undefined
    return (
      <div className="detail" onClick={e => e.stopPropagation()}>
        <button className="close" onClick={onClose}>×</button>
        <div className="d-kicker">{p.is_vip ? 'VIP · ' : ''}{p.team_name}</div>
        <div className="d-title">{p.is_vip && <span className="vipstar">★ </span>}{p.name}</div>
        <div className="d-sub">{p.role}</div>
        <div className="d-stats">
          <span className={`chip ${p.status === 'traveling' ? 'active' : 'normal'}`}>{p.status === 'traveling' ? 'TRAVELING' : 'AT POST'}</span>
          {p.on_shift && <span className="chip green">ON SHIFT · {p.shift_role}</span>}
          {p.position_source === 'checkin' ? <span className="chip green">CHECKED IN {p.checkin_age_h}h ago</span> : p.checkin_stale ? <span className="chip elevated">CHECK-IN STALE {Math.round(p.checkin_age_h ?? 0)}h</span> : <span className="chip">POSITION DERIVED</span>}
        </div>
        <div className="d-stats"><span className={`chip ${p.availability === 'unreachable' ? 'red' : p.availability === 'off_duty' ? 'dim' : 'green'}`} title="§4: on shift / off duty for security; unreachable when a roll call cannot reach you or a check-in went stale on the road">{p.availability.replace('_', ' ').toUpperCase()}</span>
          {p.incident_status && <span className={`chip ${ROSTER_COLOR[p.incident_status]}`}>ROLL CALL · {p.incident_status.toUpperCase()}</span>}</div>
        {p.last_checkin_note && <div className="kv"><span>Check-in</span>{p.last_checkin_note}</div>}
        {p.phone && <div className="kv"><span>Phone</span><a href={`tel:${p.phone.replace(/\s/g, '')}`}>{p.phone}</a></div>}
        {p.email && <div className="kv"><span>Email</span>{p.email}</div>}
        <div className="kv"><span>Source</span><code>{p.source}</code></div>
        <div className="kv"><span>Home</span><a onClick={() => home && onSelect({ type: 'location', id: home.id })}>{home?.name ?? '⚿ restricted'}</a></div>
        {trip && <>
          <div className="section-label">TRIP · {trip.id}{ev && <> · <a onClick={() => onSelect({ type: 'event', id: ev.id })}>{ev.name}</a></>}</div>
          <div className="kv"><span>To</span><b>{trip.dest_name}</b></div>
          <div className="kv"><span>Depart</span>{new Date(trip.depart_at).toUTCString().slice(5, 22)} <span className="dim">({rel(trip.depart_at, now)})</span></div>
          <div className="kv"><span>Return</span>{new Date(trip.return_at).toUTCString().slice(5, 22)} <span className="dim">({rel(trip.return_at, now)})</span></div>
          <div className="kv"><span>Purpose</span>{trip.purpose}</div>
          <div className="kv"><span>Source</span><code>{trip.source}</code></div>
        </>}
        {(p.threat_ids_in_area.length > 0 || p.confirmed_threat_ids.length > 0) && <>
          <div className="section-label">THREATS IN AREA</div>
          <ul className="people">{threatRows(Array.from(new Set([...p.confirmed_threat_ids, ...p.threat_ids_in_area])), p.confirmed_threat_ids, { type: 'person', id: p.id })}</ul>
        </>}
        <div className="d-actions">{trip && draftBtn('trip', trip.id)} <button className="mini ok" disabled={!!busy} onClick={() => act('checking in', () => api.checkIn(p.id, p.lat, p.lon, 'Checked in from the wall (demo)'))}>📍 CHECK IN HERE (demo)</button></div>
      </div>)
  }
  if (sel.type === 'event') {
    const e = byId.event.get(sel.id); if (!e) return null
    const att = e.attendee_ids.map(i => byId.person.get(i)).filter(Boolean) as Person[]
    return (
      <div className="detail" onClick={ev => ev.stopPropagation()}>
        <button className="close" onClick={onClose}>×</button>
        <div className="d-kicker">S3 EVENT · {e.event_type.replace('_', ' ').toUpperCase()} · {e.status === 'active' ? 'IN PROGRESS' : `T-${e.days_until} DAYS`}</div>
        <div className="d-title">{e.name}</div>
        <div className="d-sub">{e.venue_name}</div>
        <div className="d-stats"><span><b>{e.attendee_count}</b> attending</span><span><b>{e.vip_count}</b> VIP</span><span><b>{e.security_count}</b> security</span><span><b>{e.trips_generated}</b> trips generated</span></div>
        <div className="kv"><span>Window</span>{new Date(e.start_at).toUTCString().slice(5, 22)} → {new Date(e.end_at).toUTCString().slice(5, 22)}</div>
        <div className="kv"><span>Brief</span>{e.description}</div>
        <div className="kv"><span>Source</span><code>{e.source}</code></div>
        {e.security_plan && <div className="kv"><span>Sec plan</span>{e.security_plan}</div>}
        {e.coverage && <div className="kv"><span>Coverage</span><span className={e.coverage.gap > 0 ? 'bad' : 'ok'}>{e.coverage.assigned}/{e.coverage.required}</span> {e.coverage.people.map(p => `${p.name} (${p.role})`).join(', ') || 'nobody assigned'} <span className="dim">· {e.coverage.rule}</span></div>}
        {e.threat_ids_in_area.length > 0 && <><div className="section-label">THREATS IN AREA</div>
          <ul className="people">{e.threat_ids_in_area.map(id => byId.threat.get(id)).filter(Boolean).map(t => (
            <li key={t!.id} className="tline" onClick={ev => { ev.stopPropagation(); onSelect({ type: 'threat', id: t!.id }) }}><span className={`sev ${t!.severity}`}>{t!.severity.slice(0, 3).toUpperCase()}</span><span className="pname">{t!.title}</span></li>))}</ul></>}
        <div className="d-actions">{draftBtn('event', e.id)}
          {e.operation ? <button className="mini" onClick={() => onOp(e.operation!.id)}>OP · {e.operation.status.toUpperCase()} · {e.operation.tasks_done}/{e.operation.tasks_total}</button>
            : role === 'battle_captain' && <button className="mini" disabled={!!busy} title="Opens the standard task skeleton; cite an approved assessment from the S2 card to hand off a target package" onClick={() => act('opening operation', () => api.openOperation({ subject_type: 'event', subject_id: e.id }).then(o => onOp(o.id)))}>+ OPERATION</button>}</div>
        {(snap.assessments.filter(a => a.subject_type === 'event' && a.subject_id === e.id && a.status === 'approved')).map(a => <DistributionBox key={a.id} ptype="assessment" pid={a.id} role={role} busy={busy} act={act} releasable />)}
        <div className="section-label">ATTENDEES</div>
        <ul className="people">{att.map(p => <PersonRow key={p.id} p={p} onClick={() => onSelect({ type: 'person', id: p.id })} />)}</ul>
      </div>)
  }
  const t = byId.threat.get(sel.id); if (!t) return null
  return (
    <div className="detail threat" onClick={e => e.stopPropagation()}>
      <button className="close" onClick={onClose}>×</button>
      <div className="d-kicker"><span className={`sev ${t.severity}`}>{t.severity.toUpperCase()}</span> {t.synthetic ? <span className="chip synthetic">SYNTHETIC</span> : <span className="chip live">LIVE · {t.source.toUpperCase()}</span>}{t.event_type && <span className="dim"> · {t.event_type}</span>}</div>
      <div className="d-title">{t.title}</div>
      <div className="d-stats"><span>radius <b>{t.radius_km} km</b></span><span>observed <b>{rel(t.observed_at, now)}</b></span><span className={`conf ${t.confidence}`}>{t.confidence} source confidence</span></div>
      <div className="kv"><span>Source</span><code>{t.source}</code>{t.url && <a href={t.url} target="_blank" rel="noreferrer"> ↗</a>}</div>
      <div className="bluf">{t.summary}</div>
      <div className="d-actions">{rollCallBtn({ threat_id: t.id })}</div>
      {t.confirmed_links.length > 0 && <><div className="section-label">CONFIRMED LINKS</div>
        <ul className="people">{t.confirmed_links.map(l => (
          <li key={l.link_id} className="tline"><span className="tbadge confirmed">▲</span><a onClick={() => onSelect({ type: l.target_type, id: l.target_id })}>{l.target_name}</a>
            <span className="dim">{l.confirmed_by} · {rel(l.confirmed_at, now)}</span>
            <button className="mini" disabled={!!busy} onClick={() => act('removing link', () => api.removeLink(t.id, l.link_id))}>×</button></li>))}</ul></>}
      {t.suggested_targets.filter(s => !t.confirmed_links.some(c => c.target_type === s.target_type && c.target_id === s.target_id)).length > 0 && <>
        <div className="section-label">IN AREA <span className="dim">suggested by proximity — confirm to change posture</span></div>
        <ul className="people">{t.suggested_targets.filter(s => !t.confirmed_links.some(c => c.target_type === s.target_type && c.target_id === s.target_id)).map(s => (
          <li key={s.target_type + s.target_id} className="tline"><span className="tbadge">△</span><a onClick={() => onSelect({ type: s.target_type, id: s.target_id })}>{s.target_name}</a>
            <button className="mini" disabled={!!busy} onClick={() => act('confirming link', () => api.confirmLink(t.id, s.target_type, s.target_id))}>CONFIRM</button></li>))}</ul></>}
    </div>)
}
function PersonRow({ p, onClick }: { p: Person; onClick: () => void }) {
  return (
    <li className={`person ${p.status}`} onClick={onClick}>
      <span className={`pdot ${p.status === 'traveling' ? 'away' : p.on_shift ? 'shift' : ''}`} />
      <span className="pname">{p.is_vip && <span className="vipstar">★</span>}{p.name}</span>
      <Presence p={p} />
      {p.incident_status && <span className={`chip ${ROSTER_COLOR[p.incident_status]}`}>{p.incident_status.toUpperCase()}</span>}
      <span className="prole dim">{p.status === 'traveling' ? 'away' : p.on_shift ? p.shift_role : p.role}</span>
    </li>)
}


function RosterAddForm({ busy, act, incidentId, people, onDone }: { busy: string | null; act: (l: string, f: () => Promise<unknown>) => void; incidentId: string; people: Person[]; onDone: () => void }) {
  const [f, setF] = useState({ person_id: '', name: '', phone: '', role: 'Visitor', note: '' })
  const ok = f.person_id || f.name.trim()
  return (
    <div className="dform" onClick={e => e.stopPropagation()}>
      <div className="dform-head">ADD A MISSED NAME <span className="dim">visitor, contractor, or someone the picture missed · tagged manual · logged</span></div>
      <select value={f.person_id} onChange={e => setF({ ...f, person_id: e.target.value, name: '' })}><option value="">— not in the directory —</option>{people.slice(0, 200).map(p => <option key={p.id} value={p.id}>{p.name} · {p.role}</option>)}</select>
      {!f.person_id && <>
        <div className="two"><input placeholder="Name" value={f.name} onChange={e => setF({ ...f, name: e.target.value })} /><input placeholder="Phone" value={f.phone} onChange={e => setF({ ...f, phone: e.target.value })} /></div>
        <input placeholder="Role (e.g. Contractor — HVAC)" value={f.role} onChange={e => setF({ ...f, role: e.target.value })} /></>}
      <input placeholder="Note (where seen)" value={f.note} onChange={e => setF({ ...f, note: e.target.value })} />
      <div className="row-btns"><button className="mini ok" disabled={!!busy || !ok} onClick={() => { act('adding to roster', () => api.addToRoster(incidentId, f.person_id ? { person_id: f.person_id, note: f.note || undefined } : { name: f.name, phone: f.phone || undefined, role: f.role || undefined, note: f.note || undefined })); onDone() }}>ADD</button>
        <button className="mini" onClick={onDone}>CANCEL</button></div>
    </div>)
}
