// §3.6 CCIR — the commander's critical information requirements, in one list: PIR (the enemy), FFIR (us), EEFI
// (what we must not reveal). A tripped line reports and does not act: it turns red here, writes a line on the watch,
// and suggests a warning the Battle Captain releases or dismisses. Writing a line is the Battle Captain's alone.
import { useEffect, useState } from 'react'
import * as api from './api'
import { Headline, Question } from './Headline'
import type { CcirBoard, CcirLine, CcirMetric } from './types'

const KIND_LABEL: Record<string, string> = { pir: 'PIR', ffir: 'FFIR', eefi: 'EEFI' }
const KIND_HINT: Record<string, string> = {
  pir: 'priority intelligence requirement — about the enemy or the environment',
  ffir: 'friendly force information requirement — about us',
  eefi: 'essential element of friendly information — what the other side must not learn',
}
const COMPARATOR_WORD: Record<string, string> = { lt: 'below', lte: 'at or below', gt: 'above', gte: 'at or above', eq: 'exactly' }

export function CcirPanel({ board, canEdit, busy, act, pirs }: {
  board: CcirBoard | undefined
  canEdit: boolean
  busy: string | null
  act: (label: string, f: () => Promise<unknown>) => void
  pirs: { id: string; question: string; status: string }[]
}) {
  const [write, setWrite] = useState(false)
  const [metrics, setMetrics] = useState<CcirMetric[]>([])
  const [f, setF] = useState({ kind: 'ffir' as CcirLine['kind'], text: '', metric: 'unaccounted', comparator: 'gte', threshold: '1', scope: '', priority: 2, pir_id: '', owner_section: '' })

  useEffect(() => { if (write && metrics.length === 0) api.ccirMetrics().then(r => setMetrics(r.metrics)).catch(() => undefined) }, [write, metrics.length])

  if (!board) return null
  const { lines, counts } = board
  const tripped = lines.filter(l => l.state === 'tripped')
  const metric = metrics.find(m => m.id === f.metric)

  const submit = () => {
    if (!f.text.trim()) return
    const body: Record<string, unknown> = { kind: f.kind, text: f.text.trim(), priority: f.priority }
    if (f.owner_section) body.owner_section = f.owner_section
    if (f.kind === 'ffir') { body.metric = f.metric; body.comparator = f.comparator; body.threshold = Number(f.threshold); if (f.scope.trim()) body.scope = f.scope.trim() }
    if (f.kind === 'pir') body.pir_id = f.pir_id
    act('writing a CCIR line', async () => { await api.writeCcir(body); setWrite(false); setF({ ...f, text: '', scope: '' }) })
  }

  const row = (l: CcirLine) => (
    <li key={l.id} className={`row two ccir ${l.state}`}>
      <div className="l1">
        <span className={`sev ${l.state === 'tripped' ? 'critical' : l.state === 'unmeasured' ? 'low' : 'ok'}`} title={KIND_HINT[l.kind]}>{KIND_LABEL[l.kind]}</span>
        <span className="name">{l.text}</span>
        <span className="chip dim" title="the section that answers this line">{l.owner_section}</span>
        <span className={`chip ${l.state === 'tripped' ? 'open' : l.state === 'unmeasured' ? 'active' : 'green'}`}>
          {l.state === 'tripped' ? `TRIPPED${l.tripped_min != null ? ` · ${l.tripped_min}m` : ''}` : l.state === 'unmeasured' ? 'NO READING' : l.state === 'narrative' ? 'STANDING' : 'GREEN'}
        </span>
      </div>
      <div className="l2">
        <span className="dim small">
          PRI {l.priority} · {l.condition}
          {l.value != null && <> · now <span className="mono">{l.value}{l.unit === '%' ? '%' : ` ${l.unit}`}</span></>}
          {l.trips > 0 && <> · {l.trips} trip{l.trips === 1 ? '' : 's'}</>}
        </span>
      </div>
      <div className="l3">
        {canEdit && l.status === 'active' && <span className="acts"><button className="mini" disabled={!!busy} onClick={() => act(`retiring ${l.text}`, () => api.amendCcir(l.id, { status: 'inactive' }))}>RETIRE</button></span>}
        {canEdit && l.status === 'inactive' && <span className="acts"><button className="mini" disabled={!!busy} onClick={() => act(`restoring ${l.text}`, () => api.amendCcir(l.id, { status: 'active' }))}>RESTORE</button></span>}
      </div>
    </li>
  )

  return (
    <>
      <Headline
        big={String(counts.tripped)}
        label={counts.tripped === 1 ? 'requirement tripped' : 'requirements tripped'}
        sub={`${counts.active} active of ${counts.total} · ${counts.unmeasured} with no reading`}
        tone={counts.tripped ? 'red' : counts.unmeasured ? 'amber' : 'green'}
      />
      {tripped.length > 0 && <>
        <Question q="What has to wake the commander" count={tripped.length} />
        <ul className="list">{tripped.map(row)}</ul>
      </>}
      {(['pir', 'ffir', 'eefi'] as const).map(kind => {
        const of = lines.filter(l => l.kind === kind && l.state !== 'tripped')
        if (of.length === 0) return null
        return <div key={kind}>
          <Question q={`${KIND_LABEL[kind]} — ${KIND_HINT[kind].split(' — ')[1]}`} count={of.length} />
          <ul className="list">{of.map(row)}</ul>
        </div>
      })}
      {lines.length === 0 && <div className="dim small pad">No CCIR written. A wall with no CCIR is a wall nobody agreed to watch.</div>}
      {canEdit && <div className="pad">
        <button className="mini" onClick={() => setWrite(v => !v)}>{write ? 'CANCEL' : '+ WRITE A LINE'}</button>
        {write && <div className="form">
          <div className="s-row">
            <span>KIND</span>
            {(['ffir', 'pir', 'eefi'] as const).map(k => <button key={k} className={`chip btn ${f.kind === k ? 'on' : ''}`} title={KIND_HINT[k]} onClick={() => setF({ ...f, kind: k })}>{KIND_LABEL[k]}</button>)}
          </div>
          <input placeholder="The requirement, in the commander's words" value={f.text} onChange={e => setF({ ...f, text: e.target.value })} />
          {f.kind === 'ffir' && <>
            <div className="s-row">
              <span>WATCHES</span>
              <select value={f.metric} onChange={e => setF({ ...f, metric: e.target.value })}>
                {metrics.map(m => <option key={m.id} value={m.id}>{m.section} · {m.label}</option>)}
              </select>
            </div>
            <div className="s-row">
              <span>TRIPS</span>
              <select value={f.comparator} onChange={e => setF({ ...f, comparator: e.target.value })}>
                {Object.entries(COMPARATOR_WORD).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              <input className="narrow" value={f.threshold} onChange={e => setF({ ...f, threshold: e.target.value })} />
              <span className="dim small">{metric?.unit}</span>
            </div>
            <input placeholder="Scope — a unit, a site, a supply class (optional)" value={f.scope} onChange={e => setF({ ...f, scope: e.target.value })} />
          </>}
          {f.kind === 'pir' && <div className="s-row">
            <span>PIR</span>
            <select value={f.pir_id} onChange={e => setF({ ...f, pir_id: e.target.value })}>
              <option value="">— pick the PIR this line reports on —</option>
              {pirs.map(p => <option key={p.id} value={p.id}>{p.question.slice(0, 70)}</option>)}
            </select>
          </div>}
          {f.kind === 'eefi' && <div className="dim small">An EEFI never trips by itself — nothing in the data measures our own signature. It is a standing line the staff checks itself against.</div>}
          <div className="s-row">
            <span>PRIORITY</span>
            {[1, 2, 3].map(p => <button key={p} className={`chip btn ${f.priority === p ? 'on' : ''}`} onClick={() => setF({ ...f, priority: p })}>{p}</button>)}
            <button className="mini" disabled={!!busy || !f.text.trim() || (f.kind === 'pir' && !f.pir_id)} onClick={submit}>WRITE</button>
          </div>
        </div>}
      </div>}
    </>
  )
}

