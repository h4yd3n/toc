import { useEffect, useState } from 'react'
import * as api from './api'
import { Question } from './Headline'
import { DistributionBox } from './Operation'
import type { Dsm, Operation, PIR, Role, Selection, StaffProduct, StaffProductHead, ThreatCoa } from './types'

type Act = (l: string, f: () => Promise<unknown>) => void
const LIKELIHOOD = ['unassessed', 'almost no chance', 'very unlikely', 'unlikely', 'roughly even chance', 'likely', 'very likely', 'almost certain'] as const
const CONFIDENCE = ['low', 'moderate', 'high'] as const
const hhmm = (iso: string | null) => iso ? new Date(iso).toUTCString().slice(5, 22) + 'Z' : ''
const short = (s: string) => s.split(' — ')[0].split(' · ')[0]

/** §5.10b Phase 3 — the staff products under the S2 panel: threat COAs with ICD 203 words, the decision support
 *  matrix, and the IPB / estimate / annex drafted by rule from the wall and approved or released by a human. */
export function IpbPanel({ reload, busy, act, role, pirs, onSelect }: { reload: number; busy: string | null; act: Act; role: Role; pirs: PIR[]; onSelect: (s: Selection) => void }) {
  const [coas, setCoas] = useState<ThreatCoa[]>([])
  const [dsm, setDsm] = useState<Dsm | null>(null)
  const [heads, setHeads] = useState<StaffProductHead[]>([])
  const [ops, setOps] = useState<Operation[]>([])
  const [open, setOpen] = useState<StaffProduct | null>(null)
  const [subject, setSubject] = useState<string>('')
  const [dpForm, setDpForm] = useState<{ title: string; decision: string; trigger: string; action: string; pir_id: string; latest_time: string } | null>(null)
  useEffect(() => {
    api.listCoas().then(setCoas).catch(() => setCoas([]))
    api.getDsm().then(setDsm).catch(() => setDsm(null))
    api.listStaffProducts().then(setHeads).catch(() => setHeads([]))
    api.listOperations().then(o => { setOps(o); if (!subject && o[0]) setSubject(`operation:${o[0].id}`) }).catch(() => setOps([]))
    if (open) api.getStaffProduct(open.id).then(setOpen).catch(() => setOpen(null))
  }, [reload])
  const staff = role === 'battle_captain' || role === 'analyst', isBC = role === 'battle_captain', decider = staff || role === 'ea'
  const [stype, sid] = subject.split(':')
  const opFor = (h: { operation_id: string | null }) => ops.find(o => o.id === h.operation_id)
  const live = coas.filter(c => c.status !== 'rejected')
  return <>
    <Question q="What the other side may do" count={`${live.length} COA${live.length === 1 ? '' : 's'}${coas.some(c => c.status === 'candidate') ? ` · ${coas.filter(c => c.status === 'candidate').length} to assess` : ''}`} />
    <ul className="list cards">
      {live.map(c => <li key={c.id} className={`card coa ${c.status}`}>
        <div className="card-head"><span className="id">{c.id}</span><span className="name">{c.title}</span>
          {c.most_likely && <span className="chip ml" title="most likely">ML</span>}{c.most_dangerous && <span className="chip md" title="most dangerous">MD</span>}
          <span className={`chip ${c.status === 'assessed' ? 'approved' : 'draft'}`}>{c.status.toUpperCase()}</span></div>
        <div className="est"><b>{c.likelihood}</b>{c.likelihood !== 'unassessed' ? <span className="dim"> · {c.confidence} confidence</span> : <span className="gapword"> · AWAITING THE ANALYST</span>}{c.actor_name ? <span className="dim"> · {c.actor_name}</span> : null}</div>
        {c.narrative && <div className="bluf">{c.narrative}</div>}
        {c.indicators.length > 0 && <div className="bluf dim">Indicators: {c.indicators.join('; ')}{c.nai_ids.length ? ` · ${c.nai_ids.length} NAI${c.nai_ids.length === 1 ? '' : 's'}` : ''}</div>}
        {staff && <div className="card-foot">
          <select value={c.likelihood} disabled={!!busy} onChange={e => act('assessing the COA', () => api.updateCoa(c.id, { likelihood: e.target.value }))}>{LIKELIHOOD.map(w => <option key={w}>{w}</option>)}</select>
          <select value={c.confidence} disabled={!!busy} onChange={e => act('assessing the COA', () => api.updateCoa(c.id, { confidence: e.target.value }))}>{CONFIDENCE.map(w => <option key={w}>{w}</option>)}</select>
          <button className={`mini ${c.most_likely ? 'ok' : ''}`} disabled={!!busy || c.status !== 'assessed'} onClick={() => act('flagging most likely', () => api.updateCoa(c.id, { most_likely: !c.most_likely }))}>ML</button>
          <button className={`mini ${c.most_dangerous ? 'warn' : ''}`} disabled={!!busy || c.status !== 'assessed'} onClick={() => act('flagging most dangerous', () => api.updateCoa(c.id, { most_dangerous: !c.most_dangerous }))}>MD</button>
          <button className="mini" disabled={!!busy} onClick={() => act('rejecting the COA', () => api.updateCoa(c.id, { status: 'rejected' }))}>REJECT</button>
        </div>}
      </li>)}
      {live.length === 0 && <li className="dim small" style={{ padding: '2px 14px 6px' }}>No threat course of action yet. Draft an IPB: actors with an assessed intent become candidates.</li>}
    </ul>

    <Question q="What we decide, and when" count={dsm ? `${dsm.open} open${dsm.overdue ? ` · ${dsm.overdue} overdue` : ''}${dsm.triggered ? ` · ${dsm.triggered} triggered` : ''}` : '…'}>
      {decider && sid && <button className="mini" onClick={() => setDpForm(dpForm ? null : { title: '', decision: '', trigger: '', action: '', pir_id: '', latest_time: '' })}>+ DP</button>}
    </Question>
    {dpForm && <div className="dform">
      <div className="dform-head">DECISION POINT <span className="dim">on {stype} {sid}</span></div>
      <input placeholder="Title (DP 1 — close the north gate)" value={dpForm.title} onChange={e => setDpForm({ ...dpForm, title: e.target.value })} />
      <input placeholder="The decision" value={dpForm.decision} onChange={e => setDpForm({ ...dpForm, decision: e.target.value })} />
      <input placeholder="What we would have to see (the trigger)" value={dpForm.trigger} onChange={e => setDpForm({ ...dpForm, trigger: e.target.value })} />
      <input placeholder="What happens (the action)" value={dpForm.action} onChange={e => setDpForm({ ...dpForm, action: e.target.value })} />
      <div className="two"><select value={dpForm.pir_id} onChange={e => setDpForm({ ...dpForm, pir_id: e.target.value })}><option value="">no PIR</option>{pirs.filter(p => p.status !== 'EXPIRED').map(p => <option key={p.id} value={p.id}>{p.id} · {p.question.slice(0, 60)}</option>)}</select>
        <input type="datetime-local" title="no later than" value={dpForm.latest_time} onChange={e => setDpForm({ ...dpForm, latest_time: e.target.value })} /></div>
      <div className="row-btns"><button className="mini ok" disabled={!!busy || !dpForm.title.trim()} onClick={() => act('writing a decision point', () => api.createDecisionPoint({ ...dpForm, subject_type: stype, subject_id: sid, pir_id: dpForm.pir_id || undefined, latest_time: dpForm.latest_time ? new Date(dpForm.latest_time).toISOString() : undefined }).then(() => setDpForm(null)))}>WRITE</button><button className="mini" onClick={() => setDpForm(null)}>CANCEL</button></div>
    </div>}
    {dsm && dsm.rows.length > 0 && <div className="dsm">
      <div className="dsm-row dsm-head"><span>DP</span><span>DECISION · TRIGGER</span><span>PIR · NAI · COA</span><span>NLT</span><span /></div>
      {dsm.rows.map(r => <div key={r.id} data-dp={r.id} className={`dsm-row ${r.status} ${r.overdue ? 'overdue' : ''}`} title={`${r.title}\n${r.decision}\nTrigger: ${r.trigger}\nAction: ${r.action}${r.note ? `\n${r.note}` : ''}`}>
        <span className="mono">{r.title.split(' — ')[0]}</span>
        <span><b>{r.decision || r.title}</b>{r.trigger ? <span className="dim"> · {r.trigger}</span> : null}</span>
        <span className="dim small">{r.pir ? <span title={r.pir.question}>{r.pir.id} {r.pir.status}</span> : '—'}{r.nais.length ? ` · ${r.nais.map(n => n.name).join(', ')}` : ''}{r.coas.length ? ` · ${r.coas.map(c => c.likelihood).join(', ')}` : ''}</span>
        <span className={`mono ${r.overdue ? 'bad' : 'dim'}`}>{r.latest_time ? hhmm(r.latest_time).slice(0, 12) : '—'}</span>
        <span className="row-btns">{r.status === 'open' && decider ? <>
          <button className="mini warn" disabled={!!busy} onClick={() => { const n = window.prompt('Triggered — what was seen?', ''); if (n?.trim()) act('triggering the decision point', () => api.updateDecisionPoint(r.id, { status: 'triggered', note: n.trim() })) }}>TRIGGERED</button>
          <button className="mini" disabled={!!busy} onClick={() => act('passing the decision point', () => api.updateDecisionPoint(r.id, { status: 'passed' }))}>PASSED</button>
        </> : <span className={`chip ${r.status === 'triggered' ? 'md' : 'draft'}`}>{r.status.toUpperCase()}</span>}</span>
      </div>)}
    </div>}

    <Question q="The staff products" count={`${heads.length} · ${heads.filter(h => h.status === 'approved' || h.status === 'released').length} approved`} />
    {staff && <div className="dform">
      <div className="dform-head">DRAFT FROM THE WALL <span className="dim">rule-drafted, cited by id; the analyst approves, the Battle Captain releases the annex</span></div>
      <select value={subject} onChange={e => setSubject(e.target.value)}>
        {ops.map(o => <option key={o.id} value={`operation:${o.id}`}>OP · {o.title} ({o.status})</option>)}
        {pirs.filter(p => p.subject_type && p.subject_id && ["location", "event", "person"].includes(p.subject_type)).map(p => <option key={p.id} value={`${p.subject_type}:${p.subject_id}`}>{(p.subject_type ?? "").toUpperCase()} · {p.subject_id} (PIR {p.id})</option>)}
      </select>
      <div className="row-btns">
        <button className="mini ok" disabled={!!busy || !sid} onClick={() => act('drafting the IPB', () => api.draftIpb(stype, sid).then(setOpen))}>DRAFT IPB</button>
        <button className="mini ok" disabled={!!busy || !sid} onClick={() => act('drafting the intelligence estimate', () => api.draftEstimate(stype, sid).then(setOpen))}>DRAFT ESTIMATE</button>
        <button className="mini ok" disabled={!!busy || stype !== 'operation'} title="Annex B (Intelligence) to the operation" onClick={() => act('drafting the annex', () => api.draftAnnex(sid).then(setOpen))}>DRAFT ANNEX B</button>
      </div>
    </div>}
    <ul className="list">
      {heads.slice(0, 8).map(h => <li key={h.id} className={`row ${open?.id === h.id ? 'active' : ''}`} onClick={() => open?.id === h.id ? setOpen(null) : api.getStaffProduct(h.id).then(setOpen)}>
        <span className="sev mono">{h.kind.toUpperCase()}</span>
        <span className="name">{h.title}</span>
        <span className={`chip ${h.status}`}>{h.status.toUpperCase()}</span>
        <span className="meta dim">{hhmm(h.drafted_at).slice(0, 12)}</span>
      </li>)}
    </ul>
    {open && <ProductView p={open} role={role} busy={busy} act={act} op={opFor(open)} onSelect={onSelect} onClose={() => setOpen(null)} isBC={isBC} staff={staff} />}
  </>
}

function ProductView({ p, role, busy, act, op, onSelect, onClose, isBC, staff }: { p: StaffProduct; role: Role; busy: string | null; act: Act; op?: Operation; onSelect: (s: Selection) => void; onClose: () => void; isBC: boolean; staff: boolean }) {
  const d = p.product as Record<string, any>
  const done = p.status === 'approved' || p.status === 'released'
  const next = p.kind === 'annex' ? (p.status === 'draft' ? 'review' : 'released') : (p.status === 'draft' ? 'review' : 'approved')
  const canNext = p.status !== 'released' && p.status !== 'approved' && (next === 'released' ? isBC : staff) && (p.blockers?.length ?? 0) === 0
  const Sec = ({ n, t, children }: { n: string; t: string; children: React.ReactNode }) => <><div className="section-label">{n} · {t}</div>{children}</>
  return <div className="dform product">
    <div className="dform-head">{p.kind.toUpperCase()} · {p.subject_name}{op ? ` · ${op.title}` : ''} <span className={`chip ${p.status}`}>{p.status.toUpperCase()}</span>
      <button className="mini" style={{ marginLeft: 'auto' }} onClick={onClose}>CLOSE</button></div>
    <div className="dim small">{p.drafted_by} · {hhmm(p.drafted_at)}{p.decided_by ? ` · ${p.status} by ${p.decided_by} ${hhmm(p.decided_at)}` : ''}</div>
    {(p.blockers?.length ?? 0) > 0 && <div className="gapword">BLOCKED: {p.blockers!.join('; ')}</div>}
    {p.kind === 'ipb' && <>
      <Sec n="1" t="THE AREA"><div className="small">{d.step1_area.nais.length} NAI{d.step1_area.nais.length === 1 ? '' : 's'} · {d.step1_area.sites.length} site{d.step1_area.sites.length === 1 ? '' : 's'} · {d.step1_area.events.length} event{d.step1_area.events.length === 1 ? '' : 's'} · {d.step1_area.radius_km} km
        {d.step1_area.sites.map((l: any) => <span key={l.id} className="chip btn small" onClick={() => onSelect({ type: 'location', id: l.id })}>{l.name}</span>)}</div></Sec>
      <Sec n="2" t="EFFECTS">{d.step2_effects.weather ? <div className="small">{d.step2_effects.weather.summary ?? `${d.step2_effects.weather.condition ?? ''} ${d.step2_effects.weather.flight_category ?? ''}`}</div> : null}
        <div className="small dim">{d.step2_effects.terrain.length} terrain graphic{d.step2_effects.terrain.length === 1 ? '' : 's'} · {d.step2_effects.movement_risks.length} route{d.step2_effects.movement_risks.length === 1 ? '' : 's'} at risk</div></Sec>
      <Sec n="3" t="THE THREAT"><ul className="small">{d.step3_threat.actors.map((a: any) => <li key={a.id}><b>{a.name}</b> · {a.sightings} sighting{a.sightings === 1 ? '' : 's'} / {d.step3_threat.days}d · {a.pattern}{a.assessed_intent ? <span className="dim"> · {a.assessed_intent}</span> : null}</li>)}
        {d.step3_threat.threat_graphics.map((g: any) => <li key={g.id} className="dim">{g.label}: {g.name} ({g.confidence})</li>)}</ul></Sec>
      <Sec n="4" t="COURSES OF ACTION"><ul className="small">{d.step4_coas.filter((c: any) => c.status !== 'rejected').map((c: any) => <li key={c.id}>{c.most_likely ? 'ML · ' : ''}{c.most_dangerous ? 'MD · ' : ''}<b>{c.title}</b> — {c.likelihood}</li>)}</ul>
        {d.event_template.length > 0 && <div className="small dim">Event template: {d.event_template.map((e: any) => `${short(e.coa_title)} @ ${e.nai_name}`).join(' · ')}</div>}</Sec>
      {d.gaps.length > 0 && <Sec n="—" t="GAPS"><ul className="small">{d.gaps.map((g: string, i: number) => <li key={i} className="gapword">{g}</li>)}</ul></Sec>}
    </>}
    {p.kind === 'estimate' && <>
      <Sec n="1" t="MISSION"><div className="small">{d.mission}</div></Sec>
      <Sec n="2" t="THREAT SITUATION"><div className="small">{d.threat_situation.actors.length} actor{d.threat_situation.actors.length === 1 ? '' : 's'} · {d.threat_situation.threat_graphics.length} threat graphic{d.threat_situation.threat_graphics.length === 1 ? '' : 's'} · reports {d.threat_situation.reports.open} open / {d.threat_situation.reports.corroborated} corroborated</div></Sec>
      <Sec n="3" t="COURSES OF ACTION"><ul className="small">{d.capabilities_coas.map((c: any) => <li key={c.id}>{c.most_likely ? 'ML · ' : ''}{c.most_dangerous ? 'MD · ' : ''}<b>{c.title}</b> — {c.likelihood}, {c.confidence}</li>)}</ul></Sec>
      <Sec n="4" t="CONCLUSIONS"><ul className="small">{d.conclusions.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul></Sec>
    </>}
    {p.kind === 'annex' && <>
      <Sec n="1" t="SITUATION"><ul className="small">{d.situation.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul>
        <div className="small dim">IPB {d.ipb ? `${d.ipb.id} (${d.ipb.status})` : '— none'} · estimate {d.estimate ? `${d.estimate.id} (${d.estimate.status})` : '— none'}</div></Sec>
      <Sec n="2" t="COURSES OF ACTION"><ul className="small">{d.coas.map((c: any) => <li key={c.id}>{c.most_likely ? 'ML · ' : ''}{c.most_dangerous ? 'MD · ' : ''}<b>{c.title}</b> — {c.likelihood}</li>)}</ul></Sec>
      <Sec n="3" t="DECISIONS"><ul className="small">{d.dsm.map((r: any) => <li key={r.id}><b>{r.title}</b> · {r.status}{r.latest_time ? ` · NLT ${hhmm(r.latest_time).slice(0, 12)}` : ''}</li>)}</ul></Sec>
      <Sec n="4" t="COLLECTION"><div className="small">{d.collection.nais.length} NAI{d.collection.nais.length === 1 ? '' : 's'} · PIRs {d.collection.pirs.map((x: any) => `${x.id} ${x.status}`).join(', ') || 'none'} · {d.warnings.length} warning{d.warnings.length === 1 ? '' : 's'}</div></Sec>
      {!d.releasable && <div className="gapword">NEEDS {d.missing.join(' AND ').toUpperCase()}</div>}
    </>}
    <div className="row-btns" style={{ marginTop: 6 }}>
      {canNext && <button className="mini ok" disabled={!!busy} onClick={() => act(`${next} ${p.kind}`, () => api.setStaffProductStatus(p.id, next as any))}>{next.toUpperCase()}</button>}
      {!done && p.status === 'review' && staff && <button className="mini" disabled={!!busy} onClick={() => act('back to draft', () => api.setStaffProductStatus(p.id, 'draft'))}>BACK TO DRAFT</button>}
    </div>
    {done && <DistributionBox ptype={p.kind} pid={p.id} role={role} busy={busy} act={act} releasable={true} />}
  </div>
}
