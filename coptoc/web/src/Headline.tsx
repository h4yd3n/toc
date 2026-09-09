// §3.2 the hierarchy of a panel: the one number the Battle Captain asks for first, drawn large with a bar; the secondary
// counts as small tiles; then sections headed by the question they answer. Ratios are bars — a bar reads from across
// the room, a fraction does not. Color carries meaning only: green / amber / red for state, nothing else.
import type { Health, Threat } from './types'

export type Tone = Health | 'neutral' | 'blue'

/** green ≥ ok, amber ≥ warn, else red — the same thresholds everywhere so a bar means the same thing on every panel. */
export function toneFor(pct: number, ok = 95, warn = 85): Health { return pct >= ok ? 'green' : pct >= warn ? 'amber' : 'red' }

export function Headline({ big, label, sub, pct, tone = 'neutral', onClick }: { big: string | number; label: string; sub?: string; pct?: number; tone?: Tone; onClick?: () => void }) {
  return (
    <div className={`headline ${tone} ${onClick ? 'jump' : ''}`} onClick={onClick}>
      <div className="hl-row"><span className="hl-big">{big}</span><span className="hl-label">{label}{sub && <span className="hl-sub">{sub}</span>}</span></div>
      {pct !== undefined && <div className="bar hl-bar"><span className={tone} style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} /></div>}
    </div>)
}

export interface Tile { v: string | number; l: string; tone?: Tone; hide?: boolean; title?: string; onClick?: () => void }
/** The secondary counts under a headline. A tile with `hide` is not drawn: an exception counter shows only when it is non-zero. */
export function Tiles({ items, inline }: { items: Tile[]; inline?: boolean }) {
  const shown = items.filter(t => !t.hide)
  if (shown.length === 0) return null
  return <div className={`tiles ${inline ? 'inline' : ''}`}>{shown.map(t => <div key={t.l} className={`tile ${t.tone ?? 'neutral'} ${t.onClick ? 'jump' : ''}`} title={t.title} onClick={t.onClick}><span className="tv">{t.v}</span><span className="tl">{t.l}</span></div>)}</div>
}

/** A section heading phrased as the question it answers, with the count on the right. */
export function Question({ q, count, children }: { q: string; count?: string | number; children?: React.ReactNode }) {
  return <div className="section-label q"><span className="qtext">{q}</span>{count !== undefined && <span className="dim qcount">{count}</span>}{children}</div>
}

/** A small inline bar for a ratio in a row: present/assigned, covered/required, on hand/required. */
export function MiniBar({ a, b, tone, width }: { a: number; b: number; tone?: Tone; width?: number }) {
  const pct = b > 0 ? (100 * a) / b : 0
  return <span className="bar small mini" style={width ? { width } : undefined}><span className={tone ?? toneFor(pct)} style={{ width: `${Math.min(100, pct)}%` }} /></span>
}

const SEV_ORDER = ['critical', 'elevated', 'moderate', 'low'] as const
/** Threats by severity as four counted blocks: the shape of the threat picture at a glance. */
export function SevBlocks({ threats, onClick }: { threats: Threat[]; onClick?: () => void }) {
  return <div className={`sevblocks ${onClick ? 'jump' : ''}`} onClick={onClick} title="threats by severity">
    {SEV_ORDER.map(s => { const n = threats.filter(t => t.severity === s).length; return <span key={s} className={`sb ${s} ${n === 0 ? 'zero' : ''}`}><b>{n}</b><i>{s.slice(0, 4).toUpperCase()}</i></span> })}
  </div>
}
