// §5.6a the rated area assessment: what S2 judges about a place, indicator by indicator — green, amber, red, each with
// one line that says why. No score (Decision I): the picture is the row of ratings and the worst of them. A site, a trip,
// and an event carry the strip for their place; the S2 panel lists every rated place and compares any two side by side.
import { useEffect, useState } from 'react'
import * as api from './api'
import { Question } from './Headline'
import type { AreaCompact, AreaRating, Location, Rating, Role, Selection } from './types'

type Act = (l: string, f: () => Promise<unknown>) => void
export type AreaMode = { kind: 'view'; id: string } | { kind: 'new'; location_id?: string; place?: string; lat?: number; lon?: number; from?: string } | { kind: 'compare'; ids: string[] }
const RATERS: Role[] = ['battle_captain', 'analyst']
const RATING_LABEL: Record<Rating, string> = { green: 'GREEN', amber: 'AMBER', red: 'RED', unknown: '—' }
const when = (iso: string | null | undefined) => iso ? iso.slice(0, 16).replace('T', ' ') + 'Z' : ''

/** The strip: one block per indicator in the configured order, the worst as a word, who said so and how long ago. */
export function AreaStrip({ a, onOpen, compact }: { a: AreaCompact | null | undefined; onOpen?: () => void; compact?: boolean }) {
  if (!a) return null
  return (
    <span className={`astrip ${onOpen ? 'jump' : ''}`} onClick={e => { if (onOpen) { e.stopPropagation(); onOpen() } }} title={`${a.place} · ${a.counts.red} red · ${a.counts.amber} amber · ${a.counts.green} green${a.worst_indicator ? ` · worst: ${a.worst_indicator}` : ''} · ${a.assessed_by} ${when(a.assessed_at)}`}>
      <span className="ablocks">{a.strip.map((r, i) => <i key={i} className={`ab ${r}`} />)}</span>
      <span className={`chip small ${a.worst}`}>{RATING_LABEL[a.worst]}</span>
      {!compact && <span className="dim small">{a.worst_indicator ?? 'not rated'} · {a.age_days < 1 ? 'today' : `${Math.round(a.age_days)}d ago`}{a.stale ? ' · STALE' : ''}</span>}
    </span>)
}

/** The S2 section: every rated place as a card, the worst first; ASSESS a new one; pick two to COMPARE. */
export function AreasSection({ areas, locations, role, onOpen, onSelect }: { areas: AreaRating[]; locations: Location[]; role: Role; onOpen: (m: AreaMode) => void; onSelect: (s: Selection) => void }) {
  const [picked, setPicked] = useState<string[]>([])
  const can = RATERS.includes(role)
  const pick = (id: string) => setPicked(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id].slice(-3))
  return (<>
    <Question q="What we know about places" count={`${areas.length} rated · ${areas.filter(a => a.worst === 'red').length} red`}>
      <span className="btns">
        {picked.length >= 2 && <button className="mini ok" onClick={() => { onOpen({ kind: 'compare', ids: picked }); setPicked([]) }}>COMPARE {picked.length}</button>}
        {can && <button className="mini" onClick={() => onOpen({ kind: 'new' })} title="Rate a place — a site on the wall, or anywhere">+ ASSESS</button>}
      </span>
    </Question>
    {areas.length === 0 && <div className="dim small" style={{ padding: '2px 14px 8px' }}>No place has been rated yet.</div>}
    <ul className="list">
      {areas.map(a => (
        <li key={a.id} className={`row area ${a.worst}`} onClick={() => onOpen({ kind: 'view', id: a.id })}>
          <div className="l1">
            <input type="checkbox" className="pick" checked={picked.includes(a.id)} onClick={e => e.stopPropagation()} onChange={() => pick(a.id)} title="compare side by side" />
            <span className="name">{a.place}</span>
            <span className={`chip small ${a.worst}`}>{RATING_LABEL[a.worst]}</span>
          </div>
          <div className="l2">
            <span className="ablocks">{a.ratings.map(r => <i key={r.indicator} className={`ab ${r.rating}`} title={`${r.label}: ${r.rating}${r.note ? ' — ' + r.note : ''}`} />)}</span>
            <span className="dim small">{a.worst_indicator ?? 'nothing rated'} · {a.assessed_by} · {a.age_days < 1 ? 'today' : `${Math.round(a.age_days)}d ago`}{a.stale ? ' · STALE' : ''}</span>
            {a.location_id && locations.some(l => l.id === a.location_id) && <button className="mini" onClick={e => { e.stopPropagation(); onSelect({ type: 'location', id: a.location_id! }) }} title="fly to the site">⌖</button>}
          </div>
        </li>))}
    </ul>
  </>)
}

interface Ind { id: string; label: string }
type Line = { indicator: string; rating: Rating; note: string }

/** Over the map: one assessment to read or write, or several side by side. */
export function AreaPanel({ mode, areas, locations, role, busy, act, onClose, onSelect }: { mode: AreaMode; areas: AreaRating[]; locations: Location[]; role: Role; busy: string | null; act: Act; onClose: () => void; onSelect: (s: Selection) => void }) {
  const [inds, setInds] = useState<Ind[]>([])
  const [editing, setEditing] = useState(mode.kind === 'new')
  const [place, setPlace] = useState(mode.kind === 'new' ? (mode.place ?? '') : '')
  const [locId, setLocId] = useState(mode.kind === 'new' ? (mode.location_id ?? '') : '')
  const [latlon, setLatlon] = useState(mode.kind === 'new' && mode.lat != null ? `${mode.lat}, ${mode.lon}` : '')
  const [summary, setSummary] = useState('')
  const [lines, setLines] = useState<Line[]>([])
  const [history, setHistory] = useState<AreaRating[]>([])
  const can = RATERS.includes(role)
  const current = mode.kind === 'view' ? areas.find(a => a.id === mode.id) : undefined
  useEffect(() => { api.areaIndicators().then(d => setInds(d.indicators)).catch(() => setInds([])) }, [])
  useEffect(() => { if (mode.kind === 'view') api.listAreaRatings(true).then(all => setHistory(all.filter(a => a.status === 'superseded' && (a.location_id && a.location_id === current?.location_id || a.place === current?.place)))).catch(() => {}) }, [mode, current?.location_id, current?.place])
  useEffect(() => {  // a new assessment starts from the last one for the place, so the analyst edits rather than retypes
    const base = mode.kind === 'new' ? areas.find(a => (mode.location_id && a.location_id === mode.location_id) || (mode.place && a.place === mode.place)) : current
    setLines(inds.map(i => { const r = base?.ratings.find(x => x.indicator === i.id); return { indicator: i.id, rating: r?.rating ?? 'unknown', note: r?.note ?? '' } }))
    if (base) { setSummary(base.summary); if (mode.kind === 'new') { setPlace(base.place); if (base.location_id) setLocId(base.location_id) } }
  }, [inds, mode, current, areas])
  const setLine = (id: string, patch: Partial<Line>) => setLines(ls => ls.map(l => l.indicator === id ? { ...l, ...patch } : l))
  const save = () => {
    const [lat, lon] = latlon.split(',').map(s => parseFloat(s.trim()))
    const body = { place: place || undefined, location_id: locId || undefined, lat: isNaN(lat) ? undefined : lat, lon: isNaN(lon) ? undefined : lon, summary, ratings: lines }
    act(`assessing ${place || locations.find(l => l.id === locId)?.name || 'a place'}`, async () => { await api.assessArea(body); onClose() })
  }
  if (mode.kind === 'compare') {
    const cols = mode.ids.map(id => areas.find(a => a.id === id)).filter(Boolean) as AreaRating[]
    return (
      <div className="detail arate compare" onClick={e => e.stopPropagation()}>
        <button className="close" onClick={onClose}>×</button>
        <div className="d-kicker">AREA ASSESSMENT · SIDE BY SIDE · no composite, the reader ranks</div>
        <div className="d-title">{cols.map(c => c.place).join(' vs ')}</div>
        <div className="matrix-wrap"><table className="matrix arate">
          <thead><tr><th className="ind">INDICATOR</th>{cols.map(c => <th key={c.id}>{c.place}<div className="dim small">{c.counts.red} red · {c.counts.amber} amber · {c.counts.green} green · {c.assessed_by}</div></th>)}</tr></thead>
          <tbody>{(cols[0]?.ratings ?? []).map((r0, i) => <tr key={r0.indicator}>
            <td className="ind">{r0.label}</td>
            {cols.map(c => { const r = c.ratings[i]; return <td key={c.id} className={`cell rt-${r?.rating ?? 'unknown'}`}><span className={`chip small ${r?.rating ?? 'unknown'}`}>{RATING_LABEL[r?.rating ?? 'unknown']}</span><div className="note">{r?.note}</div></td> })}
          </tr>)}</tbody>
        </table></div>
      </div>)
  }
  const a = current
  return (
    <div className={`detail arate ${a?.worst ?? ''}`} onClick={e => e.stopPropagation()}>
      <button className="close" onClick={onClose}>×</button>
      <div className="d-kicker">AREA ASSESSMENT · RATED BY S2{a && <> · <span className={`chip small ${a.worst}`}>{RATING_LABEL[a.worst]}</span> · {a.assessed_by} · {when(a.assessed_at)}{a.stale ? <span className="chip small amber"> STALE</span> : null}</>}</div>
      {editing ? <div className="arate-head">
        <select value={locId} onChange={e => { setLocId(e.target.value); const l = locations.find(x => x.id === e.target.value); if (l) { setPlace(l.name); setLatlon('') } }}>
          <option value="">— not a site on the wall —</option>{locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select>
        {!locId && <input placeholder="Place (e.g. Lisbon, Portugal)" value={place} onChange={e => setPlace(e.target.value)} />}
        {!locId && <input placeholder="lat, lon (optional)" value={latlon} onChange={e => setLatlon(e.target.value)} />}
      </div> : <div className="d-title">{a?.place}{a?.location_id && locations.some(l => l.id === a.location_id) && <button className="mini" style={{ marginLeft: 10 }} onClick={() => onSelect({ type: 'location', id: a.location_id! })}>⌖ SITE</button>}</div>}
      {editing ? <textarea className="arate-summary" placeholder="One paragraph, if it needs one: what this place is, and what is open." value={summary} onChange={e => setSummary(e.target.value)} rows={2} />
        : a?.summary && <div className="bluf">{a.summary}</div>}
      <ul className="arows">
        {(editing ? lines : (a?.ratings ?? [])).map(l => { const label = inds.find(i => i.id === l.indicator)?.label ?? ('label' in l ? (l as { label: string }).label : l.indicator); return (
          <li key={l.indicator} className={`arow rt-${l.rating}`}>
            <span className="alabel">{label}</span>
            {editing ? <span className="rts">{(['green', 'amber', 'red', 'unknown'] as Rating[]).map(r => <button key={r} className={`rt ${r} ${l.rating === r ? 'on' : ''}`} onClick={() => setLine(l.indicator, { rating: r })} title={RATING_LABEL[r]}>{r === 'unknown' ? '?' : r[0].toUpperCase()}</button>)}</span>
              : <span className={`chip small ${l.rating}`}>{RATING_LABEL[l.rating]}</span>}
            {editing ? <input className="anote" placeholder="why — one line" value={l.note} onChange={e => setLine(l.indicator, { note: e.target.value })} /> : <span className="anote">{l.note || <span className="dim">no justification recorded</span>}</span>}
          </li>) })}
      </ul>
      <div className="row-btns" style={{ marginTop: 10 }}>
        {editing && <><button className="mini ok" disabled={!!busy || (!place && !locId) || lines.every(l => l.rating === 'unknown')} onClick={save}>{a ? 'SAVE AS NEW VERSION' : 'SAVE'}</button><button className="mini" onClick={() => a ? setEditing(false) : onClose()}>CANCEL</button></>}
        {!editing && can && a && <button className="mini" onClick={() => setEditing(true)} title="Rate the place again; the current assessment is kept as history">REASSESS</button>}
        {!editing && a?.supersedes && <span className="dim small">supersedes {a.supersedes}{history.length ? ` · ${history.length} earlier version${history.length === 1 ? '' : 's'}` : ''}</span>}
      </div>
      {!editing && history.length > 0 && <><div className="section-label">HISTORY</div>{history.slice(0, 5).map(h => <div key={h.id} className="pline"><span className={`chip small ${h.worst}`}>{RATING_LABEL[h.worst]}</span><span className="lbl">{h.assessed_by} · {when(h.assessed_at)}</span><span className="src dim">{h.counts.red} red · {h.counts.amber} amber</span></div>)}</>}
    </div>)
}
