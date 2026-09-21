// §5.6b the subject of concern: the file the desk keeps on a *person* directed at us, rated the way §5.6a rates a
// place — a fixed indicator list, green / amber / red, each with one line that says why. No score (Decision I): the
// picture is the row of ratings and the worst of them, and the reader ranks. Beside it, the MAILROOM: what arrived
// naming one of ours, graded when it landed, filed onto a subject or left in the inbox. Nothing is guessed onto a
// folder. The whole panel is restricted — it names private individuals against whom nothing has been proven.
import { useEffect, useState } from 'react'
import * as api from './api'
import { Question } from './Headline'
import type { Contact, Directness, Location, Person, Rating, Role, Selection, Subject, SubjectCompact, SubjectStatus } from './types'

type Act = (l: string, f: () => Promise<unknown>) => void
export type SubjectMode = { kind: 'view'; id: string } | { kind: 'new'; principal_id?: string; location_id?: string; name?: string } | { kind: 'inbox' }
const READERS: Role[] = ['battle_captain', 'ep', 'analyst']
const OWNERS: Role[] = ['battle_captain', 'ep', 'analyst']
const ASSESSORS: Role[] = ['battle_captain', 'analyst']
const RATING_LABEL: Record<Rating, string> = { green: 'GREEN', amber: 'AMBER', red: 'RED', unknown: '—' }
const STATUS_LABEL: Record<SubjectStatus, string> = { open: 'OPEN', monitoring: 'MONITORING', referred: 'REFERRED', closed: 'CLOSED' }
// How the threat is expressed, if it is expressed at all. It is the *wording*, never our view of the risk.
const DIRECT_LABEL: Record<Directness, string> = { directed: 'DIRECTED', conditional: 'CONDITIONAL', veiled: 'VEILED', none: 'NO THREAT' }
const CHANNELS = ['email', 'dm', 'letter', 'phone', 'form', 'in_person', 'other'] as const
const when = (iso: string | null | undefined) => iso ? iso.slice(0, 16).replace('T', ' ') + 'Z' : ''
const ago = (d: number | null | undefined) => d == null ? '' : d < 1 ? 'today' : `${Math.round(d)}d ago`

export const canReadSubjects = (role: Role) => READERS.includes(role)

/** The strip on a principal or a site: the file's name, its row of ratings, and the worst of them as a word. */
export function SubjectStrip({ s, onOpen }: { s: SubjectCompact; onOpen?: () => void }) {
  return (
    <span className={`astrip subj ${onOpen ? 'jump' : ''}`} onClick={e => { if (onOpen) { e.stopPropagation(); onOpen() } }}
          title={`${s.name} · ${s.counts.red} red · ${s.counts.amber} amber · ${s.counts.green} green${s.worst_indicator ? ` · worst: ${s.worst_indicator}` : ''}${s.unassessed ? ' · never assessed' : ''}`}>
      <span className="name">{s.name}</span>
      <span className="ablocks">{s.strip.map((r, i) => <i key={i} className={`ab ${r}`} />)}</span>
      {s.unassessed ? <span className="chip small amber">UNASSESSED</span> : <span className={`chip small ${s.worst}`}>{RATING_LABEL[s.worst]}</span>}
      {s.contact_count > 0 && <span className="dim small">{s.contact_count} contact{s.contact_count === 1 ? '' : 's'}{s.new_contacts ? ` · ${s.new_contacts} new` : ''}</span>}
      {s.stale && <span className="chip small amber">STALE</span>}
    </span>)
}

/** The S2 rail section: every open file, worst first, plus the inbox of what nobody has attributed yet.
 *  It fetches its own data rather than reading the snapshot, because the snapshot only carries subjects for a
 *  caller who asked for the restricted layer — and a clearance is not a map layer the operator toggled. */
export function SubjectsSection({ role, reload, onOpen }: { role: Role; reload: number; onOpen: (m: SubjectMode) => void }) {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [inbox, setInbox] = useState<Contact[]>([])
  const [denied, setDenied] = useState(!READERS.includes(role))
  useEffect(() => {
    if (!READERS.includes(role)) { setDenied(true); setSubjects([]); setInbox([]); return }
    setDenied(false)
    api.listSubjects().then(setSubjects).catch(() => { setDenied(true); setSubjects([]) })
    api.listContacts({ inbox: true }).then(setInbox).catch(() => setInbox([]))
  }, [role, reload])
  const can = OWNERS.includes(role)
  const live = subjects.filter(s => s.status === 'open' || s.status === 'monitoring')
  const rest = subjects.filter(s => s.status === 'referred' || s.status === 'closed')
  if (denied) return (<>
    <Question q="Who is directed at us" count="restricted" />
    <div className="dim small" style={{ padding: '2px 14px 8px' }}>
      Subject files name private individuals. Battle Captain, Executive Protection or the S2 analyst only.
    </div>
  </>)
  return (<>
    <Question q="Who is directed at us" count={`${live.length} open · ${live.filter(s => s.worst === 'red').length} red`}>
      <span className="btns">
        {inbox.length > 0 && <button className="mini warn" onClick={() => onOpen({ kind: 'inbox' })} title="What arrived and has been attributed to nobody">INBOX {inbox.length}</button>}
        {can && <button className="mini" onClick={() => onOpen({ kind: 'new' })} title="Open a file on a person">+ OPEN FILE</button>}
      </span>
    </Question>
    {live.length === 0 && <div className="dim small" style={{ padding: '2px 14px 8px' }}>No file is open on anyone.</div>}
    <ul className="list">
      {[...live, ...rest].map(s => (
        <li key={s.id} className={`row area subj ${s.status === 'closed' || s.status === 'referred' ? 'done' : s.worst}`} onClick={() => onOpen({ kind: 'view', id: s.id })}>
          <div className="l1">
            <span className="name">{s.name}</span>
            {s.unassessed ? <span className="chip small amber">UNASSESSED</span> : <span className={`chip small ${s.worst}`}>{RATING_LABEL[s.worst]}</span>}
            {s.status !== 'open' && <span className={`chip small ${s.status}`}>{STATUS_LABEL[s.status]}</span>}
          </div>
          <div className="l2">
            <span className="ablocks">{(s.assessment?.ratings ?? []).map(r => <i key={r.indicator} className={`ab ${r.rating}`} title={`${r.label}: ${r.rating}${r.note ? ' — ' + r.note : ''}`} />)}</span>
            <span className="dim small">
              {s.principal_name ? `directed at ${s.principal_name}` : s.worst_indicator ?? 'nothing rated'}
              {s.contact_count > 0 && ` · ${s.contact_count} contact${s.contact_count === 1 ? '' : 's'}`}
              {s.worst_directness !== 'none' && ` · ${DIRECT_LABEL[s.worst_directness].toLowerCase()}`}
              {s.assessed_at ? ` · ${ago(s.age_days)}` : ' · never assessed'}{s.stale ? ' · STALE' : ''}
            </span>
          </div>
        </li>))}
    </ul>
  </>)
}

interface Ind { id: string; label: string }
type Line = { indicator: string; rating: Rating; note: string }

/** Over the map: one file to read or write, or the inbox to work. */
export function SubjectPanel({ mode, people, locations, role, busy, act, onClose, onSelect, onChanged }: {
  mode: SubjectMode; people: Person[]; locations: Location[]; role: Role; busy: string | null; act: Act
  onClose: () => void; onSelect: (s: Selection) => void; onChanged: () => void }) {
  const [inds, setInds] = useState<Ind[]>([])
  const [subject, setSubject] = useState<Subject | null>(null)
  const [inbox, setInbox] = useState<Contact[]>([])
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [editing, setEditing] = useState(mode.kind === 'new')
  const [name, setName] = useState(mode.kind === 'new' ? (mode.name ?? '') : '')
  const [principal, setPrincipal] = useState(mode.kind === 'new' ? (mode.principal_id ?? '') : '')
  const [locId, setLocId] = useState(mode.kind === 'new' ? (mode.location_id ?? '') : '')
  const [summary, setSummary] = useState('')
  const [lines, setLines] = useState<Line[]>([])
  const [rating, setRating] = useState(false)   // the assessment editor, separate from the file's own fields
  const canOwn = OWNERS.includes(role), canRate = ASSESSORS.includes(role)

  useEffect(() => { api.subjectIndicators().then(d => setInds(d.indicators)).catch(() => setInds([])) }, [])
  useEffect(() => {
    if (mode.kind === 'view') api.getSubject(mode.id).then(s => { setSubject(s); setSummary(s.summary); setName(s.name); setPrincipal(s.principal_id ?? ''); setLocId(s.location_id ?? '') }).catch(() => setSubject(null))
    if (mode.kind === 'inbox') { api.listContacts({ inbox: true }).then(setInbox).catch(() => setInbox([])); api.listSubjects().then(setSubjects).catch(() => setSubjects([])) }
  }, [mode])
  useEffect(() => {  // a reassessment starts from the current one, so the analyst edits rather than retypes
    const base = subject?.assessment
    setLines(inds.map(i => { const r = base?.ratings.find(x => x.indicator === i.id); return { indicator: i.id, rating: r?.rating ?? 'unknown', note: r?.note ?? '' } }))
  }, [inds, subject])
  const setLine = (id: string, patch: Partial<Line>) => setLines(ls => ls.map(l => l.indicator === id ? { ...l, ...patch } : l))
  const reload = () => { if (subject) api.getSubject(subject.id).then(setSubject).catch(() => {}); onChanged() }

  // ---------------------------------------------------------------- the inbox
  if (mode.kind === 'inbox') {
    return (
      <div className="detail arate subjects-inbox" onClick={e => e.stopPropagation()}>
        <button className="close" onClick={onClose}>×</button>
        <div className="d-kicker">MAILROOM · UNATTRIBUTED · graded on arrival, attributed by hand</div>
        <div className="d-title">What arrived, and to whose file it belongs</div>
        <div className="bluf">Nothing here has been attributed to anyone. A message that reads like a subject we hold is still not that subject until an analyst says so.</div>
        {inbox.length === 0 && <div className="dim small">The inbox is empty.</div>}
        <ul className="list cards">
          {inbox.map(c => (
            <li key={c.id} className="card contact">
              <div className="card-head">
                <span className="id">{c.channel.toUpperCase().replace('_', ' ')}</span>
                <span className="name">{c.from_label || 'sender not given'}</span>
                <span className={`chip small d-${c.directness}`}>{DIRECT_LABEL[c.directness]}</span>
                <span className="chip small dim">{c.reliability}/{c.credibility}</span>
              </div>
              <div className="q">{c.text}</div>
              <div className="dim small">
                {when(c.received_at)} · received by {c.received_by || 'unrecorded'}
                {c.principal_name ? ` · names ${c.principal_name}` : ' · names nobody we hold'}
              </div>
              {canOwn && <div className="row-btns">
                <select defaultValue="" onChange={e => { const v = e.target.value; if (v) act(`attributing the ${c.channel}`, async () => { await api.triageContact(c.id, { subject_id: v }); setInbox(await api.listContacts({ inbox: true })); onChanged() }) }}>
                  <option value="">— attribute to a file —</option>
                  {subjects.filter(s => s.status === 'open' || s.status === 'monitoring').map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
                <button className="mini" disabled={!!busy} onClick={() => { const note = prompt('Dismissing needs a line saying why:'); if (note) act('dismissing the contact', async () => { await api.triageContact(c.id, { triage: 'dismissed', note }); setInbox(await api.listContacts({ inbox: true })); onChanged() }) }}>DISMISS</button>
              </div>}
            </li>))}
        </ul>
      </div>)
  }

  // ---------------------------------------------------------------- open a new file
  if (mode.kind === 'new') {
    const save = () => act(`opening a file on ${name || 'a person'}`, async () => {
      await api.openSubject({ name, summary, principal_id: principal || undefined, location_id: locId || undefined })
      onChanged(); onClose()
    })
    return (
      <div className="detail arate" onClick={e => e.stopPropagation()}>
        <button className="close" onClick={onClose}>×</button>
        <div className="d-kicker">SUBJECT OF CONCERN · NEW FILE · restricted</div>
        <div className="arate-head">
          <input placeholder="Name, or what we call him until we have one" value={name} onChange={e => setName(e.target.value)} />
          <select value={principal} onChange={e => setPrincipal(e.target.value)}>
            <option value="">— not directed at one person —</option>
            {people.filter(p => p.is_vip).map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select value={locId} onChange={e => setLocId(e.target.value)}>
            <option value="">— no site —</option>{locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
        </div>
        <textarea className="arate-summary" placeholder="What brought this to us, in the words of whoever reported it." value={summary} onChange={e => setSummary(e.target.value)} rows={3} />
        <div className="dim small">A file opens unassessed, and reads as unassessed until someone rates it. It never reads as green by default.</div>
        <div className="row-btns" style={{ marginTop: 10 }}>
          <button className="mini ok" disabled={!!busy || !name.trim()} onClick={save}>OPEN FILE</button>
          <button className="mini" onClick={onClose}>CANCEL</button>
        </div>
      </div>)
  }

  // ---------------------------------------------------------------- one file
  const s = subject
  if (!s) return (<div className="detail arate" onClick={e => e.stopPropagation()}><button className="close" onClick={onClose}>×</button><div className="dim small">Loading, or you are not cleared for this file.</div></div>)
  const saveAssessment = () => act(`assessing ${s.name}`, async () => { await api.assessSubject(s.id, { summary, ratings: lines }); setRating(false); reload() })
  const saveFile = () => act(`amending ${s.name}`, async () => {
    await api.updateSubject(s.id, { name, summary, principal_id: principal || undefined, location_id: locId || undefined })
    setEditing(false); reload()
  })
  const setStatus = (status: SubjectStatus) => {
    if (status === 'closed') { const closed_reason = prompt('Closing needs a reason — what changed, or what it turned out to be:'); if (!closed_reason) return; act(`closing ${s.name}`, async () => { await api.updateSubject(s.id, { status, closed_reason }); reload() }); return }
    if (status === 'referred') { const referred_to = prompt('Referring needs a name — who it was handed to:'); if (!referred_to) return; act(`referring ${s.name}`, async () => { await api.updateSubject(s.id, { status, referred_to }); reload() }); return }
    act(`moving ${s.name} to ${status}`, async () => { await api.updateSubject(s.id, { status }); reload() })
  }
  return (
    <div className={`detail arate subj ${s.worst}`} onClick={e => e.stopPropagation()}>
      <button className="close" onClick={onClose}>×</button>
      <div className="d-kicker">
        SUBJECT OF CONCERN · RESTRICTED · <span className={`chip small ${s.status}`}>{STATUS_LABEL[s.status]}</span>
        {s.unassessed ? <> · <span className="chip small amber">NEVER ASSESSED</span></> : <> · <span className={`chip small ${s.worst}`}>{RATING_LABEL[s.worst]}</span> · {s.assessment?.assessed_by} · {when(s.assessed_at)}{s.stale ? <span className="chip small amber"> STALE</span> : null}</>}
      </div>
      {editing ? <div className="arate-head">
        <input value={name} onChange={e => setName(e.target.value)} />
        <select value={principal} onChange={e => setPrincipal(e.target.value)}>
          <option value="">— not directed at one person —</option>
          {people.filter(p => p.is_vip).map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select value={locId} onChange={e => setLocId(e.target.value)}>
          <option value="">— no site —</option>{locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
      </div> : <div className="d-title">
        {s.name}
        {s.principal_id && <button className="mini" style={{ marginLeft: 10 }} onClick={() => onSelect({ type: 'person', id: s.principal_id! })}>⌖ {s.principal_name}</button>}
        {s.location_id && locations.some(l => l.id === s.location_id) && <button className="mini" style={{ marginLeft: 6 }} onClick={() => onSelect({ type: 'location', id: s.location_id! })}>⌖ SITE</button>}
      </div>}
      {s.aliases.length > 0 && !editing && <div className="dim small">also: {s.aliases.join(' · ')}</div>}
      {editing ? <textarea className="arate-summary" value={summary} onChange={e => setSummary(e.target.value)} rows={3} /> : s.summary && <div className="bluf">{s.summary}</div>}
      {s.status === 'referred' && s.referred_to && <div className="est"><b>REFERRED</b> · {s.referred_to} · {when(s.referred_at)}</div>}
      {s.status === 'closed' && s.closed_reason && <div className="est"><b>CLOSED</b> · {s.closed_reason}</div>}

      <div className="section-label">THE ASSESSMENT{s.unassessed ? ' — none yet' : ''}</div>
      {s.unassessed && !rating && <div className="dim small">Nobody has rated this person. That is an exception in its own right; it is not a green file.</div>}
      {(!s.unassessed || rating) && <ul className="arows">
        {(rating ? lines : (s.assessment?.ratings ?? [])).map(l => {
          const label = inds.find(i => i.id === l.indicator)?.label ?? ('label' in l ? (l as { label: string }).label : l.indicator)
          return (
            <li key={l.indicator} className={`arow rt-${l.rating}`}>
              <span className="alabel">{label}</span>
              {rating ? <span className="rts">{(['green', 'amber', 'red', 'unknown'] as Rating[]).map(r => <button key={r} className={`rt ${r} ${l.rating === r ? 'on' : ''}`} onClick={() => setLine(l.indicator, { rating: r })} title={RATING_LABEL[r]}>{r === 'unknown' ? '?' : r[0].toUpperCase()}</button>)}</span>
                : <span className={`chip small ${l.rating}`}>{RATING_LABEL[l.rating]}</span>}
              {rating ? <input className="anote" placeholder="why — one line" value={l.note} onChange={e => setLine(l.indicator, { note: e.target.value })} />
                : <span className="anote">{l.note || <span className="dim">no justification recorded</span>}</span>}
            </li>)
        })}
      </ul>}
      {!rating && s.assessment?.summary && <div className="bluf">{s.assessment.summary}</div>}

      <div className="row-btns" style={{ marginTop: 10 }}>
        {rating && <><button className="mini ok" disabled={!!busy || lines.every(l => l.rating === 'unknown')} onClick={saveAssessment}>{s.unassessed ? 'SAVE ASSESSMENT' : 'SAVE AS NEW VERSION'}</button><button className="mini" onClick={() => setRating(false)}>CANCEL</button></>}
        {editing && <><button className="mini ok" disabled={!!busy || !name.trim()} onClick={saveFile}>SAVE FILE</button><button className="mini" onClick={() => setEditing(false)}>CANCEL</button></>}
        {!rating && !editing && canRate && <button className="mini" onClick={() => setRating(true)} title="Rate the person again; the current assessment is kept as history">{s.unassessed ? 'ASSESS' : 'REASSESS'}</button>}
        {!rating && !editing && canOwn && <button className="mini" onClick={() => setEditing(true)}>EDIT FILE</button>}
        {!rating && !editing && canOwn && s.status === 'open' && <button className="mini" onClick={() => setStatus('monitoring')}>MONITOR</button>}
        {!rating && !editing && canOwn && s.status !== 'referred' && s.status !== 'closed' && <button className="mini warn" onClick={() => setStatus('referred')}>REFER</button>}
        {!rating && !editing && canOwn && s.status !== 'closed' && <button className="mini" onClick={() => setStatus('closed')}>CLOSE</button>}
      </div>

      <div className="section-label">WHAT HAS ARRIVED · {s.contact_count}</div>
      {s.contact_count === 0 && <div className="dim small">Nothing has been attributed to this file.</div>}
      <ul className="list cards">
        {s.contacts.map(c => (
          <li key={c.id} className="card contact">
            <div className="card-head">
              <span className="id">{c.channel.toUpperCase().replace('_', ' ')}</span>
              <span className="name">{c.from_label || 'sender not given'}</span>
              <span className={`chip small d-${c.directness}`}>{DIRECT_LABEL[c.directness]}</span>
              <span className="chip small dim">{c.reliability}/{c.credibility}</span>
            </div>
            <div className="q">{c.text}</div>
            <div className="dim small">{when(c.received_at)}{c.principal_name ? ` · names ${c.principal_name}` : ''}{c.note ? ` · ${c.note}` : ''}</div>
          </li>))}
      </ul>
      {canOwn && <AddContact subjectId={s.id} busy={busy} act={act} onDone={reload} />}

      {(s.history?.length ?? 0) > 0 && <><div className="section-label">HISTORY</div>
        {s.history!.slice(0, 5).map(h => (
          <div key={h.id} className="pline">
            <span className={`chip small ${h.worst}`}>{RATING_LABEL[h.worst]}</span>
            <span className="lbl">{h.assessed_by} · {when(h.assessed_at)}</span>
            <span className="src dim">{h.counts.red} red · {h.counts.amber} amber · {h.counts.unknown} unknown</span>
          </div>))}</>}
      <div className="dim small" style={{ marginTop: 8 }}>Opened by {s.opened_by} · {when(s.opened_at)}{s.case_id ? ` · case ${s.case_id}` : ''}</div>
    </div>)
}

/** File something that arrived straight onto this subject — the mailroom's other door. */
function AddContact({ subjectId, busy, act, onDone }: { subjectId: string; busy: string | null; act: Act; onDone: () => void }) {
  const [open, setOpen] = useState(false)
  const [channel, setChannel] = useState<string>('email')
  const [from, setFrom] = useState('')
  const [text, setText] = useState('')
  const [directness, setDirectness] = useState<Directness>('none')
  if (!open) return <button className="mini" onClick={() => setOpen(true)}>+ FILE A CONTACT</button>
  return (
    <div className="arate-head contact-form">
      <select value={channel} onChange={e => setChannel(e.target.value)}>{CHANNELS.map(c => <option key={c} value={c}>{c.replace('_', ' ')}</option>)}</select>
      <input placeholder="from — the address, handle or return address as it arrived" value={from} onChange={e => setFrom(e.target.value)} />
      <textarea placeholder="What it says, in the words it arrived in." value={text} onChange={e => setText(e.target.value)} rows={3} />
      <select value={directness} onChange={e => setDirectness(e.target.value as Directness)}>
        {(['none', 'veiled', 'conditional', 'directed'] as Directness[]).map(d => <option key={d} value={d}>{DIRECT_LABEL[d]}</option>)}
      </select>
      <div className="row-btns">
        <button className="mini ok" disabled={!!busy || !text.trim()} onClick={() => act('filing the contact', async () => {
          await api.fileContact({ subject_id: subjectId, channel, from_label: from, text, directness }); setOpen(false); setText(''); setFrom(''); onDone()
        })}>FILE</button>
        <button className="mini" onClick={() => setOpen(false)}>CANCEL</button>
      </div>
    </div>)
}
