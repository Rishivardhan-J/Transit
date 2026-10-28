import { Text } from './ui'
import { fmtNum } from '../lib/format'

interface Box { min: number; q1: number; median: number; q3: number; max: number; outliers: number; n: number }

/** One horizontal box plot per variable (whiskers = last point inside 1.5×IQR), with the numbers printed alongside. */
export function BoxPlot({ name, box }: { name: string; box: Box }) {
  const span = box.max - box.min || 1
  const pos = (v: number) => ((v - box.min) / span) * 100
  return (
    <div className="flex flex-col gap-1" role="img" aria-label={`${name}: median ${fmtNum(box.median)}, middle half ${fmtNum(box.q1)} to ${fmtNum(box.q3)}, ${box.outliers} outliers`}>
      <div className="flex justify-between"><Text size={14} weight="medium">{name}</Text><Text size={12} variant="muted">{box.outliers.toLocaleString()} outliers of {box.n.toLocaleString()}</Text></div>
      <svg viewBox="0 0 100 10" preserveAspectRatio="none" className="w-full h-6" aria-hidden>
        <line x1={pos(box.min)} x2={pos(box.max)} y1="5" y2="5" stroke="#64748B" strokeWidth="0.6" vectorEffect="non-scaling-stroke" />
        <rect x={pos(box.q1)} y="1.5" width={Math.max(pos(box.q3) - pos(box.q1), 0.5)} height="7" fill="rgba(245,158,11,0.35)" stroke="#F59E0B" strokeWidth="0.6" vectorEffect="non-scaling-stroke" />
        <line x1={pos(box.median)} x2={pos(box.median)} y1="1.5" y2="8.5" stroke="#F1F5F9" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="flex justify-between text-12 text-text-secondary tabular-nums"><span>{fmtNum(box.min)}</span><span>Q1 {fmtNum(box.q1)}</span><span>median {fmtNum(box.median)}</span><span>Q3 {fmtNum(box.q3)}</span><span>{fmtNum(box.max)}</span></div>
    </div>
  )
}
