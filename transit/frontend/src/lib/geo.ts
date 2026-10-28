export type LngLat = [number, number]

const dist = (a: LngLat, b: LngLat) => Math.hypot(a[0] - b[0], a[1] - b[1])

/** Resample a polyline to exactly n points evenly spaced along its length (so two routes can be blended). */
export function resample(line: LngLat[], n: number): LngLat[] {
  if (line.length === 0) return []
  if (line.length === 1) return Array.from({ length: n }, () => line[0])
  const cum = [0]
  for (let i = 1; i < line.length; i++) cum.push(cum[i - 1] + dist(line[i - 1], line[i]))
  const total = cum[cum.length - 1] || 1
  const out: LngLat[] = []
  let seg = 1
  for (let k = 0; k < n; k++) {
    const target = (k / (n - 1)) * total
    while (seg < cum.length - 1 && cum[seg] < target) seg++
    const span = cum[seg] - cum[seg - 1] || 1
    const t = Math.min(1, Math.max(0, (target - cum[seg - 1]) / span))
    out.push([line[seg - 1][0] + (line[seg][0] - line[seg - 1][0]) * t, line[seg - 1][1] + (line[seg][1] - line[seg - 1][1]) * t])
  }
  return out
}

/** Linear blend between two equally long polylines; t in [0, 1]. */
export function blend(a: LngLat[], b: LngLat[], t: number): LngLat[] {
  return a.map((p, i) => [p[0] + (b[i][0] - p[0]) * t, p[1] + (b[i][1] - p[1]) * t] as LngLat)
}

export const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2)
