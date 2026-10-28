import { describe, expect, it } from 'vitest'
import { blend, resample, type LngLat } from '../lib/geo'

describe('route morph geometry', () => {
  const line: LngLat[] = [[0, 0], [10, 0], [10, 10]]

  it('resamples to exactly n points keeping the endpoints', () => {
    const r = resample(line, 21)
    expect(r).toHaveLength(21)
    expect(r[0]).toEqual([0, 0])
    expect(r[20][0]).toBeCloseTo(10); expect(r[20][1]).toBeCloseTo(10)
  })

  it('spaces points evenly along the length', () => {
    const r = resample(line, 5)           // total length 20 -> every 5 units
    expect(r[1][0]).toBeCloseTo(5); expect(r[2][0]).toBeCloseTo(10); expect(r[2][1]).toBeCloseTo(0); expect(r[3][1]).toBeCloseTo(5)
  })

  it('handles a single point and blends between two lines', () => {
    expect(resample([[3, 4]], 3)).toEqual([[3, 4], [3, 4], [3, 4]])
    const a = resample([[0, 0], [0, 0]], 4), b = resample([[10, 10], [10, 10]], 4)
    expect(blend(a, b, 0.5)[2]).toEqual([5, 5])
    expect(blend(a, b, 0)[0]).toEqual([0, 0]); expect(blend(a, b, 1)[3]).toEqual([10, 10])
  })
})
