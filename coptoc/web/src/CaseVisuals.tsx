import { useState } from 'react'
import type { CaseDetail, CaseEntity, CaseEvent, Evidence } from './types'

// §5.11 — the three views over one graph. The case's own evidence is blue (confirmed) or amber (suggested); the live
// picture Sigtoc owns is red: an actor as a node, each of its sightings as a dated event, and a dotted line to every
// entity the same report produced. A red line is derived arithmetic, not an analyst's confirmation, so it is never
// solid and it never enters the review queue.
const NODE_COLOR = (n: CaseEntity) => n.type === 'actor' ? '#ef4444' : n.status === 'confirmed' ? '#60a5fa' : '#f59e0b'
const isLive = (x: { origin?: string }) => x.origin === 'sigtoc'
const eventKind = (e: CaseEvent) => e.type === 'sighting' ? 'SIGHTING' : e.type.toUpperCase()
/** What a line traces to: a report from our own people, or a collected signal (§5.11). */
const cited = (v: Evidence) => v.report_id ?? (v.signal_id ? `signal ${v.signal_id}` : 'unattributed')

export function CaseVisuals({ detail }: { detail: CaseDetail }) {
  const [confirmed,setConfirmed]=useState(false),[entity,setEntity]=useState(''),[view,setView]=useState('links'),[live,setLive]=useState(true)
  const keep=(x:{origin?:string;status:string})=>(live||!isLive(x))&&(!confirmed||x.status==='confirmed')
  const nodes=detail.graph.entities.filter(keep)
  const ids=new Set(nodes.map(e=>e.id))
  const edges=detail.graph.relationships.filter(e=>keep(e)&&ids.has(e.from)&&ids.has(e.to)&&(!entity||e.from===entity||e.to===entity))
  const events=detail.graph.events.filter(e=>keep(e)&&(!entity||e.participants.includes(entity))).sort((a,b)=>(a.at??'').localeCompare(b.at??''))
  const visibleNodes=nodes.filter(n=>!entity||n.id===entity||edges.some(e=>e.from===n.id||e.to===n.id)).slice(0,40)
  const points=new Map(visibleNodes.map((n,i)=>[n.id,{x:320+235*Math.cos(i/visibleNodes.length*Math.PI*2),y:220+155*Math.sin(i/visibleNodes.length*Math.PI*2)}]))
  const actors=nodes.filter(n=>n.type==='actor')
  const grid=Array.from({length:7},()=>Array<number>(24).fill(0))
  for(const e of events) if(e.at){ const d=new Date(e.at);if(!isNaN(d.getTime()))grid[(d.getUTCDay()+6)%7][d.getUTCHours()]++ }
  const max=Math.max(1,...grid.flat())
  return <section className="case-visuals"><div className="ws-toolbar"><div className="ws-tabs">{[['links','Link chart'],['timeline','Timeline'],['pattern','Time wheel']].map(([v,l])=><button key={v} aria-pressed={view===v} onClick={()=>setView(v)}>{l}</button>)}</div><label><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/> Confirmed only</label><label title="actors and their sightings, from the live S2 picture"><input type="checkbox" checked={live} onChange={e=>setLive(e.target.checked)}/> Live picture{actors.length>0?` (${actors.length} actor${actors.length===1?'':'s'})`:''}</label><select aria-label="Filter by entity" value={entity} onChange={e=>setEntity(e.target.value)}><option value="">All entities</option>{nodes.map(n=><option key={n.id} value={n.id}>{n.type==='actor'?'◆ ':''}{n.name}</option>)}</select></div>
    {view==='links'&&<><p className="dim">Solid lines: confirmed. Dashed: suggested. Dotted red: derived from a sighting and the report it came from — the actor and that report&apos;s entities. Select an entity to focus its links.</p>{visibleNodes.length>0?<svg viewBox="0 0 640 440" className="case-link-chart" role="img" aria-label="Case entity relationship chart">{edges.map(e=>{const a=points.get(e.from),b=points.get(e.to);return a&&b?<g key={e.id}><line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={e.status==='derived'?'#ef4444':e.status==='confirmed'?'#60a5fa':'#8d9eb2'} strokeDasharray={e.status==='confirmed'?undefined:e.status==='derived'?'2 4':'5 5'}/><text x={(a.x+b.x)/2} y={(a.y+b.y)/2} textAnchor="middle">{e.type} [{e.grade}]</text></g>:null})}{visibleNodes.map(n=>{const p=points.get(n.id)!;return <g key={n.id}>{n.type==='actor'?<rect x={p.x-9} y={p.y-9} width={18} height={18} transform={`rotate(45 ${p.x} ${p.y})`} fill={NODE_COLOR(n)}/>:<circle cx={p.x} cy={p.y} r={8} fill={NODE_COLOR(n)}/>}<text x={p.x} y={p.y+22} textAnchor="middle">{n.name}</text></g>})}</svg>:<p className="ws-empty">No entities match this view.</p>}<div className="ws-tabs">{nodes.map(n=><button key={n.id} aria-pressed={entity===n.id} onClick={()=>setEntity(entity===n.id?'':n.id)}>{n.type==='actor'?'◆ ':''}{n.name}</button>)}</div>{nodes.length>40&&<p className="dim">Chart displays up to 40 entities; select an entity to inspect its neighborhood.</p>}
      {actors.map(a=><details className="ws-citation" key={a.id}><summary>◆ {a.name} · {a.attributes?.kind ?? 'actor'}{a.attributes?.actor_status?` · ${a.attributes.actor_status}`:''} · {detail.graph.events.filter(v=>v.participants.includes(a.id)).length} sighting(s)</summary>{a.attributes?.assessed_intent&&<p>{a.attributes.assessed_intent}</p>}{a.attributes?.last_seen&&<p className="dim">Last seen {a.attributes.last_seen}{a.attributes.last_seen_at?` · ${new Date(a.attributes.last_seen_at).toLocaleString()}`:''}</p>}{a.evidence.map((v,i)=><blockquote key={i}>{v.quote}<footer>{cited(v)} · {v.reliability}{v.credibility}</footer></blockquote>)}</details>)}
      {edges.map(e=><details className="ws-citation" key={e.id}><summary>{nodes.find(n=>n.id===e.from)?.name} → {e.type} → {nodes.find(n=>n.id===e.to)?.name} · {e.grade} · {e.status}</summary>{e.evidence.map((v,i)=><blockquote key={i}>{v.quote}<footer>{cited(v)} · {v.reliability}{v.credibility}</footer></blockquote>)}</details>)}</>}
    {view==='timeline'&&<div className="case-timeline">{events.length===0&&<p>No dated events match this view.</p>}{events.map(e=><article key={e.id} className={isLive(e)?'live':undefined}><time>{e.at?new Date(e.at).toLocaleString():'Time unknown'}</time><span className="ws-kicker">{eventKind(e)}{e.confidence?` · ${e.confidence}`:''} · {e.status} · {e.place}</span><p>{e.summary}</p>{e.evidence.map((v,i)=><details key={i}><summary>Source {cited(v)} · {v.reliability}{v.credibility}</summary><blockquote>{v.quote}</blockquote></details>)}</article>)}</div>}
    {view==='pattern'&&<><p>Activity by weekday and hour (UTC). Counts reflect the selected evidence, including suggestions and — while the live picture is on — sightings.</p><div className="time-wheel"><table><caption>Events by day and hour</caption><thead><tr><th>UTC</th>{grid[0].map((_,h)=><th key={h}>{h}</th>)}</tr></thead><tbody>{grid.map((row,d)=><tr key={d}><th>{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][d]}</th>{row.map((n,h)=><td key={h} style={{background:n?`rgba(96,165,250,${.18+.65*n/max})`:undefined}} title={`${n} events at ${h}:00 UTC`}>{n||'·'}</td>)}</tr>)}</tbody></table></div></>}
  </section>
}
