import { useEffect, useState } from 'react'
import * as api from './api'
import type { Snapshot } from './types'

export function ActivityPanel({reload}:{reload:number}) {
  const [reads,setReads]=useState(false)
  return <details className="ws-card"><summary>Battle log · recorded activity</summary><label><input type="checkbox" checked={reads} onChange={e=>setReads(e.target.checked)}/> Include access audits</label><ActivityList key={String(reads)+':'+reload} reads={reads}/></details>
}
function ActivityList({reads}:{reads:boolean}) {
  const [items,setItems]=useState<Snapshot['log']>([])
  const [cursor,setCursor]=useState<number|null>(null)
  const [busy,setBusy]=useState(true)
  const [error,setError]=useState('')
  useEffect(()=>{let alive=true;api.getActivity(undefined,reads).then(r=>{if(alive){setItems(r.items);setCursor(r.next_cursor)}}).catch(e=>{if(alive)setError(String(e))}).finally(()=>{if(alive)setBusy(false)});return()=>{alive=false}},[reads])
  const more=async()=>{if(!cursor)return;setBusy(true);try{const r=await api.getActivity(cursor,reads);setItems(v=>[...v,...r.items]);setCursor(r.next_cursor);setError('')}catch(e){setError(String(e))}finally{setBusy(false)}}
  return <>{error&&<p role="alert">{error}</p>}{items.map(e=><p key={e.id}><time>{new Date(e.at).toLocaleString()}</time> · {e.summary} <span className="dim">— {e.actor}</span></p>)}{!busy&&!items.length&&!error&&<p>No recorded activity is available to this profile.</p>}{busy&&<p role="status">Loading activity…</p>}{cursor&&<button disabled={busy} onClick={more}>Load earlier activity</button>}</>
}
