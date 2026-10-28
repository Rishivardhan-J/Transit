import { describe, expect, it } from 'vitest'
import { PRESETS, setWeight, WEIGHT_KEYS } from '../lib/weights'

const sum = (w: Record<string, number>) => WEIGHT_KEYS.reduce((s, k) => s + w[k as keyof typeof w], 0)

describe('setWeight (what-if sliders)', () => {
  it('always renormalizes so the four weights sum to 1', () => {
    for (const start of Object.values(PRESETS)) {
      for (const k of WEIGHT_KEYS) {
        for (const v of [0, 0.1, 0.5, 0.93, 1]) expect(sum(setWeight(start, k, v))).toBeCloseTo(1, 10)
      }
    }
  })

  it('keeps the moved weight and scales the others proportionally', () => {
    const next = setWeight({ w_distance: 0.4, w_time: 0.4, w_fuel: 0.1, w_delay: 0.1 }, 'w_distance', 0.6)
    expect(next.w_distance).toBe(0.6)
    expect(next.w_time).toBeCloseTo(0.4 * (0.4 / 0.6), 10)
    expect(next.w_fuel).toBeCloseTo(next.w_delay, 10)
  })

  it('splits the remainder evenly when every other weight was zero', () => {
    const next = setWeight({ w_distance: 1, w_time: 0, w_fuel: 0, w_delay: 0 }, 'w_distance', 0.4)
    expect(next.w_time).toBeCloseTo(0.2, 10)
    expect(sum(next)).toBeCloseTo(1, 10)
  })

  it('clamps out-of-range input', () => {
    expect(setWeight(PRESETS.balanced, 'w_time', 5).w_time).toBe(1)
    expect(setWeight(PRESETS.balanced, 'w_time', -1).w_time).toBe(0)
  })
})
