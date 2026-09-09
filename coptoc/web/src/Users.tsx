// §9 — the directory and the permission grid. Admin only. Everyone else sees this panel's sign-in list in the header.
import { useEffect, useState } from 'react'
import * as api from './api'
import type { UserInfo } from './types'

const SECTIONS = ['S1', 'S2', 'S3', 'S4', 'S6'] as const
const NEXT: Record<string, 'view' | 'edit' | null> = { none: 'view', view: 'edit', edit: null }

export function UsersPanel({ busy, act, reload, onChanged }: { busy: string | null; act: (l: string, f: () => Promise<unknown>) => void; reload: number; onChanged: () => void }) {
  const [users, setUsers] = useState<UserInfo[]>([])
  const [presets, setPresets] = useState<Record<string, { label: string }>>({})
  const [draft, setDraft] = useState({ name: '', title: '', preset: 'custom' })
  const [err, setErr] = useState<string | null>(null)
  const load = () => api.listUsers().then(d => { setUsers(d.users); setPresets(d.presets); setErr(null) }).catch(e => setErr(String(e)))
  useEffect(() => { load() }, [reload])
  const cycle = (u: UserInfo, s: string) => {
    const cur = u.perms?.[s] ?? 'none'; const nxt = NEXT[cur]
    act(`setting ${u.name} ${s}`, async () => { await api.updateUser(u.id, { perms: { [s]: nxt } }); await load(); onChanged() })
  }
  const flag = (u: UserInfo, k: 'battle_captain' | 'admin' | 'active') => act(`setting ${u.name} ${k}`, async () => { await api.updateUser(u.id, { [k]: !u[k] } as Partial<UserInfo>); await load(); onChanged() })
  const add = () => { if (!draft.name.trim()) return; act(`adding ${draft.name}`, async () => { await api.createUser({ name: draft.name.trim(), title: draft.title.trim(), preset: draft.preset }); setDraft({ name: '', title: '', preset: 'custom' }); await load(); onChanged() }) }
  const remove = (u: UserInfo) => { if (!window.confirm(`Remove ${u.name}?`)) return; act(`removing ${u.name}`, async () => { await api.deleteUser(u.id); await load(); onChanged() }) }
  if (err) return <div className="dim small" style={{ padding: 14 }}>{err.includes('403') ? 'The directory is the admin\u2019s.' : err}</div>
  return (<>
    <div className="settings-blurb dim small">Per section: click to cycle none → view → edit. BC is the floor (watch, roll calls, FLASH, DEFCON, operations). ADMIN is this grid. A preset fills the row; the grid is the truth.</div>
    <div className="users-grid">
      <div className="uh">USER</div>{SECTIONS.map(s => <div key={s} className="uh c">{s}</div>)}<div className="uh c">BC</div><div className="uh c">ADMIN</div><div className="uh c"></div>
      {users.map(u => (<div key={u.id} className={`urow ${u.active === false ? 'off' : ''}`}>
        <div className="uname"><b>{u.name}</b><span className="dim small"> · {u.title}{u.preset !== 'custom' && ` · ${presets[u.preset]?.label ?? u.preset}`}</span></div>
        {SECTIONS.map(s => { const v = u.perms?.[s]; return <button key={s} className={`perm ${v ?? 'none'}`} disabled={!!busy} onClick={() => cycle(u, s)} title={`${s}: ${v ?? 'none'}`}>{v === 'edit' ? 'E' : v === 'view' ? 'V' : '·'}</button> })}
        <button className={`perm flag ${u.battle_captain ? 'on' : ''}`} disabled={!!busy} onClick={() => flag(u, 'battle_captain')}>{u.battle_captain ? '★' : '·'}</button>
        <button className={`perm flag ${u.admin ? 'on' : ''}`} disabled={!!busy} onClick={() => flag(u, 'admin')}>{u.admin ? '⚙' : '·'}</button>
        <span className="uacts"><button className="mini" disabled={!!busy} onClick={() => flag(u, 'active')} title={u.active === false ? 'reactivate' : 'deactivate'}>{u.active === false ? 'ON' : 'OFF'}</button><button className="mini danger" disabled={!!busy} onClick={() => remove(u)}>×</button></span>
      </div>))}
    </div>
    <div className="section-label">ADD A USER</div>
    <div className="dform">
      <input placeholder="Name (rank and name)" value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} />
      <input placeholder="Duty position" value={draft.title} onChange={e => setDraft({ ...draft, title: e.target.value })} />
      <div className="row-btns"><select value={draft.preset} onChange={e => setDraft({ ...draft, preset: e.target.value })}>{Object.entries(presets).map(([k, p]) => <option key={k} value={k}>{p.label}</option>)}</select>
        <button className="mini ok" disabled={!!busy || !draft.name.trim()} onClick={add}>ADD</button></div>
    </div>
  </>)
}
