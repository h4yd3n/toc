import { useMemo } from 'react'

interface TzDef {
  label: string
  tz: string
  sub: string
  fullName: string
  isZulu?: boolean
}

const MILITARY_TZS: TzDef[] = [
  { label: 'PACIFIC', tz: 'Pacific/Honolulu', sub: 'HST', fullName: 'Pacific / INDOPACOM (Hawaii)' },
  { label: 'LOS ANGELES', tz: 'America/Los_Angeles', sub: 'PT', fullName: 'Los Angeles / US West Coast' },
  { label: 'WASH DC', tz: 'America/New_York', sub: 'ET', fullName: 'Washington DC / Pentagon / HQDA' },
  { label: 'ZULU', tz: 'UTC', sub: 'UTC', fullName: 'Universal Coordinated Time (Military Z)', isZulu: true },
  { label: 'MIDDLE EAST', tz: 'Asia/Baghdad', sub: 'AST', fullName: 'Middle East / CENTCOM AOR (Baghdad/Kuwait)' },
  { label: 'KOREA', tz: 'Asia/Seoul', sub: 'KST', fullName: 'Korea / USFK / 8th Army (Seoul)' },
]

const CORPORATE_TZS: TzDef[] = [
  { label: 'SAN FRANCISCO', tz: 'America/Los_Angeles', sub: 'PT', fullName: 'San Francisco HQ (Pacific Time)' },
  { label: 'NEW YORK', tz: 'America/New_York', sub: 'ET', fullName: 'New York / Eastern Operations' },
  { label: 'ZULU', tz: 'UTC', sub: 'UTC', fullName: 'Universal Coordinated Time (Z)', isZulu: true },
  { label: 'DUBLIN', tz: 'Europe/Dublin', sub: 'IST/GMT', fullName: 'Dublin, Ireland / EMEA Operations' },
  { label: 'SINGAPORE', tz: 'Asia/Singapore', sub: 'SGT', fullName: 'Singapore / APAC Regional Hub' },
]

function formatTz(d: Date, tz: string): string {
  try {
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: tz,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(d)
  } catch {
    return d.toISOString().slice(11, 19)
  }
}

interface Props {
  now: number
  profile?: 'military' | 'corporate'
}

export default function HeaderClocks({ now, profile = 'military' }: Props) {
  const tzs = profile === 'corporate' ? CORPORATE_TZS : MILITARY_TZS
  const date = useMemo(() => new Date(now), [now])

  return (
    <div className="header-clocks" title="Operational Time Zones">
      {tzs.map(t => {
        const timeStr = formatTz(date, t.tz)
        const displayTime = t.isZulu ? `${timeStr}Z` : timeStr
        return (
          <div
            key={t.label}
            className={`hclock ${t.isZulu ? 'zulu' : ''}`}
            title={`${t.fullName} (${t.tz})`}
          >
            <div className="hclock-top">
              <span className="hclock-label">{t.label}</span>
              <span className="hclock-sub dim">{t.sub}</span>
            </div>
            <div className="hclock-time mono">{displayTime}</div>
          </div>
        )
      })}
    </div>
  )
}
