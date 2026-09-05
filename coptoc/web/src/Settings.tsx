// §11.3 — SETTINGS: sources, keys, comms, sections. Battle Captain only. Keys are write-only: the wall shows set / not set, never a value.
import { useEffect, useState } from 'react'
import * as api from './api'
import { SourcesDrawer } from './Requirements'
import type { SettingInfo } from './types'

const GROUPS: { key: SettingInfo['group']; title: string; blurb: string }[] = [
  { key: 'sources', title: 'SOURCE KEYS', blurb: 'Keyless feeds are already live. These unlock the keyed ones — the SOURCES list below turns LIVE when a key lands.' },
  { key: 'comms', title: 'COMMS', blurb: 'Without these, roll-call SMS and chat are recorded as simulated, never sent.' },
  { key: 'drafter', title: 'S2 DRAFTER', blurb: 'With a key, assessments and INTSUM prose are drafted for a human to release. Without, humans draft.' },
  { key: 'sections', title: 'STAFF SECTIONS', blurb: 'Which sections this deployment runs. S1–S3 are always on.' },
]

export function SettingsPanel({ busy, act, reload }: { busy: string | null; act: (l: string, f: () => Promise<unknown>) => void; reload: number }) {
  const [items, setItems] = useState<SettingInfo[]>([])
  const [note, setNote] = useState('')
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [err, setErr] = useState<string | null>(null)
  const load = () => api.listSettings().then(d => { setItems(d.settings); setNote(d.note); setErr(null) }).catch(e => setErr(String(e)))
  useEffect(() => { load() }, [reload])
  const save = (s: SettingInfo) => { const v = (draft[s.name] ?? '').trim(); if (!v) return; act(`setting ${s.label}`, async () => { await api.putSetting(s.name, v); setDraft(d => ({ ...d, [s.name]: '' })); await load() }) }
  const clear = (s: SettingInfo) => { if (!window.confirm(`Clear ${s.label}?`)) return; act(`clearing ${s.label}`, async () => { await api.clearSetting(s.name); await load() }) }
  if (err) return <div className="dim small" style={{ padding: 14 }}>{err.includes('403') ? 'Settings are the Battle Captain\u2019s.' : err}</div>
  return (<>
    <div className="settings-note dim small">{note}</div>
    {GROUPS.map(g => (
      <div key={g.key}>
        <div className="section-label">{g.title}</div>
        <div className="dim small settings-blurb">{g.blurb}</div>
        <ul className="list settings-list">
          {items.filter(i => i.group === g.key).map(s => (
            <li key={s.name} className="row two" title={s.help}>
              <div className="l1">
                <span className="name">{s.label}<span className="dim mono"> · {s.name}</span></span>
                <span className={`chip ${s.set_in === 'env' ? 'green' : s.set_in === 'stored' ? 'active' : ''}`}>{s.set_in === 'env' ? 'FROM ENV' : s.set_in === 'stored' ? `SET${s.set_by ? ' · ' + s.set_by : ''}` : 'NOT SET'}</span>
              </div>
              <div className="l2">
                {s.set_in && <span className="mono dim small">{s.secret ? (s.hint ?? '••••') : s.value}</span>}
                {s.error && <span className="bad small">{s.error}</span>}
                {s.set_in !== 'env' && <>
                  <input className="setting-input" type={s.secret ? 'password' : 'text'} autoComplete="off" placeholder={s.set_in ? 'replace…' : (s.help || 'value')} value={draft[s.name] ?? ''}
                    onChange={e => setDraft(d => ({ ...d, [s.name]: e.target.value }))} onKeyDown={e => { if (e.key === 'Enter') save(s) }} disabled={!!busy} />
                  <button className="mini ok" disabled={!!busy || !(draft[s.name] ?? '').trim()} onClick={() => save(s)}>SET</button>
                  {s.set_in === 'stored' && <button className="mini danger" disabled={!!busy} onClick={() => clear(s)}>CLEAR</button>}
                </>}
                {s.set_in === 'env' && <span className="dim small">set on the server; the environment wins</span>}
              </div>
            </li>))}
        </ul>
      </div>))}
    <div className="section-label">SOURCES <span className="dim">enable · grade · cadence</span></div>
    <SourcesDrawer busy={busy} act={act} reload={reload} />
  </>)
}
