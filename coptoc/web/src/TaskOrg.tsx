// §4 — the task organization: brigade → battalions → companies, with present/assigned and who is away. Collapsed by default;
// a battalion opens on click. Where the data has no hierarchy (a flat set of teams) the panel shows nothing and the team list stands.
import { useState } from 'react'
import type { Person, Selection, Team } from './types'

export function TaskOrg({ teams, people, onSelect, sel }: { teams: Team[]; people: Person[]; onSelect: (s: Selection) => void; sel: Selection }) {
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const roots = teams.filter(t => !t.parent_id && teams.some(c => c.parent_id === t.id))
  if (roots.length === 0) return null
  const kids = (id: string) => teams.filter(t => t.parent_id === id)
  const members = (id: string): Person[] => { const direct = people.filter(p => p.team_id === id); return direct.concat(...kids(id).map(k => members(k.id))) }
  const stat = (id: string) => { const m = members(id); const away = m.filter(p => p.status === 'traveling').length; const bad = m.filter(p => p.availability === 'unreachable' || p.confirmed_threat_ids.length > 0).length; return { total: m.length, present: m.length - away, away, bad } }
  const Row = ({ t, depth }: { t: Team; depth: number }) => {
    const s = stat(t.id); const ch = kids(t.id); const isOpen = open[t.id] ?? depth === 0
    return (<>
      <li className={`row org d${depth} ${sel?.type === 'location' && sel.id === t.location_id ? 'active' : ''}`} onClick={() => ch.length ? setOpen(o => ({ ...o, [t.id]: !isOpen })) : onSelect({ type: 'location', id: t.location_id })} title={t.name}>
        <span className="tw dim">{ch.length ? (isOpen ? '▾' : '▸') : ''}</span>
        <span className="short mono">{t.short ?? t.name}</span>
        <span className="name dim">{depth === 0 ? t.name : t.equipment ?? t.function}</span>
        {s.bad > 0 && <span className="tbadge confirmed">▲{s.bad}</span>}
        <span className="meta mono">{s.present}<span className="dim">/{s.total}</span>{s.away > 0 && <span className="away"> ·{s.away}↗</span>}</span>
      </li>
      {isOpen && ch.map(c => <Row key={c.id} t={c} depth={depth + 1} />)}
    </>)
  }
  return (<>
    <div className="section-label">TASK ORGANIZATION <span className="dim">present/assigned · ↗ away</span></div>
    <ul className="list taskorg">{roots.map(r => <Row key={r.id} t={r} depth={0} />)}</ul>
  </>)
}
