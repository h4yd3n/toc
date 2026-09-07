import { useState } from 'react'
import * as api from './api'
import type { Person, Selection, Snapshot } from './types'
type Act=(label:string,fn:()=>Promise<unknown>)=>void
export function PersonForm({snap,busy,act,onDone}:{snap:Snapshot;busy:string|null;act:Act;onDone:()=>void}) {
  const [f,setF]=useState({name:'',role:'Staff',team_id:snap.teams[0]?.id??'',email:'',phone:''})
  return <form className="ws-form" onSubmit={e=>{e.preventDefault();act('adding person',async()=>{await api.createPerson(f);onDone()})}}><h2>Add person</h2><label>Name<input required value={f.name} onChange={e=>setF({...f,name:e.target.value})}/></label><label>Role<input required value={f.role} onChange={e=>setF({...f,role:e.target.value})}/></label><label>Team<select required value={f.team_id} onChange={e=>setF({...f,team_id:e.target.value})}>{snap.teams.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label><label>Email<input type="email" value={f.email} onChange={e=>setF({...f,email:e.target.value})}/></label><label>Phone<input type="tel" value={f.phone} onChange={e=>setF({...f,phone:e.target.value})}/></label><div className="ws-actions"><button className="ws-primary" disabled={!!busy}>Save person</button><button type="button" onClick={onDone}>Cancel</button></div></form>
}
export function EventForm({snap,busy,act,onDone}:{snap:Snapshot;busy:string|null;act:Act;onDone:()=>void}) {
  const [f,setF]=useState({name:'',venue_location_id:snap.locations[0]?.id??'',start_at:'',end_at:'',description:''})
  const valid=f.start_at&&f.end_at&&new Date(f.end_at)>new Date(f.start_at)
  return <form className="ws-form" onSubmit={e=>{e.preventDefault();if(!valid)return;act('creating activity',async()=>{await api.createEvent({...f,start_at:new Date(f.start_at).toISOString(),end_at:new Date(f.end_at).toISOString(),generate_trips:false});onDone()})}}><h2>Create activity</h2><label>Name<input required value={f.name} onChange={e=>setF({...f,name:e.target.value})}/></label><label>Site<select required value={f.venue_location_id} onChange={e=>setF({...f,venue_location_id:e.target.value})}>{snap.locations.map(l=><option key={l.id} value={l.id}>{l.name}</option>)}</select></label><label>Start (local time)<input type="datetime-local" required value={f.start_at} onChange={e=>setF({...f,start_at:e.target.value})}/></label><label>End (local time)<input type="datetime-local" required value={f.end_at} onChange={e=>setF({...f,end_at:e.target.value})}/></label><label>Description<textarea value={f.description} onChange={e=>setF({...f,description:e.target.value})}/></label>{f.end_at&&!valid&&<p className="ws-error">End must be after start.</p>}<div className="ws-actions"><button className="ws-primary" disabled={!!busy||!valid}>Create activity</button><button type="button" onClick={onDone}>Cancel</button></div></form>
}

export function StaffRecordForm({kind,snap,busy,act,onDone}:{kind:'supply'|'shipment'|'system';snap:Snapshot;busy:string|null;act:Act;onDone:()=>void}) {
  const [f,setF]=useState({name:'',location:snap.locations[0]?.id??'',on_hand:'0',required:'0',unit:'ea',quantity:'',eta:'',pace:'',status:'up',note:''})
  const set=(field:keyof typeof f,value:string)=>setF({...f,[field]:value})
  const submit=async()=>{
    if(kind==='supply') await api.createSupply({item:f.name,location_id:f.location||null,on_hand:+f.on_hand,required:+f.required,unit:f.unit,note:f.note})
    if(kind==='shipment') await api.createShipment({description:f.name,quantity:f.quantity,to_location_id:f.location||null,eta:new Date(f.eta).toISOString(),note:f.note})
    if(kind==='system') await api.createSystem({name:f.name,location_id:f.location||null,pace:f.pace||null,status:f.status,note:f.note})
    onDone()
  }
  return <form className="ws-form" onSubmit={e=>{e.preventDefault();act('saving '+kind,submit)}}>
    <h2>{kind==='supply'?'Add inventory line':kind==='shipment'?'Add shipment':'Add communications system'}</h2>
    <label>{kind==='shipment'?'Description':'Name'}<input required value={f.name} onChange={e=>set('name',e.target.value)}/></label>
    <label>{kind==='shipment'?'Destination site':'Site'}<select required value={f.location} onChange={e=>set('location',e.target.value)}>{snap.locations.map(l=><option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
    {kind==='supply'&&<><label>On hand<input type="number" required min={0} step="any" value={f.on_hand} onChange={e=>set('on_hand',e.target.value)}/></label><label>Required<input type="number" required min={0} step="any" value={f.required} onChange={e=>set('required',e.target.value)}/></label><label>Unit<input required value={f.unit} onChange={e=>set('unit',e.target.value)}/></label></>}
    {kind==='shipment'&&<><label>Quantity<input required value={f.quantity} onChange={e=>set('quantity',e.target.value)}/></label><label>Expected arrival (local time)<input type="datetime-local" required value={f.eta} onChange={e=>set('eta',e.target.value)}/></label></>}
    {kind==='system'&&<><label>Fallback role<select value={f.pace} onChange={e=>set('pace',e.target.value)}><option value="">No PACE role</option>{['primary','alternate','contingency','emergency'].map(v=><option key={v}>{v}</option>)}</select></label><label>System status<select value={f.status} onChange={e=>set('status',e.target.value)}>{['up','degraded','down'].map(v=><option key={v}>{v}</option>)}</select></label></>}
    <label>Note<textarea value={f.note} onChange={e=>set('note',e.target.value)}/></label>
    <div className="ws-actions"><button className="ws-primary" disabled={!!busy}>Save {kind}</button><button type="button" onClick={onDone}>Cancel</button></div>
  </form>
}

export function PersonnelList({people,canEdit,busy,act,onSelect}:{people:Person[];canEdit:boolean;busy:string|null;act:Act;onSelect:(s:Selection)=>void}) {
  const [limit,setLimit]=useState(50)
  const [editing,setEditing]=useState<Person|null>(null)
  const [onShift,setOnShift]=useState(false),[shiftRole,setShiftRole]=useState('')
  return <><p className="dim">{people.length} personnel · showing {Math.min(limit,people.length)}</p>
    {editing&&<form className="ws-form" onSubmit={e=>{e.preventDefault();act('updating assignment',async()=>{await api.updatePersonAssignment(editing.id,{on_shift:onShift,shift_role:shiftRole||null});setEditing(null)})}}><h3>{editing.name}</h3><label>Duty status<select value={onShift?'on':'off'} onChange={e=>setOnShift(e.target.value==='on')}><option value="on">On shift</option><option value="off">Off shift</option></select></label>{onShift&&<label>Assigned role<input value={shiftRole} onChange={e=>setShiftRole(e.target.value)}/></label>}<div className="ws-actions"><button disabled={!!busy}>Save assignment</button><button type="button" onClick={()=>setEditing(null)}>Cancel</button></div></form>}
    <div className="ws-record-list">{people.slice(0,limit).map(p=><div className="ws-person-row" key={p.id}><button onClick={()=>onSelect({type:'person',id:p.id})}><strong>{p.name}</strong><span>{p.team_name}</span><span>{p.availability.replace('_',' ')}</span></button>{canEdit&&<button className="ws-link" onClick={()=>{setEditing(p);setOnShift(p.on_shift);setShiftRole(p.shift_role??'')}}>Update duty</button>}</div>)}</div>
    {limit<people.length&&<button onClick={()=>setLimit(limit+50)}>Show 50 more</button>}
  </>
}
