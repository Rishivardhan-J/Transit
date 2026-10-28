export type WeightKey = 'w_distance' | 'w_time' | 'w_fuel' | 'w_delay'
export type WeightMap = Record<WeightKey, number>
export const WEIGHT_KEYS: WeightKey[] = ['w_distance', 'w_time', 'w_fuel', 'w_delay']

export const PRESETS: Record<string, WeightMap> = {
  balanced: { w_distance: 0.25, w_time: 0.25, w_fuel: 0.25, w_delay: 0.25 },
  time_focused: { w_distance: 0.1, w_time: 0.6, w_fuel: 0.1, w_delay: 0.2 },
  cost_focused: { w_distance: 0.2, w_time: 0.1, w_fuel: 0.6, w_delay: 0.1 },
  distance_focused: { w_distance: 0.7, w_time: 0.1, w_fuel: 0.1, w_delay: 0.1 },
}

/**
 * Set one weight and rescale the others proportionally so the four always sum to 1 (PRD 10 / 11.5).
 * If the others are all zero the remainder is split evenly.
 */
export function setWeight(current: WeightMap, key: WeightKey, value: number): WeightMap {
  const v = Math.min(1, Math.max(0, value))
  const others = WEIGHT_KEYS.filter((k) => k !== key)
  const restTotal = others.reduce((s, k) => s + current[k], 0)
  const remaining = 1 - v
  const next = { ...current, [key]: v } as WeightMap
  for (const k of others) next[k] = restTotal > 0 ? (current[k] / restTotal) * remaining : remaining / others.length
  return next
}
