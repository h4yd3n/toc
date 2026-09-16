import { useEffect, useState } from 'react'
import * as api from './api'
import { Question } from './Headline'
import type { IsrSync as IsrSyncView, IsrNai, Patterns, TimeWheel, Selection } from './types'

/** §5.10b Phase 2 — the ISR synchronization view and the pattern of life, under the S2 panel.
 *  Counts, never scores: a cell is what came back that day, a gap is an NAI-day nobody is watching. */
export function IsrPanel({ reload, busy, onTask, onSelect }: { reload: number; busy: string | null; onTask: (n: IsrNai) => void; onSelect: (s: Selection) => void }) {
  const [mode, setMode] = useState<'sync' | 'patterns'>('sync')
  const [sync, setSync] = useState<IsrSyncView | null>(null)
  const [pat, setPat] = useState<Patterns | null>(null)
  const [open, setOpen] = useState<string | null>(null)
  useEffect(() => { api.getIsrSync(7, 3).then(setSync).catch(() => setSync(null)); api.getPatterns(30).then(setPat).catch(() => setPat(null)) }, [reload])
  const select = (n: { subject_type: string; subject_id: string | null }) => {
    if (n.subject_type === 'location' && n.subject_id) onSelect({ type: 'location', id: n.subject_id })
    else if (n.subject_type === 'event' && n.subject_id) onSelect({ type: 'event', id: n.subject_id })
    else if (n.subject_type === 'person' && n.subject_id) onSelect({ type: 'person', id: n.subject_id })
  }
  return <>
    <Question q={mode === 'sync' ? 'Who is watching what' : 'Pattern of life'} count={mode === 'sync' ? (sync ? `${sync.gaps.length} gap-day${sync.gaps.length === 1 ? '' : 's'} · ${sync.taskings_open} tasked` : '…') : (pat ? `${pat.actors.length} actors · ${pat.nais.length} NAIs` : '…')}>
      <button className={`mini ${mode === 'sync' ? 'ok' : ''}`} onClick={() => setMode('sync')} title="ISR synchronization: NAIs by day">SYNC</button>
      <button className={`mini ${mode === 'patterns' ? 'ok' : ''}`} onClick={() => setMode('patterns')} title="Time wheels from sightings and reports">PATTERNS</button>
    </Question>
    {mode === 'sync' && sync && <div className="isr">
      <div className="isr-row isr-head"><span className="isr-nai">NAI</span>{sync.days.map(d => <span key={d} className={`isr-day ${d === sync.today ? 'today' : ''}`} title={d}>{d.slice(8)}</span>)}</div>
      {sync.nais.map(n => <div key={n.id} className={`isr-nai-block ${open === n.id ? 'open' : ''}`}>
        <div className="isr-row" onClick={() => setOpen(open === n.id ? null : n.id)} title={`${n.name} · P${n.priority} · ${n.subject_name}\n${n.question}\n${n.sources.length} source${n.sources.length === 1 ? '' : 's'} watching · ${n.taskings.length} tasking${n.taskings.length === 1 ? '' : 's'} · ${n.gap_days} gap-day${n.gap_days === 1 ? '' : 's'}`}>
          <span className={`isr-nai ${n.health}`}><b>{n.nai}</b> {n.subject_name.split(' — ')[0].split(' · ')[0]}</span>
          {n.cells.map(c => <span key={c.date} className={`isr-cell ${c.covered ? 'cov' : 'gap'} ${c.future ? 'future' : ''} ${c.tasked.length ? 'tasked' : ''} ${c.date === sync.today ? 'today' : ''}`}
            title={`${c.date}${c.tasked.length ? ` · ${c.tasked.length} tasked` : ''}${c.future ? '' : ` · ${c.sightings} sighting${c.sightings === 1 ? '' : 's'} · ${c.reports} report${c.reports === 1 ? '' : 's'}`}${c.covered ? '' : ' · GAP'}`}>
            {c.future ? (c.tasked.length ? '▣' : '') : (c.sightings + c.reports > 0 ? c.sightings + c.reports : (c.covered ? '·' : '×'))}</span>)}
        </div>
        {open === n.id && <div className="isr-detail">
          <div className="dim small">{n.question}</div>
          <div className="small">{n.sources.length ? n.sources.map(s => <span key={s.id} className="chip" title={s.indicators.join(', ')}>{s.name} · {s.cadence}</span>) : <span className="gapword">NO SOURCE WATCHING</span>}</div>
          {n.taskings.map(t => <div key={t.id} className="small"><span className="dim mono">◎ {t.status.toUpperCase()}</span> {t.title}{t.asset ? <span className="dim"> · {t.asset}</span> : null}{t.window_from ? <span className="dim"> · {t.window_from.slice(0, 10)}{t.window_to ? ` → ${t.window_to.slice(0, 10)}` : ''}</span> : null}</div>)}
          <div className="row-btns">
            <button className="mini ok" disabled={!!busy} onClick={() => onTask(n)} title="Raise a collection tasking on S3 for this NAI">TASK COLLECTION</button>
            {n.subject_id && <button className="mini" onClick={() => select(n)}>ON THE MAP</button>}
            {n.pir_ids.length > 0 && <span className="dim small">{n.pir_ids.join(', ')}</span>}
          </div>
        </div>}
      </div>)}
      {sync.nais.length === 0 && <div className="dim small" style={{ padding: '2px 14px 8px' }}>No active requirements, so no NAIs.</div>}
    </div>}
    {mode === 'patterns' && pat && <div className="isr">
      {pat.since_intsum && <div className="dim small" style={{ padding: '0 14px 6px' }}>Since the last INTSUM ({pat.since_intsum.period_to?.slice(0, 16)}Z): {pat.since_intsum.sightings} sighting{pat.since_intsum.sightings === 1 ? '' : 's'}, {pat.since_intsum.reports} report{pat.since_intsum.reports === 1 ? '' : 's'}{pat.since_intsum.new_actors.length ? `, ${pat.since_intsum.new_actors.length} new actor${pat.since_intsum.new_actors.length === 1 ? '' : 's'}` : ''}.</div>}
      {pat.actors.filter(a => a.sightings_total > 0).map(a => <div key={a.id} className="pol">
        <div className="pol-head"><span className="id">{a.kind.toUpperCase()}</span><span className="name">{a.name}</span><span className="meta dim">{a.sightings_7d} / 7d · {a[`sightings_${pat.days}d` as 'sightings_7d']} / {pat.days}d{a.since_intsum != null ? ` · +${a.since_intsum} since INTSUM` : ''}</span></div>
        <Wheel w={a.wheel} />
        <div className="dim small">{a.wheel.pattern}{a.nais.length ? ` · ${a.nais.map(n => `${n.name} ×${n.sightings}`).join(', ')}` : ''}</div>
      </div>)}
      {pat.nais.filter(n => n.sightings + n.reports > 0).map(n => <div key={n.id} className="pol">
        <div className="pol-head"><span className="id">{n.name}</span><span className="name">{n.subject_name}</span><span className="meta dim">{n.activity_7d} / 7d · {n[`activity_${pat.days}d` as 'activity_7d']} / {pat.days}d</span></div>
        <Wheel w={n.wheel} />
        <div className="dim small">{n.wheel.pattern}{n.actors.length ? ` · ${n.actors.map(a => `${a.name} ×${a.sightings}`).join(', ')}` : ''}</div>
      </div>)}
      {pat.actors.every(a => a.sightings_total === 0) && pat.nais.every(n => n.sightings + n.reports === 0) && <div className="dim small" style={{ padding: '2px 14px 8px' }}>Nothing sighted or reported in the window.</div>}
    </div>}
  </>
}

/** 7 × 24: rows are days, columns are hours UTC; a cell darkens with the count. */
function Wheel({ w }: { w: TimeWheel }) {
  const max = Math.max(1, ...w.grid.flat())
  return <div className="wheel" title="rows Mon–Sun, columns 00–23 UTC">
    {w.grid.map((row, d) => <div key={d} className="wheel-row"><span className="wheel-day">{w.days[d]}</span>{row.map((v, h) => <span key={h} className="wheel-cell" style={{ opacity: v ? 0.25 + 0.75 * (v / max) : 0.06 }} title={`${w.days[d]} ${String(h).padStart(2, '0')}:00Z · ${v}`} />)}</div>)}
  </div>
}
