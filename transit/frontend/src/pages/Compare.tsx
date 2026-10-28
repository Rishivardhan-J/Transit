import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from 'recharts'
import { Play } from 'lucide-react'
import { api } from '../api/endpoints'
import type { BenchmarkRow, Metrics, SolverRow } from '../api/types'
import { ChartCard, chart } from '../components/charts'
import { Button, Card, CardHeader, DataTable, EmptyState, Heading, QueryBoundary, Skeleton, StatusBadge, Tabs, Text, errorMessage, type Column } from '../components/ui'
import { catColors } from '../design-system/tokens'
import { fmtNum, fmtPct } from '../lib/format'
import { PRESETS } from '../lib/weights'
import { canUseResearch, useAuthStore } from '../store/authStore'

const SOLVER_NAME: Record<string, string> = { hgs: 'HGS', ortools: 'OR-Tools', nn: 'Nearest neighbour' }
const SOLVER_COLOR: Record<string, string> = { hgs: '#F59E0B', ortools: catColors[0], nn: catColors[1] }

export function Compare() {
  const role = useAuthStore((s) => s.role)
  const [tab, setTab] = useState<'latest' | 'benchmark'>('latest')
  const bench = useQuery({ queryKey: ['benchmarks'], queryFn: api.benchmarks, enabled: tab === 'benchmark' })
  const plan = useQuery({ queryKey: ['plan', 'latest'], queryFn: api.latestPlan })
  const live = useMutation({ mutationFn: () => api.compareLive(PRESETS.balanced, 10) })

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Heading level={1} size={32}>Baseline vs HGS</Heading>
          <Text variant="secondary" className="mt-1">Same orders, same cost weights, three solvers. Every solution is re-checked for capacity and time-window violations.</Text>
        </div>
        <Tabs tabs={[{ id: 'latest', label: 'Current orders' }, { id: 'benchmark', label: 'Solomon benchmark' }]} value={tab} onChange={setTab} />
      </div>

      {tab === 'latest' ? (
        <>
          <QueryBoundary query={plan} skeleton={<Skeleton className="h-chart w-full" />}>
            {(p) => p?.metrics ? <LatestVsBaseline hgs={p.metrics} nn={p.baseline_metrics ?? null} solver={p.solver} /> : <Card><EmptyState title="No plan yet" description="Run an optimization to compare it with the nearest-neighbour baseline." /></Card>}
          </QueryBoundary>
          {canUseResearch(role) && (
            <Card>
              <CardHeader title="Run all three solvers now" description="Researcher tool: re-solves the current orders with Nearest Neighbour, OR-Tools and HGS (about 30 s)."
                actions={<Button loading={live.isPending} icon={<Play className="h-icon w-icon" aria-hidden />} onClick={() => live.mutate()}>Run comparison</Button>} />
              {live.error && <p role="alert" className="p-4 text-14 text-status-error-text">{errorMessage(live.error)}</p>}
              {live.data && <SolverTable rows={live.data.solvers} />}
            </Card>
          )}
        </>
      ) : (
        <QueryBoundary query={bench} skeleton={<Skeleton className="h-chart w-full" />}>{(rows) => <Benchmark rows={rows} />}</QueryBoundary>
      )}
    </div>
  )
}

function LatestVsBaseline({ hgs, nn, solver }: { hgs: Metrics; nn: Metrics | null; solver: string }) {
  const rows: SolverRow[] = [
    ...(nn ? [{ solver: 'nn', ...pick(nn) }] : []),
    { solver, ...pick(hgs) },
  ]
  const saving = nn && nn.cost_per_order && hgs.cost_per_order ? ((hgs.cost_per_order - nn.cost_per_order) / nn.cost_per_order) * 100 : null
  return (
    <div className="flex flex-col gap-6">
      {saving !== null && (
        <Card className="p-4 flex flex-row items-center gap-4">
          <StatusBadge tone={saving <= 0 ? 'success' : 'warning'} label={`${fmtPct(saving)} cost per order`} />
          <Text variant="secondary">{SOLVER_NAME[solver] ?? solver} versus the nearest-neighbour baseline on the same problem.{nn && nn.orders_unassigned > 0 ? ` The baseline left ${nn.orders_unassigned} orders unrouted.` : ''}</Text>
        </Card>
      )}
      <MetricBars rows={rows} />
      <Card><CardHeader title="Detail" /><SolverTable rows={rows} /></Card>
    </div>
  )
}

const pick = (m: Metrics) => ({ total_distance: m.total_distance, total_time_min: m.total_time_min, total_cost: m.total_cost, vehicles_used: m.vehicles_used, predicted_late: m.predicted_late ?? 0, late_deliveries: m.late_deliveries, utilization_pct: m.utilization_pct, orders_assigned: m.orders_assigned, orders_unassigned: m.orders_unassigned, runtime_s: m.runtime_s ?? 0, feasible: m.feasible })

function SolverTable({ rows }: { rows: SolverRow[] }) {
  const columns: Column<SolverRow>[] = [
    { key: 'solver', header: 'Solver', render: (r) => SOLVER_NAME[r.solver] ?? r.solver },
    { key: 'total_distance', header: 'Distance', numeric: true, render: (r) => fmtNum(r.total_distance) },
    { key: 'total_time_min', header: 'Time (min)', numeric: true, render: (r) => fmtNum(r.total_time_min, 0) },
    { key: 'predicted_late', header: 'At risk', numeric: true },
    { key: 'utilization_pct', header: 'Utilization', numeric: true, render: (r) => `${fmtNum(r.utilization_pct, 0)}%` },
    { key: 'vehicles_used', header: 'Vehicles', numeric: true },
    { key: 'orders_unassigned', header: 'Unassigned', numeric: true },
    { key: 'total_cost', header: 'Cost', numeric: true, render: (r) => fmtNum(r.total_cost) },
    { key: 'feasible', header: 'Constraints', render: (r) => <StatusBadge tone={r.feasible ? 'success' : 'error'} label={r.feasible ? 'No violations' : 'Violations'} /> },
  ]
  return <DataTable columns={columns} data={rows} rowKey={(r) => r.solver} />
}

function MetricBars({ rows }: { rows: SolverRow[] }) {
  const metrics: [keyof SolverRow, string][] = [['total_distance', 'Distance'], ['total_time_min', 'Time (min)'], ['predicted_late', 'At risk'], ['total_cost', 'Cost']]
  const data = metrics.map(([k, label]) => ({ metric: label, ...Object.fromEntries(rows.map((r) => [r.solver, Number(r[k])])) }))
  return (
    <ChartCard title="Solver comparison" description="Lower is better on every metric shown">
      <BarChart data={data}>
        <CartesianGrid stroke={chart.grid} vertical={false} />
        <XAxis dataKey="metric" {...chart.axis} /><YAxis {...chart.axis} />
        <Tooltip {...chart.tooltip} /><Legend {...chart.legend} formatter={(v) => SOLVER_NAME[String(v)] ?? v} />
        {rows.map((r) => <Bar key={r.solver} dataKey={r.solver} fill={SOLVER_COLOR[r.solver] ?? catColors[2]} radius={[4, 4, 0, 0]} />)}
      </BarChart>
    </ChartCard>
  )
}

function Benchmark({ rows }: { rows: BenchmarkRow[] }) {
  const data = rows.map((r) => ({ instance: r.Instance, hgs: +r.HGS_Gap.toFixed(2), ortools: +r.ORT_Gap.toFixed(2), nn: +r.NN_Gap.toFixed(1) }))
  const columns: Column<BenchmarkRow>[] = [
    { key: 'Instance', header: 'Instance' },
    { key: 'Best_Known_Dist', header: 'Best known', numeric: true, render: (r) => `${fmtNum(r.Best_Known_Dist, 2)} (${r.Best_Known_Veh} veh)` },
    { key: 'HGS_Dist', header: 'HGS', numeric: true, render: (r) => `${fmtNum(r.HGS_Dist, 2)} (${r.HGS_Veh} veh)` },
    { key: 'HGS_Gap', header: 'HGS gap', numeric: true, render: (r) => fmtPct(r.HGS_Gap, 2) },
    { key: 'ORT_Dist', header: 'OR-Tools', numeric: true, render: (r) => `${fmtNum(r.ORT_Dist, 2)} (${r.ORT_Veh} veh)` },
    { key: 'ORT_Gap', header: 'OR-Tools gap', numeric: true, render: (r) => fmtPct(r.ORT_Gap, 2) },
    { key: 'NN_Unassigned', header: 'NN unrouted', numeric: true },
    { key: 'viol', header: 'Violations', numeric: true, render: (r) => r.HGS_Viol + r.ORT_Viol + r.NN_Viol },
  ]
  return (
    <div className="flex flex-col gap-6">
      <ChartCard title="Distance gap to best-known solution" description="Solomon 100-customer instances, lower is better. NN gaps can look small only because it leaves orders unrouted (see table).">
        <BarChart data={data}>
          <CartesianGrid stroke={chart.grid} vertical={false} />
          <XAxis dataKey="instance" {...chart.axis} /><YAxis {...chart.axis} unit="%" />
          <Tooltip {...chart.tooltip} /><Legend {...chart.legend} formatter={(v) => SOLVER_NAME[String(v)] ?? v} />
          <Bar dataKey="hgs" fill={SOLVER_COLOR.hgs} radius={[4, 4, 0, 0]} /><Bar dataKey="ortools" fill={SOLVER_COLOR.ortools} radius={[4, 4, 0, 0]} /><Bar dataKey="nn" fill={SOLVER_COLOR.nn} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ChartCard>
      <Card><CardHeader title="Benchmark detail" description="Vehicles first, then distance, as in the standard VRPTW ranking" /><DataTable columns={columns} data={rows} rowKey={(r) => r.Instance} /></Card>
    </div>
  )
}
