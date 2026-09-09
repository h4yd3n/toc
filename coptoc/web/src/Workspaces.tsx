import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { Destination } from './navigation'
import type { Assessment, Report, Role, SectionCode, Selection, Snapshot } from './types'
import * as api from './api'
import { CasesPanel, ReportForm } from './Cases'
import { RequirementsPanel } from './Requirements'
import { S4Panel, S6Panel } from './Sections'
import { TaskingBox } from './Taskings'
import { UploadDrawer } from './Upload'
import { ImportDrawer, PlanningPanel } from './Planning'
import { EstimateLine } from './Watch'
import { WarningsSection } from './Warnings'
import { TaskOrg } from './TaskOrg'
import { WorkPanel } from './WorkPanel'
import { ActivityPanel } from './ActivityPanel'
import { IntakePanel } from './IntakePanel'
import { PersonForm, EventForm, PersonnelList, StaffRecordForm } from './RecordForms'

type Act = (label: string, fn: () => Promise<unknown>) => void
export const STAFF: Record<SectionCode, string> = { S1: 'Personnel', S2: 'Intelligence', S3: 'Operations', S4: 'Logistics', S6: 'Communications' }
const TABS: Record<SectionCode, [string, string][]> = {
  S1: [['overview','Overview'], ['personnel','Personnel'], ['assignments','Assignments'], ['accountability','Accountability'], ['tasks','Tasks'], ['analysis','AI analysis']],
  S2: [['overview','Overview'], ['reporting','Reporting'], ['collection','Requirements & collection'], ['cases','Cases'], ['products','Products'], ['tasks','Tasks'], ['analysis','AI analysis']],
  S3: [['overview','Overview'], ['operations','Current operations'], ['planning','Planning'], ['tasks','Tasks'], ['analysis','AI analysis']],
  S4: [['overview','Overview'], ['inventory','Inventory'], ['shipments','Shipments'], ['tasks','Requests'], ['analysis','AI analysis']],
  S6: [['overview','Overview'], ['systems','Systems'], ['contacts','Contact plans'], ['incidents','Incidents'], ['tasks','Tasks'], ['analysis','AI analysis']],
}
export function SectionSummary({ section, snap, onOpen, onSelect }: { section: SectionCode; snap: Snapshot; onOpen: (tab?: string, record?: string) => void; onSelect: (s: Selection) => void }) {
  const estimate = snap.estimates.find(e => e.section === section)
  const recordsTab = section === 'S1' ? 'personnel' : section === 'S2' ? 'products' : section === 'S3' ? 'operations' : section === 'S4' ? 'inventory' : 'systems'
  const exceptions: { id: string; title: string; detail: string; select?: Selection; tab?: string }[] = []
  if (section === 'S1') snap.people.filter(p => p.availability === 'unreachable' || p.incident_status === 'unaccounted' || p.incident_status === 'assist').forEach(p => exceptions.push({ id:p.id, title:p.name, detail:p.incident_status || p.availability, select:{ type:'person',id:p.id } }))
  if (section === 'S2') { snap.warnings.filter(w => ['draft','suggested','released'].includes(w.status)).forEach(w => exceptions.push({ id:w.id,title:w.title,detail:`Warning · ${w.status}`,tab:'products' })); snap.assessments.filter(a => a.status === 'review').forEach(a => exceptions.push({ id:a.id,title:a.title,detail:'Assessment awaiting review',tab:'products' })) }
  if (section === 'S3') snap.events.filter(e => e.status !== 'past' && (e.coverage?.gap ?? 0) > 0).forEach(e => exceptions.push({ id:e.id,title:e.name,detail:`${e.coverage?.gap} unfilled security positions`, select:{ type:'event',id:e.id } }))
  if (section === 'S4') snap.s4?.supplies.filter(x => x.status !== 'green').forEach(x => exceptions.push({ id:x.id,title:x.item,detail:`${x.location_name} · ${x.on_hand}/${x.required} ${x.unit}`,tab:'inventory' }))
  if (section === 'S6') snap.s6?.systems.filter(x => x.status !== 'up').forEach(x => exceptions.push({ id:x.id,title:x.name,detail:`${x.location_name} · ${x.status}`,tab:'systems' }))
  const counts = snap.taskings?.per_section?.[section]
  return <div className="section-summary">
    <p className="ws-kicker">Current estimate</p><p className="section-estimate">{estimate?.assessment || 'No current staff estimate recorded.'}</p>
    {estimate?.updated_at && <p className="dim small">{estimate.updated_by} · {new Date(estimate.updated_at).toLocaleString()}</p>}
    <div className="ws-toolbar"><h3>Needs attention</h3><span className="ws-count">{exceptions.length}</span></div>
    {exceptions.length === 0 ? <p className="dim">No exceptions in this view.</p> : exceptions.slice(0,3).map(x => <button className="section-exception" key={x.id} onClick={() => x.select ? onSelect(x.select) : onOpen(x.tab,x.id)}><strong>{x.title}</strong><span>{x.detail}</span></button>)}
    {exceptions.length > 3 && <button className="ws-link" onClick={() => onOpen(recordsTab)}>View all {exceptions.length} exceptions →</button>}
    <button className="section-task-count" onClick={() => onOpen('tasks')}>{counts?.inbox ?? 0} tasks to do · {counts?.outbox ?? 0} waiting on others →</button>
    <button className="ws-primary" onClick={() => onOpen(section === 'S2' ? 'reporting' : section === 'S1' ? 'personnel' : section === 'S3' ? 'operations' : section === 'S4' ? 'inventory' : 'systems')}>Open {STAFF[section].toLowerCase()} records →</button>
  </div>
}
interface Props {
  destination: Destination; navigate: (next: Partial<Destination>) => void; snap: Snapshot; role: Role; enabled: SectionCode[];
  can: (s: string, level?: 'view'|'edit') => boolean; act: Act; busy: string | null; reload: number;
  onSelect: (s: Selection) => void; onArea: (id: string) => void; onIntsum: () => void; onOp: (id: string) => void; siteForm: ReactNode;
  onReload?: () => void;
  onClose?: () => void;
}
export default function Workspaces({ destination:d, navigate, snap, role, enabled, can, act, busy, reload, onSelect, onArea, onIntsum, onOp, siteForm, onReload, onClose }: Props) {
  const [query, setQuery] = useState('')
  const [importing, setImporting] = useState(false)
  const [site, setSite] = useState(false)
  const [adding,setAdding] = useState(false)
  useEffect(() => { setQuery(''); setImporting(false); setSite(false); setAdding(false) }, [d.section,d.tab])
  const section = enabled.includes(d.section) ? d.section : enabled.find(s=>can(s,'edit')) ?? enabled[0]
  const tabs: [string,string][] = section ? [...TABS[section], ['activity','Activity']] : []
  const tab = tabs.some(([id]) => id === d.tab) ? d.tab : 'overview'
  const open = (tab='overview',record?:string) => navigate({ page:'workspace',section,tab,record:record ?? null })
  if (!section) return <div className="workspace"><p>No staff workspaces are available to this profile.</p></div>
  const common = { busy, act, role, reload }
  const match = (text:string) => text.toLowerCase().includes(query.toLowerCase())
  const tasks = <TaskingBox section={section} board={snap.taskings} canEdit={can(section,'edit')} busy={busy} act={act} enabled={enabled} />
  const search = <label className="ws-search"><span className="sr-only">Search {STAFF[section]}</span><input type="search" placeholder="Search this view…" value={query} onChange={e=>setQuery(e.target.value)} /></label>
  return <div className="workspace" aria-label={`${STAFF[section]} workspace`}>
    <header className="workspace-header">
      <div className="ws-head-meta">
        <span className={`ws-badge ${section.toLowerCase()}`}>{section}</span>
        <div className="ws-title-group">
          <span className="ws-kicker">{section} · STAFF WORKSPACE</span>
          <h1 className="ws-title">{snap.sections.find(x=>x.code===section)?.title || STAFF[section]}</h1>
        </div>
      </div>
      <div className="ws-head-actions">
        <span className="ws-operator dim">{snap.me?.name || role.replace('_',' ').toUpperCase()}</span>
        {onClose && <button className="ws-return-btn" onClick={onClose} title="Return to tactical map (Esc)">← MAP VIEW</button>}
      </div>
    </header>
    <nav className="workspace-tabs" aria-label={`${section} views`}>
      {tabs.map(([id,label])=><button key={id} className={`ws-tab-btn ${tab===id?'active':''}`} aria-current={tab===id?'page':undefined} onClick={()=>open(id)}>{label.toUpperCase()}</button>)}
    </nav>
    <div className="workspace-body">
        {tab==='overview' && <>
          {section==='S4' && <IntakePanel snap={snap} canEdit={can('S4','edit')} act={act} busy={busy} reload={reload} selected={d.record} onSelect={id=>open('overview',id??undefined)}/>}
          {!(section==='S4'&&d.record)&&<><details className="ws-card"><summary>Section picture & staff estimate</summary><SectionSummary section={section} snap={snap} onOpen={open} onSelect={onSelect}/><EstimateLine e={snap.estimates.find(e=>e.section===section) ?? {section,assessment:'',recommendation:'',updated_by:null,updated_at:null}} canEditOverride={can(section,'edit')} role={role} busy={busy} act={act}/></details><WorkPanel locations={snap.locations} section={section} role={role} canEdit={s=>can(s,'edit')} reload={reload} busy={busy} act={act} onOpenCase={id=>open('cases',id)}/></>}
        </>}
        {tab==='activity' && <ActivityPanel reload={reload}/>}
        {tab==='tasks' && <section className="ws-card">{tasks}</section>}
        {tab==='analysis' && <WorkPanel locations={snap.locations} section={section} caseId={d.record?.startsWith('run_')?null:d.record} selectedRun={d.record?.startsWith('run_')?d.record:null} role={role} canEdit={s=>can(s,'edit')} reload={reload} busy={busy} act={act} onOpenCase={id=>open('cases',id)}/>}
        {section==='S2' && tab==='cases' && <section className="ws-card"><CasesPanel {...common} selectedCase={d.record} onSelectCase={id=>open('cases',id ?? undefined)} onAnalyzeCase={id=>open('analysis',id)} onChanged={()=>{}} /></section>}
        {section==='S2' && tab==='reporting' && <Reporting {...common} onCase={id=>open('cases',id)}/>}
        {section==='S2' && tab==='collection' && <section className="ws-card"><div className="ws-toolbar"><h2>Requirements & collection</h2>{can('S2','edit') && <button className="ws-primary" disabled={!!busy} onClick={()=>act('collecting intelligence',api.refreshIntel)}>Collect from enabled sources</button>}</div><RequirementsPanel {...common} onSelect={onSelect} onArea={onArea}/></section>}
        {section==='S2' && tab==='products' && <><div className="ws-toolbar"><h2>Intelligence products</h2><button className="ws-primary" onClick={onIntsum}>Open daily INTSUM</button></div><section className="ws-card"><WarningsSection warnings={snap.warnings} {...common} onSelect={onSelect}/></section><WorkPanel locations={snap.locations} section="S2" role={role} canEdit={s=>can(s,'edit')} reload={reload} busy={busy} act={act} selectedRun={d.record}/>{search}{snap.assessments.filter(a=>match(a.title)).map(a=><AssessmentCard key={a.id+':'+a.status+':'+a.bluf} assessment={a} role={role} canEdit={can('S2','edit')} busy={busy} act={act}/>)}</>}
        {section==='S1' && ['personnel','assignments'].includes(tab) && <>{can('S1','edit')&&<button className="ws-primary" onClick={()=>setAdding(!adding)}>Add person</button>}{adding&&<PersonForm snap={snap} busy={busy} act={act} onDone={()=>setAdding(false)}/>}<div className="ws-toolbar">{search}{can('S1','edit') && <button className="ws-primary" onClick={()=>setImporting(!importing)}>{importing ? 'Close import' : 'Import roster'}</button>}</div>{importing && <section className="ws-card"><div className="ws-toolbar"><h3>Ingestion &amp; Imports</h3><button className="mini" onClick={()=>setImporting(false)}>✕ CLOSE</button></div><UploadDrawer section="S1" busy={busy} act={act} onDone={()=>{ onReload?.() }}/><ImportDrawer busy={busy} act={act} onDone={()=>{ setImporting(false); onReload?.() }}/></section>}<section className="ws-card">{tab==='assignments'?<TaskOrg teams={snap.teams} people={snap.people.filter(p=>match(p.name+' '+p.team_name))} onSelect={onSelect} sel={null}/>:<PersonnelList key={query} people={snap.people.filter(p=>match(p.name+' '+p.team_name))} canEdit={can('S1','edit')} busy={busy} act={act} onSelect={onSelect}/>}</section></>}
        {(section==='S1' && tab==='accountability') && <section className="ws-card"><h2>Accountability incidents</h2>{snap.incidents.length===0 && <p className="dim">No incidents recorded. Open a site on the COP to start a roll call.</p>}{snap.incidents.map(i=><button className="section-exception" key={i.id} onClick={()=>onSelect({type:'incident',id:i.id})}><strong>{i.title}</strong><span>{i.accounted}/{i.total} accounted · {i.status}</span></button>)}</section>}
        {section==='S3' && tab==='operations' && <>{can('S3','edit')&&<button className="ws-primary" onClick={()=>setAdding(!adding)}>Create activity</button>}{adding&&<EventForm snap={snap} busy={busy} act={act} onDone={()=>setAdding(false)}/>}<div className="ws-toolbar">{search}{can('S3','edit') && <button className="ws-primary" onClick={()=>setImporting(!importing)}>{importing ? 'Close import' : 'Import schedule'}</button>}{can('S3','edit') && <button onClick={()=>setSite(!site)}>Add site</button>}</div>{site && <section className="ws-card">{siteForm}</section>}{importing && <section className="ws-card"><div className="ws-toolbar"><h3>Ingestion &amp; Imports</h3><button className="mini" onClick={()=>setImporting(false)}>✕ CLOSE</button></div><UploadDrawer section="S3" busy={busy} act={act} onDone={()=>{ onReload?.() }}/><ImportDrawer busy={busy} act={act} onDone={()=>{ setImporting(false); onReload?.() }}/></section>}<section className="ws-card"><h2>Activities & operations</h2>{snap.events.filter(e=>match(e.name)).map(e=><button className="section-exception" key={e.id} onClick={()=>e.operation?onOp(e.operation.id):onSelect({type:'event',id:e.id})}><strong>{e.name}</strong><span>{e.venue_name} · {e.status} · {new Date(e.start_at).toLocaleString()}</span></button>)}</section></>}
        {section==='S3' && tab==='planning' && <div className="workspace-embedded"><PlanningPanel {...common} snap={snap} onSelect={onSelect} onClose={()=>open()}/></div>}
        {section==='S4' && ['inventory','shipments'].includes(tab) && <>{can('S4','edit')&&<button className="ws-primary" onClick={()=>setAdding(!adding)}>{tab==='inventory'?'Add inventory line':'Add shipment'}</button>}{adding&&<StaffRecordForm kind={tab==='inventory'?'supply':'shipment'} snap={snap} busy={busy} act={act} onDone={()=>setAdding(false)}/>}<div className="ws-toolbar">{search}{can('S4','edit') && <button className="ws-primary" onClick={()=>setImporting(!importing)}>{importing ? 'Close import' : 'Import logistics'}</button>}</div>{importing && <section className="ws-card"><div className="ws-toolbar"><h3>Ingestion &amp; Imports</h3><button className="mini" onClick={()=>setImporting(false)}>✕ CLOSE</button></div><UploadDrawer section="S4" busy={busy} act={act} onDone={()=>{ onReload?.() }}/></section>}<section className="ws-card"><S4Panel canEditOverride={can('S4','edit')} role={role} busy={busy} act={act} view={tab==='inventory'?'supplies':'shipments'} board={{...snap.s4,supplies:snap.s4.supplies.filter(x=>match(x.item+' '+x.location_name)),shipments:snap.s4.shipments.filter(x=>match(x.description+' '+x.to_name))}}/></section></>}
        {section==='S6' && ['systems','contacts','incidents'].includes(tab) && <>{can('S6','edit')&&<button className="ws-primary" onClick={()=>setAdding(!adding)}>Add system</button>}{adding&&<StaffRecordForm kind="system" snap={snap} busy={busy} act={act} onDone={()=>setAdding(false)}/>}<div className="ws-toolbar">{search}{can('S6','edit') && <button className="ws-primary" onClick={()=>setImporting(!importing)}>{importing ? 'Close import' : 'Import communications'}</button>}</div>{importing && <section className="ws-card"><div className="ws-toolbar"><h3>Ingestion &amp; Imports</h3><button className="mini" onClick={()=>setImporting(false)}>✕ CLOSE</button></div><UploadDrawer section="S6" busy={busy} act={act} onDone={()=>{ onReload?.() }}/></section>}<section className="ws-card"><S6Panel canEditOverride={can('S6','edit')} role={role} busy={busy} act={act} view={tab==='contacts'?'pace':'systems'} board={{...snap.s6,systems:snap.s6.systems.filter(x=>match(x.name+' '+x.location_name)&&(tab!=='incidents'||x.status!=='up'))}}/></section></>}
    </div>
  </div>
}
function Reporting({ role, busy, act, reload, onCase }: { role:Role;busy:string|null;act:Act;reload:number;onCase:(id:string)=>void }) {
  const [reports,setReports]=useState<Report[]>([]), [cases,setCases]=useState<Awaited<ReturnType<typeof api.listCases>>>([])
  const [error,setError]=useState(''),[add,setAdd]=useState(false),[query,setQuery]=useState(''),[attachTo,setAttachTo]=useState<Record<string,string>>({})
  useEffect(()=>{let alive=true;Promise.all([api.listReports(),api.listCases()]).then(([r,c])=>{if(alive){setReports(r);setCases(c);setError('')}}).catch(e=>{if(alive)setError(String(e))});return()=>{alive=false}},[reload,role])
  return <><div className="ws-toolbar"><input type="search" aria-label="Search reporting" placeholder="Search reporting…" value={query} onChange={e=>setQuery(e.target.value)}/>{['battle_captain','analyst','security','ep','ea'].includes(role)&&<button className="ws-primary" onClick={()=>setAdd(!add)}>Add report</button>}</div>{error&&<p className="ws-error" role="alert">{error}</p>}{add&&<section className="ws-card"><ReportForm role={role} busy={busy} act={act} cases={cases} defaultCase={null} onDone={()=>setAdd(false)}/></section>}{reports.filter(r=>(r.text+' '+r.reported_by+' '+r.place).toLowerCase().includes(query.toLowerCase())).map(r=><article className="ws-card" key={r.id}><p className="ws-kicker">{r.kind} · {r.grade} · {r.reported_by} · {new Date(r.at).toLocaleString()}</p><p className="ws-source">{r.text}</p><p className="dim">{r.place||'Location unspecified'}</p>{!r.case_id&&['analyst','battle_captain'].includes(role)&&<div className="ws-actions"><select aria-label="Attach report to case" value={attachTo[r.id]??''} onChange={e=>setAttachTo({...attachTo,[r.id]:e.target.value})}><option value="">Choose case…</option>{cases.filter(c=>c.status==='open').map(c=><option key={c.id} value={c.id}>{c.title}</option>)}</select><button disabled={!!busy||!attachTo[r.id]} onClick={()=>act('attaching report',()=>api.attachReport(r.id,attachTo[r.id]))}>Attach to case</button></div>}{r.case_id&&<button className="ws-link" onClick={()=>onCase(r.case_id!)}>Open case →</button>}</article>)}{reports.length===0&&!error&&<div className="ws-empty">No reporting yet. Add a report to start an investigation.</div>}</>
}
function AssessmentCard({assessment:a,role,canEdit,busy,act}:{assessment:Assessment;role:Role;canEdit:boolean;busy:string|null;act:Act}) {
  const [text,setText]=useState(a.bluf),[edit,setEdit]=useState(false)
  return <article className="ws-card"><p className="ws-kicker">{a.id} · {a.status} · {a.confidence} confidence</p><h2>{a.title}</h2>{edit?<textarea value={text} onChange={e=>setText(e.target.value)} rows={5}/>:<p>{a.bluf}</p>}<details><summary>Evidence & gaps</summary>{a.evidence.map(e=><p key={e.threat_id}>{e.title} · {e.source}</p>)}{a.gaps.map((g,i)=><p key={i}>{g}</p>)}</details>{canEdit&&['draft','review'].includes(a.status)&&<div className="ws-actions"><button onClick={()=>setEdit(!edit)}>Edit summary</button>{edit&&<button disabled={!!busy} onClick={()=>act('saving assessment',async()=>{await api.editAssessment(a.id,text);setEdit(false)})}>Save</button>}{a.status==='draft'&&<button disabled={!!busy} onClick={()=>act('sending assessment to review',()=>api.setAssessmentStatus(a.id,'review'))}>Send to review</button>}{a.status==='review'&&role==='battle_captain'&&a.confidence!=='insufficient'&&<button disabled={!!busy} onClick={()=>act('approving assessment',()=>api.setAssessmentStatus(a.id,'approved'))}>Approve</button>}</div>}</article>
}
