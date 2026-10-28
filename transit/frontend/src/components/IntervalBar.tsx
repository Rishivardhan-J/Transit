import { fmtTime } from '../lib/format'
import { cn } from './ui'

/**
 * Where the delivery window sits against the predicted arrival interval (PRD 11.4): the amber span is p10-p90,
 * the tick is the median, the vertical line is the deadline. Anything right of the line is a late risk.
 */
export function IntervalBar({ p10, p50, p90, windowStart, windowEnd }: { p10: string; p50: string; p90: string; windowStart: string; windowEnd: string }) {
  const t = (s: string) => new Date(s).getTime()
  const lo = Math.min(t(windowStart), t(p10)), hi = Math.max(t(windowEnd), t(p90))
  const span = Math.max(hi - lo, 1)
  const pct = (s: string) => `${((t(s) - lo) / span) * 100}%`
  const late = t(p90) > t(windowEnd)
  const label = `Arrival between ${fmtTime(p10)} and ${fmtTime(p90)}, median ${fmtTime(p50)}; deadline ${fmtTime(windowEnd)}${late ? ' (can be late)' : ''}`
  return (
    <div className="flex flex-col gap-2" role="img" aria-label={label}>
      <div className="relative h-6 bg-surface-dominant rounded-md border-1 border-border-default">
        <div className="absolute top-0 h-full bg-status-success-bg" style={{ left: pct(windowStart), width: `calc(${pct(windowEnd)} - ${pct(windowStart)})` }} />
        <div className={cn('absolute top-1 h-4 rounded-sm', late ? 'bg-status-warning-text' : 'bg-accent')} style={{ left: pct(p10), width: `calc(${pct(p90)} - ${pct(p10)})`, opacity: 0.6 }} />
        <div className="absolute top-0 h-full w-1 bg-text-primary" style={{ left: pct(p50) }} />
        <div className="absolute top-0 h-full w-px bg-status-error-text" style={{ left: pct(windowEnd) }} />
      </div>
      <div className="flex justify-between text-12 text-text-secondary tabular-nums">
        <span>{fmtTime(p10)} p10</span><span>{fmtTime(p50)} median</span><span>{fmtTime(p90)} p90</span>
      </div>
    </div>
  )
}
