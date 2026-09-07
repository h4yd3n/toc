import { useEffect, useState } from 'react'
import * as api from './api'
import type { Case, Location, Role, SectionCode } from './types'
import type { WorkAnalysis, WorkBoard, WorkRun } from './api'

type Act = (label: string, fn: () => Promise<unknown>) => void
const date = (s: string | null) => s ? new Date(s.endsWith('Z') ? s : s + 'Z').toLocaleString() : 'Not yet'
const defaults: Record<SectionCode, string> = {
  S1: 'Review personnel availability and identify conflicting records or staffing gaps. Cite the records and prepare recommended follow-up.',
  S2: 'Compare the reporting, identify supported findings and contradictions, explain collection gaps, and prepare an assessment with cited evidence.',
  S3: 'Review upcoming activities for schedule conflicts and resource dependencies. Explain supported gaps and propose follow-up tasks.',
  S4: 'Review stock and shipments for shortages and delays. Cite the quantities and propose support requests.',
  S6: 'Review system outages and recorded fallback coverage. Explain communications gaps and propose follow-up actions.',
}
export function WorkPanel({ section, caseId, role, canEdit, reload, act, busy, onOpenCase, selectedRun, locations = [] }: { locations?: Location[]; section?: SectionCode; caseId?: string | null; role: Role; canEdit: (s: SectionCode) => boolean; reload: number; act: Act; busy: string | null; onOpenCase?: (id: string) => void; selectedRun?: string | null }) {
  const defaultScope = section ?? (canEdit('S2') ? 'S2' : (Object.keys(defaults) as SectionCode[]).find(canEdit) ?? 'S2')
  const [board, setBoard] = useState<WorkBoard | null>(null)
  const [error, setError] = useState('')
  const [create, setCreate] = useState(false)
  const [editingAssignment,setEditingAssignment]=useState<string|null>(null)
  const [scope, setScope] = useState<SectionCode>(defaultScope)
  const [cases, setCases] = useState<Case[]>([])
  const [chosenCase, setChosenCase] = useState(caseId ?? '')
  const [instruction, setInstruction] = useState(defaults[defaultScope])
  const [cadence, setCadence] = useState(0)
  const [locationId, setLocationId] = useState('')
  const [open, setOpen] = useState<string | null>(selectedRun ?? null)
  const [filter, setFilter] = useState('attention')
  useEffect(() => { setOpen(selectedRun ?? null) }, [selectedRun])
  useEffect(() => { setScope(defaultScope); setLocationId(''); setChosenCase(caseId ?? ''); setInstruction(defaults[defaultScope]) }, [defaultScope, caseId])
  useEffect(() => {
    let alive = true
    const load = () => api.getWork().then(b => { if (alive) { setBoard(b); setError('') } }).catch(e => { if (alive) setError(String(e)) })
    void load(); const interval = window.setInterval(load, 10000)
    return () => { alive = false; window.clearInterval(interval) }
  }, [reload, role])
  useEffect(() => { let alive = true; if (scope === 'S2') api.listCases().then(c => { if (alive) setCases(c) }).catch(() => {}); return () => { alive = false } }, [scope, role, reload])
  const assignments = board?.assignments.filter(a => (!section || a.section === section) && (!caseId || a.case_id === caseId)) ?? []
  const ids = new Set(assignments.map(a => a.id))
  const runs = board?.runs.filter(r => ids.has(r.assignment_id)) ?? []
  const actionable = (r: WorkRun) => r.status === 'failed' || r.status === 'queued' || r.status === 'running' || r.status === 'completed' && ['draft', 'review'].includes(r.review_status)
  const visible = runs.filter(r => r.id === open || filter === 'all' || (filter === 'released' ? r.review_status === 'released' : actionable(r))).sort((a,b) => b.created_at.localeCompare(a.created_at))
  return <section className="work-panel">
    <div className="ws-toolbar"><div><h2>{caseId ? 'Case analysis' : 'AI assignments & products'}</h2><p className="dim">Assign work, inspect the evidence, and review prepared findings.</p></div>
      {(section ? canEdit(section) : Object.keys(defaults).some(s => canEdit(s as SectionCode))) && <button className="ws-primary" onClick={() => {setEditingAssignment(null);setCreate(!create)}}>Assign analysis</button>}</div>
    {error && <p role="alert" className="ws-error">{error}</p>}
    {board && <p className="ws-notice">{board.provider.configured ? `Provider: ${board.provider.provider} · ${board.provider.model}` : 'AI provider is off or incomplete. Configure the staff analysis provider, model, and API key in Settings.'} Drafts require review before release.</p>}
    {create && <form className="ws-form" onSubmit={e => { e.preventDefault(); act('assigning analysis', async () => { if(editingAssignment) await api.editWork(editingAssignment,instruction,cadence); else await api.assignWork({ section: scope, case_id: chosenCase || undefined, location_id: locationId || undefined, instruction, cadence_minutes: cadence }); setCreate(false) }) }}>
      {!section && <label>Staff section<select disabled={!!editingAssignment} value={scope} onChange={e => { setScope(e.target.value as SectionCode); setInstruction(defaults[e.target.value as SectionCode]); setChosenCase(''); setLocationId('') }}>{Object.keys(defaults).filter(s => canEdit(s as SectionCode)).map(s => <option key={s}>{s}</option>)}</select></label>}
      {scope === 'S2' && <label>Evidence scope<select disabled={!!editingAssignment} value={chosenCase} onChange={e => setChosenCase(e.target.value)}><option value="">Accessible reporting and threat picture</option>{cases.filter(c => c.status === 'open').map(c => <option key={c.id} value={c.id}>{c.title}</option>)}</select></label>}
      {scope !== 'S2' && <label>Site scope<select disabled={!!editingAssignment} value={locationId} onChange={e=>setLocationId(e.target.value)}><option value="">All accessible sites</option>{locations.map(l=><option key={l.id} value={l.id}>{l.name}</option>)}</select></label>}
      <label>Assignment<textarea required minLength={10} maxLength={4000} rows={4} value={instruction} onChange={e => setInstruction(e.target.value)} /></label>
      <label>Check for changes<select value={cadence} onChange={e => setCadence(+e.target.value)}><option value={0}>One analysis</option><option value={15}>Every 15 minutes</option><option value={60}>Every hour</option><option value={1440}>Daily</option></select></label>
      <div className="ws-actions"><button className="ws-primary" disabled={!!busy || !canEdit(scope)}>{editingAssignment?'Save and rerun':'Save assignment'}</button><button type="button" onClick={() => setCreate(false)}>Cancel</button></div>
    </form>}
    <div className="ws-tabs" aria-label="Result filters">{[['attention','Needs attention'],['released','Released'],['all','All activity']].map(([v,l]) => <button key={v} aria-pressed={filter === v} onClick={() => setFilter(v)}>{l}{v === 'attention' ? ` (${runs.filter(actionable).length})` : ''}</button>)}</div>
    {visible.length === 0 && <div className="ws-empty">{board ? 'No results in this view. Create an assignment to prepare an analysis.' : 'Loading assignments…'}</div>}
    {visible.map(r => { const a = assignments.find(a => a.id === r.assignment_id)!; return <article className="ws-card" key={r.id}>
      <button className="ws-result-heading" onClick={() => setOpen(open === r.id ? null : r.id)} aria-expanded={open === r.id}><span><span className="ws-kicker">{a.section} · {r.status === 'completed' ? r.review_status : r.status}</span><strong>{r.result.title || a.instruction}</strong></span><span className="dim">{date(r.created_at)}</span></button>
      {r.error && <p className="ws-error">{r.error}</p>}
      {open === r.id && <><p className="dim">Assigned by {a.owner} · {r.provider && `${r.provider} / ${r.model} · `}Last successful check: {date(a.last_success_at)}</p>
        {a.case_id && onOpenCase && <button className="ws-link" onClick={() => onOpenCase(a.case_id!)}>Open supporting case →</button>}
        {r.status === 'completed' && <ResultEditor caseScoped={!!a.case_id || r.evidence.some(e=>!!e.case_id)} key={r.id + ':' + r.revision} run={r} editable={canEdit(a.section)} role={role} busy={busy} act={act} />}
        {r.status === 'unchanged' && <p>Evidence is unchanged since the last successful analysis.</p>}
      </>}
    </article> })}
    {assignments.length > 0 && <details className="ws-card"><summary>Manage assignments ({assignments.length})</summary>{assignments.map(a => <div className="ws-assignment" key={a.id}><strong>{a.instruction}</strong><p className="dim">{a.section} · {a.status} · {a.cadence_minutes ? `Checks every ${a.cadence_minutes} minutes` : 'One analysis'} · {a.owner}</p>{canEdit(a.section) && a.status !== 'cancelled' && <div className="ws-actions">{<button disabled={!!busy} onClick={()=>{setEditingAssignment(a.id);setScope(a.section);setChosenCase(a.case_id??'');setLocationId(a.location_id??'');setInstruction(a.instruction);setCadence(a.cadence_minutes);setCreate(true)}}>Edit</button>}{['run', a.status === 'paused' ? 'resume' : 'pause', 'cancel'].map(action => <button key={action} disabled={!!busy} onClick={() => act(action + ' assignment', () => api.changeWork(a.id, action as 'run' | 'resume' | 'pause' | 'cancel'))}>{action === 'run' ? 'Run again' : action}</button>)}</div>}</div>)}</details>}
  </section>
}
function ResultEditor({ run, editable, role, busy, act, caseScoped }: { caseScoped: boolean; run: WorkRun; editable: boolean; role: Role; busy: string | null; act: Act }) {
  const [result, setResult] = useState(run.result as WorkAnalysis)
  const [edit, setEdit] = useState(false)
  const [note, setNote] = useState('')
  const [taskSection,setTaskSection]=useState<SectionCode>(caseScoped ? 'S2' : 'S3')
  const [createdTasks,setCreatedTasks]=useState<Record<number,string>>({})
  const can = editable && ['draft','review'].includes(run.review_status)
  const submit = (action: 'save' | 'review' | 'release' | 'reject') => act(action + ' analysis', async () => { await api.reviewWork(run.id, run.revision, action, result, note); setEdit(false) })
  return <div className="ws-analysis">
    {edit ? <label>Assessment summary<textarea rows={5} value={result.summary} onChange={e => setResult({ ...result, summary: e.target.value })} /></label> : <p className="ws-summary">{result.summary}</p>}
    <h3>Findings & evidence</h3>
    {result.findings.map((f,i) => <div className="ws-finding" key={i}>{edit ? <textarea value={f.claim} onChange={e => setResult({ ...result, findings: result.findings.map((x,j) => i === j ? { ...x, claim: e.target.value } : x) })} /> : <p>{f.claim}</p>}{f.uncertainty && <p className="dim">Uncertainty: {f.uncertainty}</p>}{f.citations.map((c,j) => <details className="ws-citation" key={j}><summary>{run.evidence.find(e => e.id === c.source_id)?.label ?? c.source_id}</summary><blockquote>{c.quote}</blockquote><details><summary>Read source</summary><p className="ws-source">{run.evidence.find(e => e.id === c.source_id)?.text}</p></details></details>)}</div>)}
    {result.gaps.length > 0 && <><h3>Gaps & competing explanations</h3><ul className="ws-bullets">{result.gaps.map((g,i) => <li key={i}>{g}</li>)}</ul></>}
    {result.proposed_tasks.length > 0 && <><h3>Proposed follow-up</h3>{caseScoped && <p className="dim">Case follow-up stays in S2. The shared task board links to this restricted product without copying case details.</p>}<ul className="ws-bullets">{result.proposed_tasks.map((g,i) => <li key={i}>{g}{editable && ['review','released'].includes(run.review_status) && <button className="ws-link" disabled={!!busy || !!createdTasks[i]} onClick={()=>act('creating follow-up task',async()=>{const t=await api.createWorkTask(run.id,i,taskSection);setCreatedTasks(s=>({...s,[i]:t.id}))})}>{createdTasks[i]?'Task created':`Assign to ${taskSection}`}</button>}</li>)}</ul>{editable && ['review','released'].includes(run.review_status) ? <label>Assign follow-up to<select value={taskSection} onChange={e=>setTaskSection(e.target.value as SectionCode)}>{(caseScoped ? ['S2'] : ['S1','S2','S3','S4','S6']).map(s=><option key={s}>{s}</option>)}</select></label> : <p className="dim">Send this analysis to review before assigning follow-up tasks.</p>}</>}
    {can && <><label>Review note<input value={note} onChange={e => setNote(e.target.value)} placeholder="Corrections, judgment, or reason for rejection" /></label><div className="ws-actions"><button onClick={() => setEdit(!edit)}>{edit ? 'Read draft' : 'Edit draft'}</button>{edit && <button disabled={!!busy} onClick={() => submit('save')}>Save changes</button>}<button disabled={!!busy} onClick={() => submit('review')}>Send to review</button>{role === 'battle_captain' && run.review_status === 'review' && <button className="ws-primary" disabled={!!busy} onClick={() => submit('release')}>Release to COP</button>}<button disabled={!!busy} onClick={() => submit('reject')}>Reject</button></div></>}
    {run.history.length > 0 && <details><summary>Review history ({run.history.length})</summary>{run.history.map((h,i) => <p key={i}>{date(h.at)} · {h.actor} · {h.action}{h.note && ` — ${h.note}`}</p>)}</details>}
  </div>
}
