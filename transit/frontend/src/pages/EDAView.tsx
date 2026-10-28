import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Upload } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/endpoints'
import type { UploadReport } from '../api/types'
import { BoxPlot } from '../components/BoxPlot'
import { ChartCard, chart } from '../components/charts'
import { Heatmap } from '../components/Heatmap'
import { Button, Card, CardHeader, DataTable, EmptyState, Heading, QueryBoundary, Skeleton, StatusBadge, Tabs, Text, errorMessage, toast, cn } from '../components/ui'
import { catColors } from '../design-system/tokens'

export function EDAView() {
  const [dataset, setDataset] = useState<'food' | 'legs'>('food')
  const eda = useQuery({ queryKey: ['eda', dataset], queryFn: () => api.eda(dataset) })
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Heading level={1} size={32}>Data &amp; features</Heading>
          <Text variant="secondary" className="mt-1">Validate incoming orders, then explore the data the models were trained on.</Text>
        </div>
        <Tabs tabs={[{ id: 'food', label: 'Food delivery' }, { id: 'legs', label: 'Amazon legs' }]} value={dataset} onChange={setDataset} />
      </div>
      <UploadCard />
      <QueryBoundary query={eda} skeleton={<Skeleton className="h-map-sm w-full" />}>
        {(d) => !d.summary ? <Card><EmptyState title="Dataset not available" description="Process the dataset first (python -m src.data_processing.process_food_delivery / build_amazon_legs)." /></Card> : (
          <>
            <Text variant="secondary" size={14}>{d.summary.title}: {d.summary.rows.toLocaleString()} rows analysed. Target: <span className="text-text-primary">{d.summary.target}</span></Text>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              {Object.entries(d.summary.distributions).map(([col, bins]) => (
                <ChartCard key={col} title={`Distribution: ${col}`} description="Extreme 1% tails trimmed so the bars stay readable">
                  <BarChart data={bins}>
                    <CartesianGrid stroke={chart.grid} vertical={false} />
                    <XAxis dataKey="bin" {...chart.axis} /><YAxis {...chart.axis} />
                    <Tooltip {...chart.tooltip} />
                    <Bar dataKey="count" fill={chart.accent} radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ChartCard>
              ))}
            </div>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <Card><CardHeader title="Spread and outliers" description="Box = middle half of the data, white line = median" />
                <div className="p-4 flex flex-col gap-6">{Object.entries(d.summary.boxplots).map(([k, b]) => <BoxPlot key={k} name={k} box={b} />)}</div></Card>
              <Card><CardHeader title="Correlation" description="Pearson r between numeric columns" />
                <div className="p-4"><Heatmap cells={d.summary.correlation} labels={Object.keys(d.summary.boxplots)} /></div></Card>
            </div>
            {d.summary.traffic_vs_time && (
              <ChartCard title={dataset === 'legs' ? 'Median leg time by departure hour (UTC)' : 'Median delivery time by traffic level'}>
                <LineChart data={d.summary.traffic_vs_time}>
                  <CartesianGrid stroke={chart.grid} vertical={false} />
                  <XAxis dataKey={dataset === 'legs' ? 'hour' : 'traffic'} {...chart.axis} /><YAxis {...chart.axis} />
                  <Tooltip {...chart.tooltip} />
                  <Line dataKey="median" stroke={chart.accent} strokeWidth={2} dot />
                </LineChart>
              </ChartCard>
            )}
            {d.importance && (
              <ChartCard title="Feature importance: impurity vs permutation" height="h-map-sm"
                description={`Share of total, model ${d.importance.version}. Rank agreement (Spearman) ${d.importance.spearman.toFixed(2)}: where the two disagree, trust permutation.`}>
                <BarChart data={d.importance.features.slice(0, 10)} layout="vertical" margin={{ left: 80 }}>
                  <CartesianGrid stroke={chart.grid} horizontal={false} />
                  <XAxis type="number" {...chart.axis} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} /><YAxis type="category" dataKey="feature" {...chart.axis} width={110} />
                  <Tooltip {...chart.tooltip} formatter={(v) => `${(Number(v) * 100).toFixed(1)}%`} /><Legend {...chart.legend} />
                  <Bar dataKey="permutation" name="Permutation" fill={chart.accent} /><Bar dataKey="impurity" name="Impurity (gain)" fill={catColors[0]} />
                </BarChart>
              </ChartCard>
            )}
          </>
        )}
      </QueryBoundary>
    </div>
  )
}

function UploadCard() {
  const qc = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [drag, setDrag] = useState(false)
  const [report, setReport] = useState<UploadReport | null>(null)
  const validate = useMutation({ mutationFn: (f: File) => api.upload(f, false), onSuccess: setReport })
  const commit = useMutation({
    mutationFn: (f: File) => api.upload(f, true),
    onSuccess: (r) => { setReport(r); toast('success', `Imported ${r.created} orders.`); void qc.invalidateQueries() },
    onError: (e) => toast('error', errorMessage(e)),
  })
  const pick = (f: File | undefined) => { if (f) { setFile(f); setReport(null); validate.mutate(f) } }

  return (
    <Card>
      <CardHeader title="Upload orders" description="CSV or Parquet. Every row is checked; problems are reported by row and field, never dropped silently." />
      <div className="p-4 flex flex-col gap-4">
        <div role="button" tabIndex={0} aria-label="Choose or drop an orders file"
          onClick={() => input.current?.click()} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') input.current?.click() }}
          onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]) }}
          className={cn('flex flex-col items-start gap-2 p-6 border-1 border-dashed rounded-md cursor-pointer transition-colors duration-150', drag ? 'border-accent bg-surface-dominant' : 'border-border-default hover:border-border-hover')}>
          <Upload className="h-icon-lg w-icon-lg text-text-muted" aria-hidden />
          <Text weight="medium">{file ? file.name : 'Drop a file here or click to browse'}</Text>
          <Text variant="muted" size={12}>Required columns: order_id, pickup/delivery lat+lng, demand_weight, time_window_start/end, service_time_minutes, created_at</Text>
          <input ref={input} type="file" accept=".csv,.parquet" className="hidden" onChange={(e) => pick(e.target.files?.[0])} />
        </div>
        {validate.isPending && <Skeleton className="h-8 w-full" />}
        {validate.error && <p role="alert" className="text-14 text-status-error-text">{errorMessage(validate.error)}</p>}
        {report && (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone="neutral" label={`${report.total} rows`} />
              <StatusBadge tone="success" label={`${report.valid} valid`} />
              <StatusBadge tone={report.error_count ? 'error' : 'success'} label={`${report.error_count} problems`} />
              {report.committed && <StatusBadge tone="success" label={`${report.created} imported`} />}
              {!report.committed && report.valid > 0 && file && <Button className="ml-auto" loading={commit.isPending} onClick={() => commit.mutate(file)}>Import {report.valid} valid rows</Button>}
            </div>
            {report.errors.length > 0 && (
              <div className="border-1 border-border-default rounded-md max-h-chart overflow-auto">
                <DataTable data={report.errors} rowKey={(e, i) => `${e.row_index}-${e.field}-${i}`}
                  columns={[{ key: 'row_index', header: 'File row', numeric: true, render: (e) => e.row_index + 2 }, { key: 'field', header: 'Field' }, { key: 'message', header: 'Problem' }]} />
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
