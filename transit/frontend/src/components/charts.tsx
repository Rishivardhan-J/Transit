import type { ReactNode } from 'react'
import { ResponsiveContainer } from 'recharts'
import { colors } from '../design-system/tokens'
import { Card, CardHeader, ErrorState, Skeleton } from './ui'

/** Shared recharts styling so every chart reads as part of one system (tokens only, no inline hex). */
export const chart = {
  axis: { stroke: colors.border.default, tick: { fill: colors.text.secondary, fontSize: 12 } },
  grid: colors.border.default,
  tooltip: {
    contentStyle: { background: colors.surface.secondary, border: `1px solid ${colors.border.default}`, borderRadius: 8, color: colors.text.primary, fontSize: 12 },
    itemStyle: { color: colors.text.primary }, labelStyle: { color: colors.text.secondary }, cursor: { fill: colors.border.default, opacity: 0.3 },
  },
  legend: { wrapperStyle: { fontSize: 12, color: colors.text.secondary } },
  accent: colors.accent, primary: colors.text.primary, muted: colors.text.muted,
}

/** Fixed-height frame: a ResponsiveContainer inside an unsized parent collapses to zero, so the height is explicit. */
export function ChartCard({ title, description, loading, error, height = 'h-chart', actions, children }:
  { title: string; description?: string; loading?: boolean; error?: unknown; height?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <Card>
      <CardHeader title={title} description={description} actions={actions} />
      <div className={`p-4 ${height}`}>
        {loading ? <Skeleton className="h-full w-full" /> : error ? <ErrorState error={error} /> : <ResponsiveContainer width="100%" height="100%">{children as React.ReactElement}</ResponsiveContainer>}
      </div>
    </Card>
  )
}
