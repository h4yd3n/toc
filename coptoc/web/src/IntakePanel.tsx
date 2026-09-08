import { useEffect, useState } from 'react'
import './App.css'
import * as api from './api'
import type { Snapshot } from './types'
import type { IntakeProposal, IntakeSubmission } from './api'

type Act = (label:string,fn:()=>Promise<unknown>)=>void
const labels:Record<string,string>={description:'Description',ref:'Reference',quantity:'Quantity (include units)',eta:'ETA (with timezone)',status:'Shipment status',carrier:'Carrier',note:'Note'}
const date=(s:string)=>new Date(s.endsWith('Z')?s:s+'Z').toLocaleString()
export function IntakePanel({snap,canEdit,act,busy,reload,selected,onSelect}:{snap:Snapshot;canEdit:boolean;act:Act;busy:string|null;reload:number;selected:string|null;onSelect:(id:string|null)=>void}) {
  const [items,setItems]=useState<IntakeSubmission[]>([]),[detail,setDetail]=useState<IntakeSubmission|null>(null)
  const [error,setError]=useState(''),[configured,setConfigured]=useState(false),[text,setText]=useState(''),[file,setFile]=useState<File|null>(null)
  const [location,setLocation]=useState(''),[history,setHistory]=useState(false),[mine,setMine]=useState(false)
  const [refresh,setRefresh]=useState(0)
  useEffect(()=>{
    let alive=true
    const load=async()=>{try {const board=await api.listIntake();const next=selected?await api.getIntake(selected):null;if(alive){setItems(board.items);setConfigured(board.provider.configured);setDetail(next);setError('')}}catch(e){if(alive){setDetail(null);setError(String(e))}}}
    void load();const timer=window.setInterval(load,10000);return()=>{alive=false;window.clearInterval(timer)}
  },[reload,selected,refresh])
  const run=(name:string,fn:()=>Promise<unknown>)=>act(name,async()=>{await fn();setRefresh(x=>x+1)})
  const destinations=snap.locations.filter(l=>l.sensitivity!=='restricted')
  const visible=items.filter(i=>(!mine||i.owner===snap.me?.name)&&(history||i.pending>0||['queued','processing','failed'].includes(i.status)))
  return <section className="intake-panel">
    {!selected&&<>
      <section className="ws-card intake-capture"><p className="ws-kicker">Provide an update</p><h2>Let the source do the typing</h2><p>Paste a delivery update or attach a manifest. Review the proposed shipment changes before they reach the COP.</p>
        {!configured&&<p className="ws-notice">AI is not configured. You can save a source now; extraction will show a setup error until a provider, model and key are configured in Settings.</p>}
        {canEdit&&<form className="ws-form" onSubmit={e=>{e.preventDefault();run('saving source',async()=>{const saved=file?await api.submitIntakeFile(file,location):await api.submitIntakeText(text,location);setText('');setFile(null);onSelect(saved.id)})}}>
          <label>Destination for this submission<select required value={location} onChange={e=>setLocation(e.target.value)}><option value="">Select a destination…</option>{destinations.map(l=><option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
          <label>Delivery update<textarea rows={4} maxLength={60000} disabled={!!file} value={text} onChange={e=>setText(e.target.value)} placeholder="Paste the original update, including shipment references, quantities, dates and timezones…" /></label>
          <label>Or attach a text-based PDF<input type="file" accept="application/pdf,.pdf" onChange={e=>{const f=e.target.files?.[0]??null;if(f&&f.size>2*1024*1024){setError('Maximum PDF size is 2 MB');e.target.value='';return}setFile(f);setError('')}}/></label>
          <p className="dim">One destination per submission · PDF up to 2 MB / 20 pages · Selectable text required. Scans, images and voice are not supported yet.</p>
          <button className="ws-primary" disabled={!!busy||!location||(!file&&text.trim().length<10)}>Prepare changes</button>
        </form>}
      </section>
      <Monitoring act={run} busy={busy} refresh={refresh+reload} canEdit={canEdit}/>
      <div className="ws-toolbar"><h2>Needs your review</h2><div className="ws-actions"><label><input type="checkbox" checked={mine} onChange={e=>setMine(e.target.checked)}/> Submitted by me</label><label><input type="checkbox" checked={history} onChange={e=>setHistory(e.target.checked)}/> Include resolved</label></div></div>
      {visible.length===0&&<p className="ws-empty">No submissions in this view.</p>}
      {visible.map(i=><button className="ws-card intake-summary" key={i.id} onClick={()=>onSelect(i.id)}><span><strong>{i.filename}</strong><span className="dim">{snap.locations.find(l=>l.id===i.location_id)?.name} · {i.owner} · {date(i.created_at)}</span></span><span>{i.status==='review'?`${i.pending} to review · ${i.applied} applied`:i.status}</span></button>)}
    </>}
    {error&&<p className="ws-error" role="alert">{error}</p>}
    {selected&&<><button className="ws-link" onClick={()=>onSelect(null)}>← All updates</button>{!detail&&!error&&<p>Loading source…</p>}</>}
    {detail&&<><div className="ws-toolbar"><div><p className="ws-kicker">{detail.status} · {detail.attempts} processing attempts</p><h2>{detail.filename}</h2><p className="dim">{detail.owner} · {date(detail.created_at)}{detail.meta.provider&&` · ${detail.meta.provider} / ${detail.meta.model}`}</p></div><button onClick={()=>run('downloading source',()=>api.downloadIntakeSource(detail.id))}>Download original</button></div>
      {detail.error&&<p className="ws-error" role="alert">{detail.error}</p>}
      {detail.status==='failed'&&canEdit&&<button disabled={!!busy} onClick={()=>run('retrying extraction',()=>api.retryIntake(detail.id))}>Retry extraction</button>}
      {['queued','processing'].includes(detail.status)&&<p className="ws-notice">Your source is saved. Processing continues in the background; you can leave this screen.</p>}
      {detail.meta.gaps?.map((g,i)=><p className="ws-notice" key={i}>{g}</p>)}
      <div className="intake-review"><aside className="ws-card intake-source"><h3>Original source</h3>{detail.pages?.map(p=><section key={p.page}><p className="ws-kicker">Page {p.page}</p><p className="ws-source">{p.text}</p></section>)}</aside>
        <div>{detail.status==='review'&&!detail.proposals?.length&&<p className="ws-empty">No supported shipment changes were extracted. Review the gaps or provide a clearer source.</p>}{detail.proposals?.map(p=><Proposal key={p.id+':'+p.revision} proposal={p} detail={detail} snap={snap} canEdit={canEdit} busy={busy} run={run}/>)}</div>
      </div>
    </>}
  </section>
}
function Proposal({proposal:p,detail,snap,canEdit,busy,run}:{proposal:IntakeProposal;detail:IntakeSubmission;snap:Snapshot;canEdit:boolean;busy:string|null;run:Act}) {
  const [editing,setEditing]=useState(false),[values,setValues]=useState(p.values),[target,setTarget]=useState(p.target_id??''),[note,setNote]=useState('')
  const editable=!['applied','rejected','unchanged'].includes(p.status)&&canEdit
  const shipments=snap.s4.shipments.filter(s=>s.to_location_id===detail.location_id)
  const fields=editing?Object.keys(labels):Object.keys(p.values)
  return <article className="ws-card intake-proposal"><p className="ws-kicker">{p.status.replaceAll('_',' ')} · Revision {p.revision}</p><h3>{p.values.description||p.values.ref||'Shipment update'}</h3>
    <p className="dim">{p.target_id?`Shipment: ${p.target_id}`:p.current._create?'New shipment confirmed':'Select a shipment or confirm creation'}</p>
    {p.questions.map((q,i)=><p className="ws-notice" key={i}>{q}</p>)}
    {editing&&<label className="intake-label">Target shipment<select value={target} onChange={e=>setTarget(e.target.value)}><option value="">Choose a target…</option><option value="__new">Create a new shipment</option>{shipments.map(s=><option key={s.id} value={s.id}>{s.description} · {s.ref||s.id}</option>)}</select></label>}
    <div className="intake-comparison"><table><thead><tr><th>Field</th><th>{p.status==='applied'?'Before':'Current'}</th><th>{p.status==='applied'?'Applied':'Proposed'}</th></tr></thead><tbody>{fields.map(k=><tr key={k}><th>{labels[k]||k}</th><td>{p.current[k]||'—'}</td><td>{editing?<input aria-label={`Proposed ${labels[k]}`} value={values[k]??''} onChange={e=>setValues({...values,[k]:e.target.value})}/>:p.values[k]||'—'}</td></tr>)}</tbody></table></div>
    <details><summary>Supporting evidence</summary>{p.evidence.map(e=><blockquote key={e.field}><p className="ws-kicker">{labels[e.field]} · Page {e.page}</p>{e.quote}</blockquote>)}<p className="dim">A matching quotation provides traceability. Review whether it supports the proposed value.</p></details>
    {editable&&<><label className="intake-label">Review note<textarea rows={2} value={note} onChange={e=>setNote(e.target.value)} placeholder="Explain corrections, resolved questions, or rejection…"/></label><div className="ws-actions">
      {editing?<><button disabled={!!busy||!target||!note.trim()} onClick={()=>run('saving clarification',()=>api.reviewIntake(detail.id,p.id,{revision:p.revision,action:'save',values:Object.fromEntries(Object.entries(values).filter(([,v])=>v.trim())),target_id:target==='__new'?undefined:target,create_new:target==='__new',note}))}>Save comparison</button><button onClick={()=>setEditing(false)}>Cancel edit</button></>:<><button onClick={()=>setEditing(true)}>Edit / resolve</button><button className="ws-primary" disabled={!!busy||p.status!=='ready'} onClick={()=>run('applying approved changes',()=>api.reviewIntake(detail.id,p.id,{revision:p.revision,action:'apply',note}))}>Approve & apply</button><button disabled={!!busy} onClick={()=>run('rejecting proposal',()=>api.reviewIntake(detail.id,p.id,{revision:p.revision,action:'reject',note}))}>Reject</button></>}
    </div></>}
    {!!p.history.length&&<details><summary>Review history</summary>{p.history.map((h,i)=><p key={i}>{h.at?date(h.at):''} · {h.actor} · {h.action}{h.status?` → ${h.status}`:''}{h.note?` — ${h.note}`:''}</p>)}</details>}
  </article>
}

function Monitoring({act,busy,refresh,canEdit}:{act:Act;busy:string|null;refresh:number;canEdit:boolean}) {
  const [clock,setClock]=useState(()=>Date.now())
  const [board,setBoard]=useState<{rule:string;items:api.IntakeFinding[]}|null>(null),[error,setError]=useState(''),[all,setAll]=useState(false),[notes,setNotes]=useState<Record<string,string>>({})
  useEffect(()=>{let alive=true;const load=()=>api.getIntakeFindings().then(b=>{if(alive){setBoard(b);setClock(Date.now());setError('')}}).catch(e=>{if(alive)setError(String(e))});void load();const timer=window.setInterval(load,30000);return()=>{alive=false;window.clearInterval(timer)}},[refresh])
  return <details className="ws-card"><summary>Monitoring · delivery records ({board?.items.filter(i=>i.status==='open').length??0})</summary><p className="dim">{board?.rule}</p><p className="dim">This check uses recorded dates and status; it does not call an AI provider.</p>{error&&<p className="ws-error">{error}</p>}<label><input type="checkbox" checked={all} onChange={e=>setAll(e.target.checked)}/> Include dismissed, snoozed and resolved</label>{board?.items.filter(i=>all||i.status==='open').map(i=><article className="ws-card" key={i.id}><p>{i.title}</p><p className="dim">{i.status} · Last checked {date(i.checked_at)}{clock-new Date(i.checked_at+'Z').getTime()>120000?' · Check is stale':''}</p>{canEdit&&i.status!=='resolved'&&<><label className="intake-label">Reason<input value={notes[i.id]??''} onChange={e=>setNotes({...notes,[i.id]:e.target.value})}/></label><div className="ws-actions">{(i.status==='open'?['dismiss','snooze']:['reopen']).map(action=><button key={action} disabled={!!busy||!notes[i.id]?.trim()} onClick={()=>act('updating monitoring',()=>api.decideIntakeFinding(i.id,i.revision,action,notes[i.id]))}>{action==='snooze'?'Snooze 24 hours':action==='reopen'?'Reopen':'Dismiss'}</button>)}</div></>}{!!i.history.length&&<details><summary>Decision history</summary>{i.history.map((h,n)=><p key={n}>{h.actor} · {h.action} · {h.note}</p>)}</details>}</article>)}{board&&!board.items.length&&<p>No evaluated delivery exceptions yet. Checks run with the background worker.</p>}</details>
}
