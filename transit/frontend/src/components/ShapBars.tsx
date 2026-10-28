import { cn, Text } from './ui'

/** Signed contributions in minutes: amber pushes the arrival later, blue pulls it earlier. Text is always shown. */
export function ShapBars({ items }: { items: { feature: string; value: number; text?: string }[] }) {
  if (!items.length) return <Text variant="secondary" size={12}>No attribution available for this stop.</Text>
  const max = Math.max(...items.map((i) => Math.abs(i.value)), 0.001)
  return (
    <ul className="flex flex-col gap-3">
      {items.map((it) => {
        const w = `${(Math.abs(it.value) / max) * 50}%`
        return (
          <li key={it.feature} className="flex flex-col gap-1">
            <div className="flex items-baseline justify-between gap-2">
              <Text size={14}>{it.text ?? it.feature}</Text>
              <Text size={12} variant="secondary" className="tabular-nums shrink-0">{it.value > 0 ? '+' : ''}{it.value.toFixed(2)} min</Text>
            </div>
            <div className="relative h-2 bg-surface-dominant rounded-full" aria-hidden>
              <div className="absolute top-0 h-full w-px bg-border-hover left-1/2" />
              <div className={cn('absolute top-0 h-full rounded-full', it.value >= 0 ? 'bg-accent' : 'bg-cat-1')}
                style={it.value >= 0 ? { left: '50%', width: w } : { right: '50%', width: w }} />
            </div>
          </li>
        )
      })}
    </ul>
  )
}
