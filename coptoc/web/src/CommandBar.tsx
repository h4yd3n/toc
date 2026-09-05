// ⌘K — one field that finds anything on the picture: a name among 2,400, a site, an event, a threat, a tasking, and the
// wall's own actions. Everything is matched client-side against the snapshot the wall already holds. Enter selects it,
// which flies the map there and opens the section it lives in.
import { useEffect, useMemo, useRef, useState } from 'react'
import type { Selection, Snapshot } from './types'

export interface Command { id: string; kind: 'person' | 'location' | 'event' | 'threat' | 'tasking' | 'action'; title: string; sub: string; run: () => void }
type Hit = Command & { score: number }

const KIND_LABEL: Record<Command['kind'], string> = { person: 'PERSON', location: 'SITE', event: 'EVENT', threat: 'THREAT', tasking: 'TASKING', action: 'ACTION' }
const norm = (s: string) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')

/** Every token of the query must appear somewhere in the item; a hit at the start of a word scores higher than one inside it. */
function score(q: string[], hay: string): number {
  let s = 0
  for (const t of q) {
    const i = hay.indexOf(t); if (i < 0) return -1
    s += i === 0 || hay[i - 1] === ' ' ? 3 : 1
  }
  return s
}

export function buildCommands(snap: Snapshot, go: { select: (s: Selection) => void; open: (panel: 'S1' | 'S2' | 'S3' | 'S4' | 'S6' | 'brief' | 'settings' | 'plan' | 'intsum') => void }): Command[] {
  const out: Command[] = []
  for (const p of snap.people) out.push({ id: `p:${p.id}`, kind: 'person', title: p.name, sub: `${p.rank ? p.rank + ' · ' : ''}${p.role} · ${p.team_name}${p.status === 'traveling' ? ' · traveling' : ''}`, run: () => { go.select({ type: 'person', id: p.id }); go.open('S1') } })
  for (const l of snap.locations) out.push({ id: `l:${l.id}`, kind: 'location', title: l.name, sub: `${l.city}, ${l.country} · ${l.present}/${l.assigned} present · DEFCON ${l.defcon ?? ''}`.replace(' · DEFCON ', l.defcon ? ' · DEFCON ' : ''), run: () => { go.select({ type: 'location', id: l.id }); go.open('S1') } })
  for (const e of snap.events) out.push({ id: `e:${e.id}`, kind: 'event', title: e.name, sub: `${e.venue_name} · ${e.status === 'active' ? 'in progress' : `in ${e.days_until} d`}`, run: () => { go.select({ type: 'event', id: e.id }); go.open('S3') } })
  for (const t of snap.threats) out.push({ id: `t:${t.id}`, kind: 'threat', title: t.title, sub: `${t.severity} · ${t.source}`, run: () => { go.select({ type: 'threat', id: t.id }); go.open('S2') } })
  for (const t of snap.taskings?.items ?? []) if (t.open) out.push({ id: `k:${t.id}`, kind: 'tasking', title: t.title, sub: `${t.from_section} → ${t.to_section} · ${t.status}${t.overdue ? ' · LATE' : ''}`, run: () => go.open(t.to_section) })
  const acts: [string, string, () => void][] = [
    ['Open the shift change brief', 'the watch, handover, acknowledgement', () => go.open('brief')],
    ['Open S1 Personnel', 'accounted for, by unit, who is moving', () => go.open('S1')], ['Open S2 Intelligence', 'threats, warnings, requirements, assessments', () => go.open('S2')],
    ['Show S3 Operations', 'the strip: this watch and the horizon', () => go.open('S3')], ['Open S4 Logistics', 'supply and inbound, by exception', () => go.open('S4')],
    ['Open S6 Signal', 'PACE and systems, by exception', () => go.open('S6')], ['Plan the next 90 days', 'the month grid, coverage per event', () => go.open('plan')],
    ['Open the INTSUM', 'the daily diff', () => go.open('intsum')], ['Open settings', 'keys, sections, the area of operations', () => go.open('settings')],
  ]
  for (const [title, sub, run] of acts) out.push({ id: `a:${title}`, kind: 'action', title, sub, run })
  return out
}

export function CommandBar({ commands, onClose }: { commands: Command[]; onClose: () => void }) {
  const [q, setQ] = useState('')
  const [cursor, setCursor] = useState(0)
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => { input.current?.focus() }, [])
  const hits = useMemo<Hit[]>(() => {
    const toks = norm(q).split(/\s+/).filter(Boolean)
    if (toks.length === 0) return commands.filter(c => c.kind === 'action').map(c => ({ ...c, score: 0 }))
    const out: Hit[] = []
    for (const c of commands) { const s = score(toks, norm(`${c.title} ${c.sub}`)); if (s >= 0) out.push({ ...c, score: s + (c.kind === 'action' ? 0 : 0.5) }) }
    return out.sort((a, b) => b.score - a.score || a.title.localeCompare(b.title)).slice(0, 14)
  }, [q, commands])
  useEffect(() => setCursor(0), [q])
  const run = (h: Command | undefined) => { if (!h) return; h.run(); onClose() }
  return (
    <div className="cmdk-back" onClick={onClose}>
      <div className="cmdk" onClick={e => e.stopPropagation()}>
        <input ref={input} value={q} onChange={e => setQ(e.target.value)} placeholder="Find a name, a site, an event, a threat, a tasking — or an action"
          onKeyDown={e => { if (e.key === 'Escape') onClose(); else if (e.key === 'ArrowDown') { e.preventDefault(); setCursor(c => Math.min(hits.length - 1, c + 1)) } else if (e.key === 'ArrowUp') { e.preventDefault(); setCursor(c => Math.max(0, c - 1)) } else if (e.key === 'Enter') run(hits[cursor]) }} />
        <ul>
          {hits.map((h, i) => <li key={h.id} className={`${i === cursor ? 'on' : ''} k-${h.kind}`} onMouseEnter={() => setCursor(i)} onClick={() => run(h)}>
            <span className="kk">{KIND_LABEL[h.kind]}</span><span className="kt">{h.title}</span><span className="ks dim">{h.sub}</span></li>)}
          {hits.length === 0 && <li className="none dim">Nothing on the picture matches.</li>}
        </ul>
        <div className="cmdk-foot dim">↑↓ move · ⏎ open · esc close · {commands.length.toLocaleString()} things on the picture</div>
      </div>
    </div>)
}
