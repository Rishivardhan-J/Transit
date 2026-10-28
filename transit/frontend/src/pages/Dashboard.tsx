import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Map as MapIcon } from 'lucide-react'
import { api } from '../api/endpoints'
import { wsUrl } from '../api/client'
import { useLiveChannel } from '../hooks/useLiveChannel'
import { MapCanvas } from '../map/MapCanvas'
import { Card, CardHeader, DataTable, EmptyState, ErrorState, Heading, PlanStatusBadge, QueryBoundary, Skeleton, Stat, StatusBadge, Text, type Column } from '../components/ui'
import { fmtNum, fmtPct, fmtTime } from '../lib/format'
import { vehicleColor } from '../design-system/tokens'
import type { Plan } from '../api/types'

interface VehicleRow { vehicle_id: string; capacity: number; stops: number; distance: number; load: number; colorIdx: number }

export function Dashboard() {
  const nav = useNavigate()
  const qc = useQueryClient()
  const kpis = useQuery({ queryKey: ['kpis'], queryFn: api.kpis, refetchInterval: 15000 })
  const plan = useQuery({ queryKey: ['plan', 'latest'], queryFn: api.latestPlan, refetchInterval: 30000 })
  const vehicles = useQuery({ queryKey: ['vehicles'], queryFn: api.vehicles })
  const [selected, setSelected] = useState<string | null>(null)

  useLiveChannel({ url: plan.data ? wsUrl(`/ws/routes/${plan.data.run_id}`) : null, onMessage: () => { void qc.invalidateQueries() } })

  const rows: VehicleRow[] = useMemo(() => {
    const byVehicle = new Map((plan.data?.routes ?? []).map((r) => [r.vehicle_id, r]))
    const order = [...byVehicle.keys()].sort()
    return (vehicles.data ?? []).map((v) => {
      const r = byVehicle.get(v.vehicle_id)
      return { vehicle_id: v.vehicle_id, capacity: v.capacity, stops: r?.stops.length ?? 0, distance: r?.total_distance_km ?? 0, load: 0, colorIdx: Math.max(0, order.indexOf(v.vehicle_id)) }
    })
  }, [plan.data, vehicles.data])

  const attention = useMemo(() => attentionList(plan.data ?? null), [plan.data])
  const k = kpis.data
  const costTone = k?.cost_vs_baseline_pct == null ? undefined : k.cost_vs_baseline_pct <= 0 ? 'success' : 'warning'

  const columns: Column<VehicleRow>[] = [
    { key: 'vehicle_id', header: 'Vehicle', render: (r) => (
      <span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-full" style={{ background: vehicleColor(r.colorIdx), opacity: r.stops ? 1 : 0.4 }} aria-hidden />{r.vehicle_id}</span>) },
    { key: 'stops', header: 'Stops', numeric: true },
    { key: 'distance', header: 'km', numeric: true, render: (r) => fmtNum(r.distance) },
    { key: 'status', header: 'Status', render: (r) => <StatusBadge tone={r.stops ? 'success' : 'neutral'} label={r.stops ? 'Active' : 'Idle'} /> },
  ]

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <Heading level={1} size={32}>Operations overview</Heading>
        {k?.latest_run && <Text variant="secondary" size={12}>Plan {k.latest_run.id.slice(0, 8)} · {k.latest_run.solver.toUpperCase()} · {k.latest_run.time_model?.startsWith('leg_') ? 'ML travel times' : 'speed-profile times'}</Text>}
      </div>

      {kpis.error ? <Card><ErrorState error={kpis.error} onRetry={() => kpis.refetch()} /></Card> : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
          {kpis.isLoading || !k ? Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-24 w-full" />) : (<>
            <Stat label="Fleet utilization" value={`${fmtNum(k.fleet_utilization_pct, 0)}%`} hint={`${rows.filter((r) => r.stops).length} of ${rows.length} vehicles on a route`} />
            <Stat label="Active routes" value={k.active_routes} hint={k.latest_run ? `${k.latest_run.unassigned} ${k.latest_run.unassigned === 1 ? 'order' : 'orders'} unassigned` : 'No plan yet'} />
            <Stat label="Predicted late" value={k.predicted_late} hint={k.predicted_late ? 'p90 arrival after the deadline' : 'All stops on track'} tone={k.predicted_late ? 'warning' : 'success'} />
            <Stat label="Cost vs baseline" value={fmtPct(k.cost_vs_baseline_pct)} hint={k.cost_vs_baseline_pct == null ? 'Run an optimization' : `per order vs ${k.baseline}`} tone={costTone} />
          </>)}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <Heading level={2} size={20}>Active routes</Heading>
            <button onClick={() => nav('/map')} className="inline-flex items-center gap-1 text-14 text-accent hover:opacity-80"><MapIcon className="h-icon w-icon" aria-hidden />Open full map</button>
          </div>
          {plan.isLoading ? <Skeleton className="h-map-md w-full" /> : plan.error ? <Card><ErrorState error={plan.error} onRetry={() => plan.refetch()} /></Card> : plan.data
            ? <MapCanvas plan={plan.data} selectedOrderId={selected} onStopClick={(id) => { setSelected(id); nav(`/map?order=${id}`) }} className="h-map-md" />
            : <Card className="h-map-md justify-center"><EmptyState title="No plan yet" description="Use “Run optimization” to build routes from the current orders." /></Card>}
        </div>

        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader title="Fleet" description="From the latest plan" />
            <QueryBoundary query={vehicles} skeleton={<Skeleton className="h-chart m-4" />}>{() => <DataTable columns={columns} data={rows} rowKey={(r) => r.vehicle_id} empty="No vehicles registered" />}</QueryBoundary>
          </Card>
          <Card>
            <CardHeader title="Model" description="Test-set quality of the active models" />
            <div className="p-4 flex flex-col gap-3">
              {kpis.isLoading ? <Skeleton className="h-16 w-full" /> : !k?.model.leg && !k?.model.order ? <Text variant="secondary">No trained model found.</Text> : (<>
                {k?.model.leg && <ModelLine title="Travel-time (leg)" m={k.model.leg} />}
                {k?.model.order && <ModelLine title="Delivery-time (order)" m={k.model.order} />}
              </>)}
            </div>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader title="Needs attention" description="Stops the model expects to miss their window, and orders that could not be routed" />
        {attention.length === 0 ? <EmptyState icon={AlertTriangle} title="Nothing needs attention" description="No stop is predicted to be late and every order is on a route." /> : (
          <ul className="divide-y-1 divide-border-default">
            {attention.map((a) => (
              <li key={a.id}>
                <button onClick={() => nav(`/map?order=${a.id}`)} className="w-full flex flex-wrap items-center justify-between gap-3 p-4 text-left hover:bg-surface-dominant/50">
                  <span className="flex items-center gap-3"><PlanStatusBadge status={a.status} /><Text weight="medium">{a.id}</Text></span>
                  <Text variant="secondary" size={12}>{a.detail}</Text>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

function ModelLine({ title, m }: { title: string; m: { version: string; unit: string; mae: number; r2: number; coverage80: number } }) {
  return (
    <div className="flex flex-col gap-1">
      <Text weight="medium">{title}</Text>
      <Text variant="secondary" size={12}>MAE {fmtNum(m.mae)} {m.unit} · R² {fmtNum(m.r2, 3)} · 80% interval covers {fmtNum(m.coverage80 * 100, 0)}%</Text>
      <Text variant="muted" size={12}>{m.version}</Text>
    </div>
  )
}

function attentionList(plan: Plan | null) {
  if (!plan) return []
  const stops = plan.routes.flatMap((r) => r.stops.filter((s) => s.status !== 'on_time').map((s) => ({
    id: s.order_id, status: s.status as 'late' | 'at_risk' | 'unassigned',
    detail: `${r.vehicle_id} · deadline ${fmtTime(s.window_end)} · p90 arrival ${fmtTime(s.p90)}` })))
  const un = plan.unassigned.map((u) => ({ id: u.order_id, status: 'unassigned' as const, detail: u.reason }))
  return [...stops, ...un]
}
