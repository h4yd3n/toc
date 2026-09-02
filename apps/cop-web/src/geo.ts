const R = 6371
const toRad = (d: number) => (d * Math.PI) / 180
const toDeg = (r: number) => (r * 180) / Math.PI

/** Ring of [lon,lat] around a center at radius km. */
export function circle(lat: number, lon: number, km: number, n = 64): [number, number][] {
  const pts: [number, number][] = []
  const φ1 = toRad(lat), λ1 = toRad(lon), δ = km / R
  for (let i = 0; i <= n; i++) {
    const θ = (2 * Math.PI * i) / n
    const φ2 = Math.asin(Math.sin(φ1) * Math.cos(δ) + Math.cos(φ1) * Math.sin(δ) * Math.cos(θ))
    const λ2 = λ1 + Math.atan2(Math.sin(θ) * Math.sin(δ) * Math.cos(φ1), Math.cos(δ) - Math.sin(φ1) * Math.sin(φ2))
    pts.push([toDeg(λ2), toDeg(φ2)])
  }
  return pts
}

/** Great-circle arc between two points, unwrapped across the antimeridian for continuous drawing. */
export function arc(lat1: number, lon1: number, lat2: number, lon2: number, n = 64): [number, number][] {
  const φ1 = toRad(lat1), λ1 = toRad(lon1), φ2 = toRad(lat2), λ2 = toRad(lon2)
  const d = 2 * Math.asin(Math.sqrt(Math.sin((φ2 - φ1) / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin((λ2 - λ1) / 2) ** 2))
  const out: [number, number][] = []
  let prevLon: number | null = null
  for (let i = 0; i <= n; i++) {
    const f = i / n
    const A = Math.sin((1 - f) * d) / Math.sin(d), B = Math.sin(f * d) / Math.sin(d)
    const x = A * Math.cos(φ1) * Math.cos(λ1) + B * Math.cos(φ2) * Math.cos(λ2)
    const y = A * Math.cos(φ1) * Math.sin(λ1) + B * Math.cos(φ2) * Math.sin(λ2)
    const z = A * Math.sin(φ1) + B * Math.sin(φ2)
    let lon = toDeg(Math.atan2(y, x))
    const lat = toDeg(Math.atan2(z, Math.sqrt(x * x + y * y)))
    if (prevLon !== null) {
      while (lon - prevLon > 180) lon -= 360
      while (lon - prevLon < -180) lon += 360
    }
    prevLon = lon
    out.push([lon, lat])
  }
  return out
}
