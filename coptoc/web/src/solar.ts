// Sun times for the board's centre — BMNT, sunrise, sunset, EENT — from the standard sunrise equation (NOAA / Meeus).
// No data source: it is arithmetic on the AO's latitude and longitude, so it is never wrong for want of a feed.
// Accuracy is a couple of minutes, which is what a planning cell uses it for. Polar day or night returns null.

const RAD = Math.PI / 180
const J2000 = 2451545.0
const toJulian = (ms: number) => ms / 864e5 + 2440587.5
const fromJulian = (j: number) => new Date((j - 2440587.5) * 864e5)

export interface SunTimes { bmnt: Date | null; sunrise: Date | null; sunset: Date | null; eent: Date | null; transit: Date }

/** Times for the UTC day containing `at`. BMNT / EENT are nautical twilight (sun 12° below the horizon). */
export function sunTimes(lat: number, lon: number, at: Date = new Date()): SunTimes {
  const day = Math.floor(toJulian(at.getTime()) - J2000 + 0.0008)   // days since J2000 at the UTC noon nearest `at`
  const jStar = day - lon / 360                                        // mean solar noon, longitude east-positive
  const M = ((357.5291 + 0.98560028 * jStar) % 360 + 360) % 360       // solar mean anomaly
  const C = 1.9148 * Math.sin(M * RAD) + 0.02 * Math.sin(2 * M * RAD) + 0.0003 * Math.sin(3 * M * RAD)
  const L = (M + C + 180 + 102.9372) % 360                             // ecliptic longitude
  const jTransit = J2000 + jStar + 0.0053 * Math.sin(M * RAD) - 0.0069 * Math.sin(2 * L * RAD)
  const decl = Math.asin(Math.sin(L * RAD) * Math.sin(23.4397 * RAD))
  const hourAngle = (altitude: number): number | null => {
    const cosW = (Math.sin(altitude * RAD) - Math.sin(lat * RAD) * Math.sin(decl)) / (Math.cos(lat * RAD) * Math.cos(decl))
    return Math.abs(cosW) > 1 ? null : Math.acos(cosW) / RAD / 360
  }
  const pair = (altitude: number): [Date | null, Date | null] => { const w = hourAngle(altitude); return w === null ? [null, null] : [fromJulian(jTransit - w), fromJulian(jTransit + w)] }
  const [sunrise, sunset] = pair(-0.833)
  const [bmnt, eent] = pair(-12)
  return { bmnt, sunrise, sunset, eent, transit: fromJulian(jTransit) }
}

/** DAY, NIGHT, or TWILIGHT right now, from the same times. */
export function sunState(t: SunTimes, now: Date = new Date()): 'day' | 'night' | 'twilight' | 'unknown' {
  if (!t.sunrise || !t.sunset) return 'unknown'
  const n = now.getTime()
  if (n >= t.sunrise.getTime() && n <= t.sunset.getTime()) return 'day'
  if (t.bmnt && t.eent && ((n >= t.bmnt.getTime() && n < t.sunrise.getTime()) || (n > t.sunset.getTime() && n <= t.eent.getTime()))) return 'twilight'
  return 'night'
}

export const hhmmZ = (d: Date | null) => d ? d.toISOString().slice(11, 16).replace(':', '') + 'Z' : '——'
