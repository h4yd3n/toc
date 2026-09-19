// §3.7 — the exercise. A banner nobody can miss while a scenario is running, and exercise control: pick a scenario,
// set the speed, STARTEX, watch the MSEL fire, pull an inject forward, ENDEX. The wall can only run one at a time,
// and only on the exercise profile — that separation is what keeps an inject off a real picture.
import { useState } from 'react'
import * as api from './api'
import { Question } from './Headline'
import type { ExerciseBoard, Inject } from './types'

const KIND_ICON: Record<string, string> = {
  message: '✎', spotrep: '◎', system: '((·))', supply: '⛽', equipment: '✇',
  position: '➜', posture: '▲', rollcall: '☎', tasking: '⇄',
}

/** The banner. Marked EXERCISE the way a CPX message is, because a drill that reads as real is how a drill hurts. */
export function ExerciseBanner({ board }: { board: ExerciseBoard | undefined }) {
  if (!board?.running || !board.exercise) return null
  const ex = board.exercise
  const next = ex.next
  return (
    <div className="ex-banner" title="A scenario is running on the exercise profile. Nothing here is real.">
      <span className="ex-tape">EXERCISE EXERCISE EXERCISE</span>
      <span className="ex-name">{ex.name}</span>
      <span className="ex-clock mono">T+{(ex.elapsed_min ?? 0).toFixed(1)}′{ex.speed !== 1 ? ` · ×${ex.speed}` : ''}</span>
      <span className="ex-count mono">{ex.fired}/{ex.total} injects{ex.failed ? ` · ${ex.failed} failed` : ''}</span>
      {next && <span className="ex-next dim">next: {next.title}{next.in_min != null && next.in_min > 0 ? ` in ${next.in_min.toFixed(1)}′` : ' now'}</span>}
    </div>
  )
}

/** Exercise control, inside SETTINGS. The MSEL reads in order and says what each inject did. */
export function ExercisePanel({ board, profile, busy, act }: {
  board: ExerciseBoard | undefined
  profile: string
  busy: string | null
  act: (label: string, f: () => Promise<unknown>) => void
}) {
  const [scenario, setScenario] = useState('')
  const [speed, setSpeed] = useState(4)
  const [notes, setNotes] = useState('')
  if (!board) return null
  const ex = board.exercise
  const pick = scenario || board.scenarios[0]?.id || ''
  const chosen = board.scenarios.find(sc => sc.id === pick)

  if (profile !== 'exercise') return (
    <>
      <div className="section-label">EXERCISE <span className="dim">§3.7</span></div>
      <div className="dim small pad">
        An exercise runs on the <b>exercise profile</b> only — switch the profile beside the wordmark to set one up.
        That separation is the guarantee: an inject can never reach this picture.
      </div>
    </>
  )

  const row = (i: Inject) => (
    <li key={i.id} className={`row two inject ${i.status}`}>
      <div className="l1">
        <span className="mono dim ex-seq">{String(i.seq).padStart(2, '0')} · T+{i.offset_min}′</span>
        <span className="name">{KIND_ICON[i.kind] ?? '·'} {i.title}</span>
        {i.section && <span className="chip dim">{i.section}</span>}
        <span className={`chip ${i.status === 'fired' ? 'green' : i.status === 'failed' ? 'open' : i.status === 'skipped' ? 'dim' : 'active'}`}>
          {i.status === 'pending' && i.in_min != null ? (i.in_min > 0 ? `IN ${i.in_min.toFixed(1)}′` : 'DUE') : i.status.toUpperCase()}
        </span>
      </div>
      <div className="l2">
        <span className="dim small">{i.error ? `FAILED — ${i.error}` : i.result || '—'}</span>
      </div>
      <div className="l3">
        {ex?.status === 'running' && i.status === 'pending' &&
          <span className="acts"><button className="mini" disabled={!!busy} onClick={() => act(`firing inject ${i.seq}`, () => api.fireInject(i.id))}>FIRE NOW</button></span>}
      </div>
    </li>
  )

  return (
    <>
      <div className="section-label">EXERCISE CONTROL <span className="dim">§3.7 · MSEL on the real clock</span></div>
      {(!ex || ex.status === 'ended') && <div className="pad">
        <div className="s-row">
          <span>SCENARIO</span>
          <select value={pick} onChange={e => setScenario(e.target.value)}>
            {board.scenarios.map(sc => <option key={sc.id} value={sc.id}>{sc.name} — {sc.injects} injects over {sc.runs_min}′</option>)}
          </select>
        </div>
        {chosen && <div className="dim small">{chosen.summary}</div>}
        <div className="s-row">
          <span>SPEED</span>
          {[1, 4, 10, 60].map(x => <button key={x} className={`chip btn ${speed === x ? 'on' : ''}`} onClick={() => setSpeed(x)} title={`a ${chosen?.runs_min ?? 0}-minute scenario runs in ${((chosen?.runs_min ?? 0) / x).toFixed(1)} minutes`}>×{x}</button>)}
          <span className="dim small">the offsets divide; the clock never does</span>
        </div>
        <button className="mini" disabled={!!busy || !pick} onClick={() => act('loading the MSEL', () => api.createExercise(pick, speed))}>LOAD MSEL</button>
      </div>}

      {ex && ex.status !== 'ended' && <div className="pad">
        <div className="ex-run-name">{ex.name}</div>
        <div className="s-row">
          <span className="chip dim">×{ex.speed}</span>
          <span className={`chip ${ex.status === 'running' ? 'open' : 'active'}`}>{ex.status.toUpperCase()}</span>
          {ex.status === 'planned'
            ? <button className="mini" disabled={!!busy} onClick={() => act('STARTEX', () => api.startExercise(ex.id))}>STARTEX</button>
            : <button className="mini" disabled={!!busy} onClick={() => act('ENDEX', () => api.endExercise(ex.id, notes))}>ENDEX</button>}
        </div>
        {ex.status === 'running' && <input placeholder="ENDEX note — what the staff did with it" value={notes} onChange={e => setNotes(e.target.value)} />}
      </div>}

      {ex && <>
        <Question q="The MSEL" count={`${ex.fired}/${ex.total}`} />
        <ul className="list">{board.injects.map(row)}</ul>
      </>}
      {ex?.status === 'ended' && <div className="dim small pad">
        Ended {ex.ended_at?.slice(0, 16).replace('T', ' ')}Z{ex.notes ? ` — ${ex.notes}` : ''}. The picture the exercise
        left is still standing: what the staff did with it is the point. Switching the profile reloads clean data.
      </div>}
    </>
  )
}
