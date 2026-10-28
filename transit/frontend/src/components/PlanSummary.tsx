import type { Metrics } from '../api/types'
import { fmtDelta, fmtNum } from '../lib/format'
import { StatusBadge, Text } from './ui'

interface Row { key: keyof Metrics; label: string; unit?: string; digits?: number }
const ROWS: Row[] = [
  { key: 'total_distance', label: 'Distance', unit: 'km', digits: 1 },
  { key: 'total_time_min', label: 'Route time', unit: 'min', digits: 0 },
  { key: 'total_cost', label: 'Weighted cost', digits: 1 },
  { key: 'vehicles_used', label: 'Vehicles used', digits: 0 },
  { key: 'predicted_late', label: 'At risk of late', digits: 0 },
  { key: 'orders_unassigned', label: 'Unassigned', digits: 0 },
]

/** Current-vs-new comparison; for every row here a lower number is better. */
export function MetricsCompare({ current, next, delta }: { current: Metrics | null | undefined; next: Metrics; delta: Record<string, number> | null | undefined }) {
  return (
    <div className="flex flex-col divide-y-1 divide-border-default">
      {ROWS.map((r) => {
        const d = delta?.[r.key as string]
        const tone = d === undefined || Math.abs(d) < 1e-6 ? 'neutral' : d < 0 ? 'success' : 'warning'
        return (
          <div key={r.key} className="flex items-center justify-between gap-3 py-3">
            <div>
              <Text variant="secondary" size={12}>{r.label}</Text>
              <Text size={20} weight="semibold" className="tabular-nums">{fmtNum(next[r.key] as number, r.digits)}<span className="text-12 text-text-secondary ml-1">{r.unit}</span></Text>
            </div>
            <div className="text-right">
              {current ? <StatusBadge tone={tone} label={`${fmtDelta(d, r.digits)} ${r.unit ?? ''}`.trim()} /> : null}
              {current && <Text variant="secondary" size={12} className="mt-1">was {fmtNum(current[r.key] as number, r.digits)}</Text>}
            </div>
          </div>
        )
      })}
    </div>
  )
}
