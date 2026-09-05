// §13 — UPLOAD: drop the spreadsheet a section actually keeps (Excel or CSV, however it is formatted). The app finds the header,
// proposes what each column is, shows a sample and what it cannot place; nothing lands until COMMIT.
import { useRef, useState } from 'react'
import * as api from './api'
import type { ImportResult, UploadPreview } from './types'

export function UploadDrawer({ section, busy, act, onDone }: { section: 'S1' | 'S3' | 'S4' | 'S6'; busy: string | null; act: (l: string, f: () => Promise<unknown>) => void; onDone: () => void }) {
  const [pv, setPv] = useState<UploadPreview | null>(null)
  const [mapping, setMapping] = useState<Record<string, string | null>>({})
  const [kind, setKind] = useState<'supply' | 'shipments'>('supply')
  const [result, setResult] = useState<(ImportResult & { section: string }) | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const what: Record<string, string> = { S1: 'a roster — rank, name, unit path like B/1-101 ARB, duty, phone, email', S3: 'a schedule — events, operations, travel with start, end, place', S4: 'a LOGSTAT — site, class, item, on hand, authorized; or shipments', S6: 'a comms status — site, system, PACE role, status' }
  const pick = (f: File | undefined) => { if (!f) return; setResult(null); setErr(null); act(`reading ${f.name}`, async () => { try { const p = await api.uploadPreview(section, f); setPv(p); setMapping(p.mapping); setKind(p.kind) } catch (e) { setErr(String(e)) } }) }
  const commit = () => pv && act(`landing ${pv.filename}`, async () => { const r = await api.uploadCommit(section, { upload_id: pv.upload_id, sheet: pv.sheet, mapping, kind }); setResult(r); onDone() })
  const mapped = Object.values(mapping).filter(Boolean)
  return (
    <div className="dform upload">
      <div className="dform-head">UPLOAD <span className="dim">{what[section]}</span></div>
      <div className="row-btns">
        <input ref={fileRef} type="file" accept=".xlsx,.xlsm,.csv" hidden onChange={e => pick(e.target.files?.[0])} />
        <button className="mini" disabled={!!busy} onClick={() => fileRef.current?.click()}>CHOOSE FILE…</button>
        {pv && <span className="dim small">{pv.filename} · sheet <b>{pv.sheet}</b> · header row {pv.header_row + 1} · {pv.rows} rows · mapping by {pv.proposed_by === 'model' ? 'the model' : 'the headers'}</span>}
      </div>
      {err && <div className="bad small">{err}</div>}
      {pv && <>
        {pv.sheets.length > 1 && <div className="dim small">Sheets: {pv.sheets.join(' · ')} — the first is used; re-save the workbook with the wanted sheet first if it is another.</div>}
        {section === 'S4' && <div className="row-btns"><span className="dim small">This sheet is</span>{(['supply', 'shipments'] as const).map(k => <button key={k} className={`chip btn ${kind === k ? 'on' : ''}`} onClick={() => setKind(k)}>{k.toUpperCase()}</button>)}</div>}
        <div className="map-grid">
          {pv.columns.map(c => (<div key={c} className="map-row">
            <span className="mcol" title={c}>{c}</span><span className="dim">→</span>
            <select value={mapping[c] ?? ''} onChange={e => setMapping({ ...mapping, [c]: e.target.value || null })}>
              <option value="">— ignore —</option>{Object.entries(pv.targets).map(([t, l]) => <option key={t} value={t}>{l}</option>)}
            </select>
            <span className="sample dim small">{pv.samples.slice(0, 2).map(r => r[c]).filter(Boolean).join(' · ') || '·'}</span>
          </div>))}
        </div>
        {pv.issues.length > 0 && <div className="small" style={{ color: 'var(--amber)' }}>{pv.issues.join(' · ')}</div>}
        <div className="row-btns">
          <button className="mini ok" disabled={!!busy || mapped.length === 0} onClick={commit}>COMMIT {pv.rows} ROWS</button>
          <button className="mini" disabled={!!busy} onClick={() => { setPv(null); setResult(null) }}>CLEAR</button>
        </div>
      </>}
      {result && <div className="small" style={{ color: result.errors.length ? 'var(--amber)' : 'var(--green)' }}>
        {result.created} created · {result.updated} updated · {result.skipped} skipped{result.errors.length > 0 && <ul className="errs">{result.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>}
      </div>}
    </div>)
}
