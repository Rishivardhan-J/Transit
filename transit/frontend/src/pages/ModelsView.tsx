import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, Scatter, ScatterChart, Tooltip, XAxis, YAxis, Legend } from 'recharts'
import { api } from '../api/endpoints'
import type { Bundle } from '../api/types'
import { ChartCard, chart } from '../components/charts'
import { ShapBars } from '../components/ShapBars'
import { IntervalBar } from '../components/IntervalBar'
import { Button, Card, CardHeader, DataTable, EmptyState, Heading, QueryBoundary, Skeleton, Stat, StatusBadge, Tabs, Text, errorMessage, type Column } from '../components/ui'
import { catColors } from '../design-system/tokens'
import { fmtDateTime, fmtNum } from '../lib/format'

export function ModelsView() {
  const perf = useQuery({ queryKey: ['models'], queryFn: api.models })
  const [kind, setKind] = useState<'leg' | 'order'>('leg')
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Heading level={1} size={32}>Model performance</Heading>
          <Text variant="secondary" className="mt-1">Held-out test results, calibration and version history. Splits are chronological; no row is shuffled across time.</Text>
        </div>
        <Tabs tabs={[{ id: 'leg', label: 'Travel time (legs)' }, { id: 'order', label: 'Delivery time (orders)' }]} value={kind} onChange={setKind} />
      </div>
      <QueryBoundary query={perf} skeleton={<Skeleton className="h-map-sm w-full" />}>
        {(p) => {
          const bundles = p.bundles.filter((b) => b.kind === kind)
          const active = bundles.find((b) => b.active) ?? bundles[0]
          if (!active) return <Card><EmptyState title="No trained model" description={`Run: python -m src.models.train --dataset ${kind === 'leg' ? 'legs' : 'food'}`} /></Card>
          return <Body kind={kind} bundles={bundles} active={active} runs={p.runs.filter((r) => r.dataset === active.dataset)} />
        }}
      </QueryBoundary>
      <ShapLookup />
    </div>
  )
}

function Body({ kind, bundles, active, runs }: { kind: 'leg' | 'order'; bundles: Bundle[]; active: Bundle; runs: { run_id: string; metrics: Record<string, number>; timestamp: string }[] }) {
  const m = active.metrics
  const diag = useQuery({ queryKey: ['diag', active.version], queryFn: () => api.diagnostics(kind) })
  const compare = [
    ...Object.entries(active.baselines).map(([k, v]) => ({ model: k === 'naive_global_speed' ? 'Naive: global speed' : 'Naive: group speed', MAE: v.MAE })),
    ...Object.entries(active.comparison).map(([k, v]) => ({ model: k === 'lightgbm' ? 'LightGBM' : k === 'random_forest' ? 'Random forest' : 'XGBoost', MAE: v.MAE })),
  ]
  const history = [...runs].reverse().map((r, i) => ({ run: i + 1, MAE: r.metrics.test_MAE, RMSE: r.metrics.test_RMSE, R2: r.metrics.test_R2 }))
  const columns: Column<Bundle>[] = [
    { key: 'version', header: 'Version' },
    { key: 'created_at', header: 'Trained', render: (b) => fmtDateTime(b.created_at) },
    { key: 'mae', header: `MAE (${b0(bundles).unit})`, numeric: true, render: (b) => fmtNum(b.metrics.test_MAE) },
    { key: 'r2', header: 'R²', numeric: true, render: (b) => fmtNum(b.metrics.test_R2, 3) },
    { key: 'cov', header: '80% coverage', numeric: true, render: (b) => `${fmtNum(b.metrics.test_coverage80_cqr * 100, 1)}%` },
    { key: 'active', header: 'Status', render: (b) => <StatusBadge tone={b.active ? 'success' : 'neutral'} label={b.active ? 'Active' : 'Archived'} /> },
  ]
  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        <Stat label={`MAE (${active.unit})`} value={fmtNum(m.test_MAE)} hint={`${fmtNum(m.test_mae_lift_vs_best_naive * 100, 0)}% better than the best naive baseline`} tone="success" />
        <Stat label="R²" value={fmtNum(m.test_R2, 3)} hint={active.leakage_audit?.r2_above_0_97 ? 'Above 0.97: review SHAP for leakage' : 'Below the 0.97 leakage tripwire'} tone={active.leakage_audit?.r2_above_0_97 ? 'warning' : undefined} />
        <Stat label="80% interval coverage" value={`${fmtNum(m.test_coverage80_cqr * 100, 1)}%`} hint={`${fmtNum(m.test_coverage80_raw * 100, 1)}% before calibration`} />
        <Stat label="Test rows" value={active.rows.test.toLocaleString()} hint={`${active.rows.train.toLocaleString()} train · ${active.rows.val.toLocaleString()} validation`} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <ChartCard title="Mean absolute error vs baselines" description={`Lower is better (${active.unit}). Challengers use the same chronological test split.`}>
          <BarChart data={compare} layout="vertical" margin={{ left: 60 }}>
            <CartesianGrid stroke={chart.grid} horizontal={false} />
            <XAxis type="number" {...chart.axis} /><YAxis type="category" dataKey="model" {...chart.axis} width={130} />
            <Tooltip {...chart.tooltip} /><Bar dataKey="MAE" fill={chart.accent} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ChartCard>
        <ChartCard title="Interval calibration" description="Share of actual values inside the p10–p90 band; the target is 80%." loading={diag.isLoading} error={diag.error}>
          <BarChart data={diag.data ? [{ name: 'Raw quantile models', v: diag.data.coverage.raw * 100 }, { name: 'After calibration (CQR)', v: diag.data.coverage.calibrated * 100 }] : []}>
            <CartesianGrid stroke={chart.grid} vertical={false} />
            <XAxis dataKey="name" {...chart.axis} /><YAxis {...chart.axis} domain={[0, 100]} unit="%" />
            <Tooltip {...chart.tooltip} formatter={(v) => `${Number(v).toFixed(1)}%`} />
            <ReferenceLine y={80} stroke={chart.primary} strokeDasharray="4 4" label={{ value: 'target 80%', fill: chart.primary, fontSize: 12, position: 'insideTopRight' }} />
            <Bar dataKey="v" fill={catColors[0]} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartCard>
        <ChartCard title="Predicted vs actual" description={`${diag.data?.n ?? '…'} held-out rows. Points on the diagonal are perfect predictions.`} loading={diag.isLoading} error={diag.error}>
          <ScatterChart margin={{ left: 8, right: 8 }}>
            <CartesianGrid stroke={chart.grid} />
            <XAxis type="number" dataKey="actual" name="Actual" {...chart.axis} /><YAxis type="number" dataKey="p50" name="Predicted" {...chart.axis} />
            <Tooltip {...chart.tooltip} cursor={{ strokeDasharray: '3 3' }} />
            {diag.data && <ReferenceLine segment={[{ x: 0, y: 0 }, { x: Math.max(...diag.data.points.map((p) => p.actual)), y: Math.max(...diag.data.points.map((p) => p.actual)) }]} stroke={chart.muted} strokeDasharray="4 4" />}
            <Scatter data={diag.data?.points ?? []} fill={catColors[0]} fillOpacity={0.45} />
          </ScatterChart>
        </ChartCard>
        <ChartCard title="Residuals" description={`Actual minus predicted (${active.unit}); centred near zero means no systematic bias.`} loading={diag.isLoading} error={diag.error}>
          <BarChart data={diag.data?.residual_hist ?? []}>
            <CartesianGrid stroke={chart.grid} vertical={false} />
            <XAxis dataKey="bin" {...chart.axis} /><YAxis {...chart.axis} /><Tooltip {...chart.tooltip} />
            <Bar dataKey="count" fill={chart.accent} radius={[2, 2, 0, 0]} />
          </BarChart>
        </ChartCard>
      </div>

      {history.length > 1 && (
        <ChartCard title="Experiment history" description="Test MAE and RMSE across tracked training runs (MLflow)">
          <LineChart data={history}>
            <CartesianGrid stroke={chart.grid} vertical={false} /><XAxis dataKey="run" {...chart.axis} /><YAxis {...chart.axis} />
            <Tooltip {...chart.tooltip} /><Legend {...chart.legend} />
            <Line dataKey="MAE" stroke={chart.accent} strokeWidth={2} /><Line dataKey="RMSE" stroke={catColors[0]} strokeWidth={2} />
          </LineChart>
        </ChartCard>
      )}

      <Card><CardHeader title="Version history" description="Each training run is saved as an immutable bundle: pipeline, models, calibration and metrics together." />
        <DataTable columns={columns} data={bundles} rowKey={(b) => b.version} /></Card>
    </>
  )
}
const b0 = (b: Bundle[]) => b[0]

function ShapLookup() {
  const [id, setId] = useState('')
  const [submitted, setSubmitted] = useState('')
  const q = useQuery({ queryKey: ['explain-lookup', submitted], queryFn: () => api.explain(submitted), enabled: !!submitted, retry: 0 })
  const d = q.data
  const window = useMemo(() => (d?.arrival && d.window_end ? { s: d.arrival.p10, e: d.window_end } : null), [d])
  return (
    <Card>
      <CardHeader title="Explain a stop" description="Enter an order id from the latest plan to see its predicted arrival and what drives it." />
      <div className="p-4 flex flex-col gap-4">
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); setSubmitted(id.trim()) }}>
          <input aria-label="Order id" placeholder="e.g. ORD-5003" value={id} onChange={(e) => setId(e.target.value)}
            className="h-control-h flex-1 max-w-panel-md bg-surface-dominant border-1 border-border-default rounded-md px-3 text-14" />
          <Button type="submit" variant="outline">Explain</Button>
        </form>
        {q.isFetching && <Skeleton className="h-chart-sm w-full" />}
        {q.error && <p role="alert" className="text-14 text-status-error-text">{errorMessage(q.error)}</p>}
        {d && !q.isFetching && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="flex flex-col gap-3">
              <Text weight="medium">{d.order_id} · {d.status?.replace('_', ' ') ?? 'predicted'}</Text>
              {d.arrival && window && <IntervalBar p10={d.arrival.p10} p50={d.arrival.p50} p90={d.arrival.p90} windowStart={window.s} windowEnd={d.window_end!} />}
              <Text variant="secondary" size={12}>Leg time {fmtNum(d.p10_mins)} – {fmtNum(d.p90_mins)} min (median {fmtNum(d.p50_mins)}) · {d.model_version}</Text>
            </div>
            <ShapBars items={d.shap_values} />
          </div>
        )}
      </div>
    </Card>
  )
}
