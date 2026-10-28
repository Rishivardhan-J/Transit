import { useQuery } from '@tanstack/react-query'
import { api } from '../api/endpoints'
import type { Plan, Stop } from '../api/types'
import { fmtDateTime, fmtTime } from '../lib/format'
import { Card, CardHeader, ErrorState, PlanStatusBadge, QueryBoundary, Skeleton, Text } from './ui'
import { IntervalBar } from './IntervalBar'
import { ShapBars } from './ShapBars'

/** Why-is-this-stop-flagged panel: order facts, arrival interval vs window, and the model's top drivers (PRD 11.4). */
export function StopDetail({ plan, orderId }: { plan: Plan; orderId: string }) {
  const stop: (Stop & { vehicle_id: string; n: number }) | undefined = plan.routes.flatMap((r) => r.stops.map((s) => ({ ...s, vehicle_id: r.vehicle_id, n: r.stops.length }))).find((s) => s.order_id === orderId)
  const unassigned = plan.unassigned.find((u) => u.order_id === orderId)
  const explain = useQuery({ queryKey: ['explain', plan.run_id, orderId], queryFn: () => api.explain(orderId), enabled: !!stop })

  if (unassigned) {
    return (
      <div className="p-4 flex flex-col gap-3">
        <PlanStatusBadge status="unassigned" />
        <Text weight="medium">{orderId}</Text>
        <Text variant="secondary">Not placed on any route: {unassigned.reason}.</Text>
      </div>
    )
  }
  if (!stop) return <ErrorState error="This order is not part of the selected plan." title="Stop not found" />

  return (
    <div className="p-4 flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-2">
          <Text weight="semibold" size={16}>{stop.order_id}</Text>
          <PlanStatusBadge status={stop.status} />
        </div>
        <Text variant="secondary" size={12}>Vehicle {stop.vehicle_id} · stop {explain.data?.stop_index !== undefined ? explain.data.stop_index + 1 : '—'} of {stop.n} · {stop.priority} priority</Text>
        <Text variant="secondary" size={12}>Window {fmtTime(stop.window_start)} – {fmtTime(stop.window_end)} · planned {fmtTime(stop.planned_arrival)}</Text>
      </div>

      {stop.p10 && stop.p50 && stop.p90 && (
        <section className="flex flex-col gap-2">
          <Text weight="medium">Predicted arrival (80% interval)</Text>
          <IntervalBar p10={stop.p10} p50={stop.p50} p90={stop.p90} windowStart={stop.window_start} windowEnd={stop.window_end} />
          {stop.status !== 'on_time' && (
            <Text variant="secondary" size={12}>
              {stop.status === 'late' ? 'The median arrival is already after the deadline.' : `There is a real chance of arriving after ${fmtTime(stop.window_end)}: the p90 arrival is ${fmtTime(stop.p90)}.`}
            </Text>
          )}
        </section>
      )}

      <section className="flex flex-col gap-3">
        <Text weight="medium">What drives the travel time into this stop</Text>
        <QueryBoundary query={explain} skeleton={<Skeleton className="h-chart-sm w-full" />}>
          {(d) => (
            <>
              {d.leg_minutes && <Text variant="secondary" size={12}>Leg: {d.leg_minutes.p10.toFixed(1)} – {d.leg_minutes.p90.toFixed(1)} min (median {d.leg_minutes.p50.toFixed(1)})</Text>}
              <ShapBars items={d.shap_values} />
              <Text variant="muted" size={12}>Model {d.model_version}. Amber lengthens the leg, blue shortens it.</Text>
            </>
          )}
        </QueryBoundary>
      </section>
    </div>
  )
}

export function StopDetailCard({ plan, orderId, onClose }: { plan: Plan; orderId: string; onClose: () => void }) {
  return (
    <Card className="w-panel-md max-w-full max-h-full overflow-auto">
      <CardHeader title="Stop detail" description={fmtDateTime(plan.created_at)} actions={<button className="text-12 text-text-secondary hover:text-text-primary" onClick={onClose}>Close</button>} />
      <StopDetail plan={plan} orderId={orderId} />
    </Card>
  )
}
