import { colors, catColors } from '../design-system/tokens'
import { Text } from './ui'

const rgba = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${a})`
}

/** Correlation matrix as a grid. Positive = amber, negative = blue; intensity = |r|. Every cell prints its value. */
export function Heatmap({ cells, labels }: { cells: { x: string; y: string; value: number }[]; labels: string[] }) {
  const get = (x: string, y: string) => cells.find((c) => c.x === x && c.y === y)?.value ?? 0
  return (
    <div className="overflow-x-auto">
      <div className="grid gap-1 min-w-panel-md" style={{ gridTemplateColumns: `minmax(96px, auto) repeat(${labels.length}, minmax(48px, 1fr))` }}>
        <div />
        {labels.map((l) => <Text key={l} size={12} variant="secondary" className="text-center truncate" title={l}>{l}</Text>)}
        {labels.map((row) => (
          <div key={row} className="contents">
            <Text size={12} variant="secondary" className="truncate pr-2" title={row}>{row}</Text>
            {labels.map((col) => {
              const v = get(col, row)
              return (
                <div key={col} title={`${row} × ${col}: ${v.toFixed(2)}`} className="h-8 rounded-sm flex items-center justify-center text-12 tabular-nums"
                  style={{ background: rgba(v >= 0 ? colors.accent : catColors[0], 0.15 + 0.85 * Math.abs(v)), color: Math.abs(v) > 0.6 ? colors.surface.dominant : colors.text.primary }}>
                  {v.toFixed(2)}
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
