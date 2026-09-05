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
import { Timeline } from './Timeline'
import { S4Panel, S6Panel } from './Sections'
import { TaskOrg } from './TaskOrg'
import { SettingsPanel } from './Settings'
import { UsersPanel } from './Users'
import { UploadDrawer } from './Upload'
import { TaskingBox } from './Taskings'
import * as api from './api'
import type { UserInfo, Assessment, CopEvent, Incident, Layers, Location, Person, Role, RosterStatus, Selection, Snapshot, Threat, Trip } from './types'

const TYPE_LABEL: Record<string, string> = { hq: 'HQ', office: 'OFFICE', datacenter: 'DATA CENTER', residence: 'RESIDENCE', venue: 'VENUE', airfield: 'AIRFIELD', cp: 'CP', fob: 'FOB', farp: 'FARP', range: 'RANGE' }
const SITE_TYPES = ['hq', 'cp', 'fob', 'farp', 'airfield', 'range', 'office', 'datacenter', 'venue', 'residence'] as const
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
  // Panels stay up until closed or displaced by another on the same rail; the choice survives a reload.
  type RightPanel = 'right' | 's4' | 's6' | 'settings' | null
  const [addSite, setAddSite] = useState(false)
  const [leftOpen, setLeftOpen] = useState<boolean>(() => { try { return localStorage.getItem('toc.panel.left') !== 'closed' } catch { return true } })
  const [rightPanel, setRightPanel] = useState<RightPanel>(() => { try { return (localStorage.getItem('toc.panel.right') as RightPanel) || null } catch { return null } })
  useEffect(() => { try { localStorage.setItem('toc.panel.left', leftOpen ? 'open' : 'closed'); localStorage.setItem('toc.panel.right', rightPanel ?? '') } catch { /* private mode */ } }, [leftOpen, rightPanel])
  const toggleRight = (p: Exclude<RightPanel, null>) => { const next = rightPanel === p ? null : p; setRightPanel(next); if (next === 's4') setLayers(l => ({ ...l, s4: true })); if (next === 's6') setLayers(l => ({ ...l, s6: true })) }
  const openPanel = rightPanel ?? (leftOpen ? 'left' : null)  // for the wall's class only
  const [s3Flash, setS3Flash] = useState(false)
  const jump = (section: 'S1' | 'S2' | 'S3') => {  // a header counter opens its section
    if (section === 'S1') setLeftOpen(true)
    else if (section === 'S2') setRightPanel('right')
    else { setS3Flash(true); document.querySelector('.bottom')?.scrollIntoView({ block: 'end' }); window.setTimeout(() => setS3Flash(false), 1200) }
  }
  const sectionOn = (code: string) => (snap?.sections?.find(x => x.code === code)?.enabled ?? (code !== 'S4' && code !== 'S6')) && can(code)
  const sectionTitle = (code: string, fallback: string) => snap?.sections?.find(x => x.code === code)?.title ?? fallback
  const sectionLabel = (code: string) => snap?.sections?.find(x => x.code === code)?.label ?? code   // what the rail says: "S1" or "PEOPLE"
  const sectionCode = (code: string) => (snap?.sections?.find(x => x.code === code)?.show_code ?? true) ? code : ''  // a corporate desk drops the staff codes
  const switchProfile = (profile: 'military' | 'corporate') => {
    if (!window.confirm(`Switch to the ${profile.toUpperCase()} profile? This reloads the sample data — ${profile === 'military' ? 'the Combat Aviation Brigade with S4 and S6' : 'the executive-protection sample, S1–S3 only'}.`)) return
    act(`switching to the ${profile} profile`, async () => { await api.setProfile(profile); window.location.reload() })
  }
  const [showSettings, setShowSettings] = useState(false)
  const [showDefcon, setShowDefcon] = useState(false)
  useEffect(() => { try { localStorage.setItem('toc.ui', JSON.stringify(ui)) } catch { /* private mode */ } }, [ui])
  const [layers, setLayers] = useState<Layers>({ locations: true, travelers: true, threats: true, routes: true, events: true, residences: false, s4: false, s6: false })
  const [now, setNow] = useState(Date.now())
  const [role, setRole] = useState<Role>(api.session.role)
  const [users, setUsers] = useState<UserInfo[]>([])
  const [userId, setUserId] = useState<string>(api.session.userId)
  const me = snap?.me
  const can = (section: string, level: 'view' | 'edit' = 'view') => !me || me.user_id === null || me.battle_captain ? true : level === 'view' ? me.sections_visible.includes(section) : me.perms[section as 'S1'] === 'edit'
  const enabledSections = (['S1', 'S2', 'S3', 'S4', 'S6'] as const).filter(c => sectionOn(c))
  const taskingsFor = (sec: 'S1' | 'S2' | 'S3' | 'S4' | 'S6') => <TaskingBox section={sec} board={snap?.taskings} canEdit={can(sec, 'edit')} busy={busy} act={act} enabled={[...enabledSections]} />
  const [showBrief, setShowBrief] = useState(false)
  const [areaId, setAreaId] = useState<string | null>(null)
  const [showIntsum, setShowIntsum] = useState(false)
  const [opId, setOpId] = useState<string | null>(null)
  const [showPlan, setShowPlan] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [upload, setUpload] = useState<'S1' | 'S3' | 'S4' | 'S6' | null>(null)
  const [s3Tasks, setS3Tasks] = useState(false)
  const [briefReload, setBriefReload] = useState(0)

  const load = useCallback(() => api.fetchSnapshot(layers.residences).then(s => { setSnap(s); setErr(null) }).catch(e => setErr(String(e))), [layers.residences])
  useEffect(() => { api.session.role = role; load() }, [role, load])
  useEffect(() => { api.listUsers().then(d => setUsers(d.users)).catch(() => {}) }, [briefReload])
  useEffect(() => { if (me?.role && me.user_id) setRole(me.role as Role) }, [me?.role, me?.user_id])
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
    <div className={`wall ${s3Flash ? 's3-flash' : ''} profile-${snap?.profile ?? 'military'} posture-${s?.posture ?? 'normal'} ${(s?.flash ?? 0) > 0 ? 'has-flash' : ''} labels-${ui.labels} header-${ui.header} ${openPanel ? 'panel-' + openPanel : ''}`}>
      <header className="top">
        <div className="brand"><img className="glyph" src="/mark.svg" alt="" /><span className="mark">TOC</span><span className="sub">COMMON OPERATING PICTURE</span></div>
        {role === 'battle_captain' && <select className="role profile" value={snap?.profile ?? 'military'} onChange={e => switchProfile(e.target.value as 'military' | 'corporate')} title="Deployment profile — reloads the sample data" disabled={!!busy}>
          <option value="military">Military</option><option value="corporate">Corporate</option>
        </select>}
        <button className={`posture-chip ${s?.posture ?? ''}`} onClick={() => { setShowDefcon(v => !v); setShowSettings(false) }} title="The wall's posture is the worst site's effective posture. Click for the levels.">DEFCON {s?.defcon ?? '—'}</button>
        {showDefcon && s && <div className="defcon" onClick={e => e.stopPropagation()}>
          <div className="dform-head">DEFCON <span className="dim">the wall reads the worst site · set a site's level from its card</span></div>
          {[...(s.defcon_levels ?? [])].sort((x, y) => y.defcon - x.defcon).map(l => <div key={l.defcon} className={`dlevel ${l.posture} ${l.defcon === s.defcon ? 'now' : ''}`}>
            <span className="dnum">{l.defcon}</span><span className="dname">{l.posture.toUpperCase()}</span><span className="dmean">{l.meaning}</span><span className="dsites dim">{l.sites ? `${l.sites} site${l.sites === 1 ? '' : 's'}` : ''}</span>
          </div>)}
        </div>}
        <WatchChip w={snap?.watch} onOpen={() => setShowBrief(v => !v)} />
        <div className="stats">
          <Stat onJump={jump} label="PERSONNEL" v={s?.total_people} /><Stat onJump={jump} label="PRESENT" v={s?.present} />
          <Stat onJump={jump} label="TRAVELING" v={s?.traveling} accent="blue" /><Stat onJump={jump} label="VIP OUT" v={s?.vips_traveling} accent="gold" />
          <Stat onJump={jump} label="CHECKED IN" v={s?.checked_in_fresh} accent="green" /><Stat onJump={jump} label="SEC ON SHIFT" v={s?.security_on_shift} accent="green" />
          <Stat onJump={jump} label="THREATS" v={s?.active_threats} accent="red" /><Stat onJump={jump} label="CONFIRMED" v={s?.confirmed_links} accent="red" />
          {(s?.unaccounted ?? 0) > 0 && <Stat onJump={jump} label="UNACCOUNTED" v={s?.unaccounted} accent="red" />}
          {(s?.flash ?? 0) > 0 && <Stat onJump={jump} label="FLASH" v={s?.flash} accent="red" />}
          {(s?.unreachable ?? 0) > 0 && <Stat onJump={jump} label="UNREACHABLE" v={s?.unreachable} accent="red" />}
          <Stat onJump={jump} label="OPEN PIRs" v={s?.open_pirs} accent="amber" /><Stat onJump={jump} label="EVENTS" v={s?.upcoming_events} />
        </div>
        <select className="role" value={userId} onChange={e => { api.signIn(e.target.value); setUserId(e.target.value); load() }} title="Profile — the role you are signed in as (§9)">
          {users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
        </select>
        {false && <select className="role" value={role} onChange={e => setRole(e.target.value as Role)} title="Demo role — until someone signs in">
          <option value="battle_captain">Battle Captain</option><option value="ep">Executive Protection</option><option value="security">Security</option><option value="analyst">S2 Analyst</option><option value="ea">Executive Assistant</option><option value="logistics">S4 Logistics</option><option value="signal">S6 Signal</option>
        </select>}
        {(me && me.user_id ? me.admin || me.battle_captain : role === 'battle_captain') && <button className={`gear ${rightPanel === 'settings' ? 'on' : ''}`} title="Sources, keys, comms, sections — Battle Captain" onClick={() => toggleRight('settings')}>⚙ SETTINGS</button>}
        <button className="gear" title="Labels and header options" onClick={() => setShowSettings(v => !v)}>DISPLAY ▾</button>
        <div className="clock">{clock(new Date(now))}</div>
        {showSettings && <div className="settings" onClick={e => e.stopPropagation()}>
          <div className="s-row"><span>LABELS</span>{(['full', 'lean'] as const).map(m => <button key={m} className={`chip btn ${ui.labels === m ? 'on' : ''}`} onClick={() => setUi({ ...ui, labels: m })}>{m.toUpperCase()}</button>)}<span className="dim small">LEAN drops hints, empty lines, second lines</span></div>
          <div className="s-row"><span>HEADER</span>{(['counters', 'posture'] as const).map(m => <button key={m} className={`chip btn ${ui.header === m ? 'on' : ''}`} onClick={() => setUi({ ...ui, header: m })}>{m.toUpperCase()}</button>)}<span className="dim small">POSTURE: one big posture tile, five counters</span></div>
        </div>}
      </header>
      <FlashStrip warnings={snap?.warnings ?? []} role={role} busy={busy} act={act} onSelect={setSel} reload={briefReload} />

      <nav className="rail rail-left">
        {sectionOn('S1') && <button className={`rail-btn ${leftOpen ? 'on' : ''}`} onClick={() => setLeftOpen(v => !v)} title={`${sectionCode('S1')} ${sectionTitle('S1', 'PERSONNEL')}`}>{sectionLabel('S1')}</button>}
        {snap && snap.incidents.some(i => i.status === 'open') && <button className="rail-btn alert" onClick={() => setLeftOpen(true)} title="open roll calls">S6</button>}
      </nav>
      <nav className="rail rail-right">
        {sectionOn('S2') && <button className={`rail-btn ${rightPanel === 'right' ? 'on' : ''}`} onClick={() => toggleRight('right')} title={`${sectionCode('S2')} ${sectionTitle('S2', 'INTELLIGENCE')}`}>{sectionLabel('S2')}{(s?.warnings_pending ?? 0) > 0 && <i className="badge">{s?.warnings_pending}</i>}</button>}
        {sectionOn('S4') && <button className={`rail-btn ${rightPanel === 's4' ? 'on' : ''} st-${s?.s4_status ?? 'green'}`} onClick={() => toggleRight('s4')} title={`S4 ${sectionTitle('S4', 'LOGISTICS')} · ${s?.s4_status ?? ''}`}>S4<i className={`dot ${s?.s4_status ?? 'green'}`} /></button>}
        {sectionOn('S6') && <button className={`rail-btn ${rightPanel === 's6' ? 'on' : ''} st-${s?.s6_status ?? 'green'}`} onClick={() => toggleRight('s6')} title={`S6 ${sectionTitle('S6', 'SIGNAL')} · ${s?.s6_status ?? ''}`}>S6<i className={`dot ${s?.s6_status ?? 'green'}`} /></button>}
      </nav>
      <aside className={`left ${leftOpen ? 'open' : ''}`}>
        <PanelHead code={sectionCode('S1')} title={sectionTitle('S1', 'PERSONNEL')} hint="Blue Force" onClose={() => setLeftOpen(false)}>{can('S1', 'edit') && <button className="mini" onClick={() => setUpload(u => u === 'S1' ? null : 'S1')} title="Drop the roster spreadsheet">UPLOAD</button>}{['battle_captain', 'ea', 'security', 'analyst'].includes(role) && <button className="mini" onClick={() => setShowImport(v => !v)} title="paste an export from the systems of record">IMPORT</button>}</PanelHead>
        {upload === 'S1' && <UploadDrawer section="S1" busy={busy} act={act} onDone={() => setBriefReload(n => n + 1)} />}
        {showImport && <ImportDrawer busy={busy} act={act} onDone={() => setShowImport(false)} />}
        <EstimateLine e={snap?.estimates.find(e => e.section === 'S1')} role={role} busy={busy} act={act} />
        {taskingsFor('S1')}
        <div className="layer-toggles">
          {(['locations', 'travelers', 'routes', 'threats', 'events'] as (keyof Layers)[]).map(k => (
            <button key={k} className={`tog ${layers[k] ? 'on' : ''}`} onClick={() => toggle(k)}>{k}</button>))}
          {sectionOn('S4') && <button className={`tog sec4 ${layers.s4 ? 'on' : ''}`} onClick={() => toggle('s4')} title="S4 health on every site">S4</button>}
          {sectionOn('S6') && <button className={`tog sec6 ${layers.s6 ? 'on' : ''}`} onClick={() => toggle('s6')} title="S6 health on every site">S6</button>}
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
        {snap && <TaskOrg teams={snap.teams} people={snap.people} onSelect={setSel} sel={sel} />}
        <SectionLabel>LOCATIONS {can('S3', 'edit') && <button className="mini" title="Add a site — a CP the TOC jumped to, a new office" onClick={e => { e.stopPropagation(); setAddSite(v => !v) }}>{addSite ? '×' : '+ SITE'}</button>}</SectionLabel>
        {addSite && <SiteForm busy={busy} act={act} onDone={() => setAddSite(false)} />}
        <ul className="list">
          {snap?.locations.map(l => (
            <li key={l.id} className={`row ${sel?.type === 'location' && sel.id === l.id ? 'active' : ''}`} onClick={() => setSel({ type: 'location', id: l.id })}>
              <span className={`dot posture-${l.effective_posture}`} />
              <span className="name">{l.is_toc && <span className="tocmark" title="the TOC is running from here">◈</span>}{l.name}{l.sensitivity === 'restricted' && <span className="lock">⚿</span>}</span>
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

      <main className="center" onClick={() => setShowSettings(false)}>
        <MapView snapshot={snap} selection={sel} layers={layers} onSelect={setSel} />
        {showPlan && <PlanningPanel role={role} busy={busy} act={act} onClose={() => setShowPlan(false)} onSelect={s => { setSel(s); setShowPlan(false) }} reload={briefReload} snap={snap} />}
        {opId && !showPlan && <OperationPanel id={opId} role={role} busy={busy} act={act} onClose={() => setOpId(null)} reload={briefReload} />}
        {showIntsum && !opId && <IntsumPanel role={role} busy={busy} act={act} onClose={() => setShowIntsum(false)} reload={briefReload} />}
        {areaId && !showIntsum && !opId && <AreaPanel id={areaId} role={role} busy={busy} act={act} onClose={() => setAreaId(null)} reload={briefReload} />}
        {sel && snap && !showBrief && !areaId && !showIntsum && !opId && !showPlan && <Detail sel={sel} snap={snap} byId={byId} now={now} busy={busy} act={act} onClose={() => setSel(null)} onSelect={setSel} onOp={setOpId} role={role} />}
        {showBrief && <BriefPanel role={role} busy={busy} act={act} onClose={() => setShowBrief(false)} reload={briefReload} />}
        {err && <div className="error" onClick={() => setErr(null)}>{err}</div>}
        {!snap && !err && <div className="loading">LOADING PICTURE…</div>}
        {busy && <div className="loading">{busy.toUpperCase()}…</div>}
      </main>

      <aside className={`right wide ${rightPanel === 'settings' ? 'open' : ''}`}>
        <PanelHead code="⚙" title="SETTINGS" hint="Battle Captain · write-only keys" onClose={() => setRightPanel(null)} />
        {(me && me.user_id ? me.admin : true) && <><div className="section-label">USERS &amp; PERMISSIONS <span className="dim">admin</span></div><UsersPanel busy={busy} act={act} reload={briefReload} onChanged={() => setBriefReload(n => n + 1)} /></>}
        <SettingsPanel busy={busy} act={act} reload={briefReload} />
      </aside>
      <aside className={`right ${rightPanel === 's4' ? 'open' : ''}`}>
        <PanelHead code="S4" title={sectionTitle('S4', 'LOGISTICS')} hint="Supply & equipment · by exception" onClose={() => setRightPanel(null)}>{can('S4', 'edit') && <button className="mini" onClick={() => setUpload(u => u === 'S4' ? null : 'S4')} title="Drop the LOGSTAT spreadsheet">UPLOAD</button>}</PanelHead>
        {upload === 'S4' && <UploadDrawer section="S4" busy={busy} act={act} onDone={() => setBriefReload(n => n + 1)} />}
        <EstimateLine e={snap?.estimates.find(e => e.section === 'S4')} role={role} busy={busy} act={act} />
        {taskingsFor('S4')}
        <S4Panel board={snap?.s4} role={role} busy={busy} act={act} site={sel?.type === 'location' ? byId.loc.get(sel.id) : undefined} onClearSite={() => setSel(null)} onMap={layers.s4} toggleMap={() => toggle('s4')} />
      </aside>
      <aside className={`right ${rightPanel === 's6' ? 'open' : ''}`}>
        <PanelHead code="S6" title={sectionTitle('S6', 'SIGNAL')} hint="Comms & systems · by exception" onClose={() => setRightPanel(null)}>{can('S6', 'edit') && <button className="mini" onClick={() => setUpload(u => u === 'S6' ? null : 'S6')} title="Drop the comms status spreadsheet">UPLOAD</button>}</PanelHead>
        {upload === 'S6' && <UploadDrawer section="S6" busy={busy} act={act} onDone={() => setBriefReload(n => n + 1)} />}
        <EstimateLine e={snap?.estimates.find(e => e.section === 'S6')} role={role} busy={busy} act={act} />
        {taskingsFor('S6')}
        <S6Panel board={snap?.s6} role={role} busy={busy} act={act} site={sel?.type === 'location' ? byId.loc.get(sel.id) : undefined} onClearSite={() => setSel(null)} onMap={layers.s6} toggleMap={() => toggle('s6')} />
        {snap && snap.incidents.filter(i => i.status === 'open').length > 0 && <>
          <SectionLabel>ACCOUNTABILITY · OPEN ROLL CALLS <span className="dim">{snap.incidents.filter(i => i.status === 'open').length}</span></SectionLabel>
          <ul className="list">{snap.incidents.filter(i => i.status === 'open').map(i => (
            <li key={i.id} className="row rollcall" onClick={() => setSel({ type: 'incident', id: i.id })}><span className="name">{i.title}</span><span className={`meta ${i.pct === 100 ? 'ok' : 'bad'}`}>{i.accounted}/{i.total}</span></li>))}</ul>
        </>}
      </aside>
      <aside className={`right ${rightPanel === 'right' ? 'open' : ''}`}>
        <PanelHead code={sectionCode('S2')} title={sectionTitle('S2', 'INTELLIGENCE')} hint="Sigtoc" onClose={() => setRightPanel(null)}>
          <button className="mini" onClick={() => { setShowIntsum(v => !v); setAreaId(null); setShowBrief(false) }} title="The daily INTSUM (Decision G)">INTSUM</button>
          <button className="mini" disabled={!!busy} onClick={() => act('collecting from every live source', api.refreshIntel)} title="Run every enabled, configured collector">⟳ COLLECT</button>
        </PanelHead>
        <EstimateLine e={snap?.estimates.find(e => e.section === 'S2')} role={role} busy={busy} act={act} />
        {taskingsFor('S2')}
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
          <PanelHead code={sectionCode('S3')} title={sectionTitle('S3', 'OPERATIONS')} hint="Events · Travel" inline>{can('S3', 'edit') && <button className="mini" onClick={() => setUpload(u => u === 'S3' ? null : 'S3')} title="Drop the schedule spreadsheet">UPLOAD</button>}<button className={`mini ${s3Tasks ? 'on' : ''}`} onClick={() => setS3Tasks(v => !v)} title="Work S3 owes and is waiting on">TASKINGS{(snap?.taskings?.per_section?.S3?.inbox ?? 0) > 0 && <i className="badge">{snap?.taskings.per_section.S3.inbox}</i>}</button><button className="mini" onClick={() => { setShowPlan(v => !v); setOpId(null); setShowBrief(false) }} title="the next 90 days by week, coverage per event">PLAN 90d</button></PanelHead>
          {upload === 'S3' && <UploadDrawer section="S3" busy={busy} act={act} onDone={() => setBriefReload(n => n + 1)} />}
          {s3Tasks && <div className="dform upload s3-tasks">{taskingsFor('S3')}</div>}
          <EstimateLine e={snap?.estimates.find(e => e.section === 'S3')} role={role} busy={busy} act={act} />
          <Timeline snap={snap} now={now} sel={sel} onSelect={setSel} onOp={id => { setOpId(id); setShowBrief(false) }} />
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
// which section a counter belongs to: click it and that section opens
const STAT_SECTION: Record<string, 'S1' | 'S2' | 'S3'> = { PERSONNEL: 'S1', PRESENT: 'S1', 'CHECKED IN': 'S1', 'SEC ON SHIFT': 'S1', UNACCOUNTED: 'S1', UNREACHABLE: 'S1', TRAVELING: 'S3', 'VIP OUT': 'S3', EVENTS: 'S3', THREATS: 'S2', CONFIRMED: 'S2', FLASH: 'S2', 'OPEN PIRs': 'S2' }
function Stat({ label, v, accent, onJump }: { label: string; v?: number; accent?: string; onJump?: (section: 'S1' | 'S2' | 'S3') => void }) {
  // data-k lets the header toggle keep five counters without changing the markup order
  const sec = STAT_SECTION[label]
  return <div className={`stat ${accent ?? ''} ${sec ? 'jump' : ''}`} data-k={label} title={sec ? `open ${sec}` : undefined} onClick={() => sec && onJump?.(sec)}><span className="v">{v ?? '—'}</span><span className="l">{label}</span></div>
}
function PanelHead({ code, title, hint, inline, children, onClose }: { code: string; title: string; hint?: string; inline?: boolean; children?: React.ReactNode; onClose?: () => void }) {
  return <div className={`panel-head ${inline ? 'inline' : ''}`}>{code && <span className="code">{code}</span>}<span className="title">{title}</span>{children}{hint && <span className="hint">{hint}</span>}{onClose && <button className="close-panel" title="Close" onClick={onClose}>×</button>}</div>
}
/** §3.1 — add a site, or correct one that moved. The TOC flag has its own action: it is a different decision. */
function SiteForm({ busy, act, onDone, site }: { busy: string | null; act: (l: string, f: () => Promise<unknown>) => void; onDone: () => void; site?: Location }) {
  const [f, setF] = useState({
    name: site?.name ?? '', type: (site?.type ?? 'cp') as string, lat: String(site?.lat ?? ''), lon: String(site?.lon ?? ''),
    city: site?.city ?? '', country: site?.country ?? '', sensitivity: site?.sensitivity ?? 'standard',
  })
  const [err, setErr] = useState<string | null>(null)
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value })
  const submit = () => {
    const lat = Number(f.lat), lon = Number(f.lon)
    if (!f.name.trim()) return setErr('A site needs a name.')
    if (!Number.isFinite(lat) || Math.abs(lat) > 90 || !Number.isFinite(lon) || Math.abs(lon) > 180) return setErr('Latitude ±90, longitude ±180.')
    setErr(null)
    const body = { name: f.name.trim(), type: f.type as Location['type'], lat, lon, city: f.city.trim(), country: f.country.trim(), sensitivity: f.sensitivity as 'standard' | 'restricted' }
    act(site ? 'saving the site' : 'adding the site', () => (site ? api.updateLocation(site.id, body) : api.createLocation(body)).then(onDone))
  }
  return (
    <div className="siteform" onClick={e => e.stopPropagation()}>
      <input className="in" placeholder="Name — e.g. TAA Falcon" value={f.name} onChange={set('name')} />
      <div className="s-row">
        <select className="in" value={f.type} onChange={set('type')}>{SITE_TYPES.map(t => <option key={t} value={t}>{TYPE_LABEL[t]}</option>)}</select>
        <select className="in" value={f.sensitivity} onChange={set('sensitivity')}><option value="standard">standard</option><option value="restricted">restricted ⚿</option></select>
      </div>
      <div className="s-row">
        <input className="in" placeholder="lat" value={f.lat} onChange={set('lat')} />
        <input className="in" placeholder="lon" value={f.lon} onChange={set('lon')} />
      </div>
      <div className="s-row">
        <input className="in" placeholder="city" value={f.city} onChange={set('city')} />
        <input className="in" placeholder="country" value={f.country} onChange={set('country')} />
      </div>
      {err && <div className="dim small bad">{err}</div>}
      <div className="s-row"><button className="chip btn on" disabled={!!busy} onClick={submit}>{site ? 'SAVE' : 'ADD SITE'}</button><button className="chip btn" disabled={!!busy} onClick={onDone}>CANCEL</button></div>
    </div>)
}

function SectionLabel({ children }: { children: React.ReactNode }) { return <div className="section-label">{children}</div> }

const LEG_ICON: Record<string, string> = { flight: '✈', ground: '🚗', lodging: '🏨' }
function Detail({ sel, snap, byId, now, busy, act, onClose, onSelect }: {
  sel: NonNullable<Selection>; snap: Snapshot; byId: ById; now: number; busy: string | null
  act: (l: string, f: () => Promise<unknown>) => void; onClose: () => void; onSelect: (s: Selection) => void
}) {
  const [addOpen, setAddOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  // S3 owns where the force sits; nobody signed in is the demo wall, which can do anything.
  const mayEditSites = !snap.me || snap.me.user_id === null || snap.me.battle_captain || snap.me.perms.S3 === 'edit'
  useEffect(() => { setEditing(false) }, [sel.type, sel.id])
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
          {(['normal', 'guarded', 'elevated', 'high', 'critical'] as const).map(p => (
            <button key={p} className={`chip btn ${p} ${l.posture === p ? 'on' : ''}`} disabled={!!busy} onClick={() => act('setting posture', () => api.setPosture(l.id, p, 'Set from the wall'))}>{p.toUpperCase()}</button>))}
          {l.effective_posture !== l.posture && <span className={`chip ${l.effective_posture}`} title="raised by a confirmed threat link">EFFECTIVE {l.effective_posture.toUpperCase()}</span>}
        </div>
        {(l.threat_ids_in_area.length > 0 || l.confirmed_threat_ids.length > 0) && <>
          <div className="section-label">THREATS IN AREA <span className="dim">proximity suggests · analyst confirms</span></div>
          <ul className="people">{threatRows(Array.from(new Set([...l.confirmed_threat_ids, ...l.threat_ids_in_area])), l.confirmed_threat_ids, { type: 'location', id: l.id })}</ul>
        </>}
        <div className="d-actions">{draftBtn('location', l.id)} {rollCallBtn({ location_id: l.id })}
          {mayEditSites && <>
            <button className={`chip btn ${l.is_toc ? 'on' : ''}`} disabled={!!busy || l.is_toc}
              title={l.is_toc ? 'the TOC is running from here' : 'the TOC jumped here — the wall opens on it from now on'}
              onClick={() => act('moving the TOC', () => api.setToc(l.id))}>{l.is_toc ? '◈ TOC IS HERE' : '◈ TOC HERE'}</button>
            <button className="chip btn" disabled={!!busy} onClick={() => setEditing(v => !v)}>{editing ? 'CANCEL' : 'EDIT SITE'}</button>
          </>}
        </div>
        {editing && <SiteForm busy={busy} act={act} site={l} onDone={() => setEditing(false)} />}
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
          {trip.legs.length > 0 && <>
            <div className="section-label">ITINERARY · {trip.legs.length} legs{trip.current_leg && <> · now: {trip.current_leg.label || trip.current_leg.to_name}</>}</div>
            <ol className="legs">{trip.legs.map(l => (
              <li key={l.id} className={`leg ${l.status}`} title={l.note || l.source}>
                <span className="leg-when">{new Date(l.start_at).toUTCString().slice(5, 22)}</span>
                <span className="leg-kind">{LEG_ICON[l.kind]}</span>
                <span className="leg-what"><b>{l.label || l.to_name}</b>{l.kind === 'lodging' ? <> · until {new Date(l.end_at).toUTCString().slice(5, 16)}</> : <> · {l.from_name} → {l.to_name}</>}{l.ref && <span className="dim"> · {l.ref}</span>}</span>
                <span className={`chip ${l.status === 'current' ? 'active' : l.status === 'done' ? 'dim' : 'planned'}`}>{l.status === 'current' ? 'NOW' : l.status.toUpperCase()}</span>
              </li>))}</ol>
          </>}
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
