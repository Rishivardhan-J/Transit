import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Pause, Play } from 'lucide-react'
import { Bar, BarChart, Cell, CartesianGrid, ReferenceLine, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/endpoints'
import type { Plan, Replay as ReplayData, Stop } from '../api/types'
import { ChartCard, chart } from '../components/charts'
import { Button, Card, EmptyState, ErrorState, Heading, Skeleton, Stat, Tabs, Text } from '../components/ui'
import { statusStyle } from '../design-system/tokens'
import { MapCanvas } from '../map/MapCanvas'
import { fmtNum } from '../lib/format'

const SPEEDS = ['1', '4', '16'] as const   // simulated minutes per real second
const ms = (iso: string) => new Date(iso).getTime()

export function Replay() {
  const latest = useQuery({ queryKey: ['plan', 'latest'], queryFn: api.latestPlan })
  const runId = latest.data?.run_id
  const replay = useQuery({ queryKey: ['replay', runId], queryFn: () => api.replay(runId!), enabled: !!runId })

  if (latest.isLoading || replay.isLoading) return <Skeleton className="h-map-lg w-full" />
  if (latest.error || replay.error) return <Card><ErrorState error={latest.error ?? replay.error} /></Card>
  if (!replay.data || !replay.data.routes.length) return <Card><EmptyState title="Nothing to replay" description="Run an optimization first; the replay shows planned versus simulated arrivals for that plan." /></Card>
  return <ReplayBody data={replay.data} />
}

function ReplayBody({ data }: { data: ReplayData }) {
  const all = data.routes.flatMap((r) => r.stops)
  const [start, end] = useMemo(() => [Math.min(...all.map((s) => Math.min(ms(s.planned), ms(s.actual)))) - 15 * 60000, Math.max(...all.map((s) => Math.max(ms(s.planned), ms(s.actual)))) + 10 * 60000], [all])
  const [t, setT] = useState(start)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>('4')
  const last = useRef(0)

  useEffect(() => {
    if (!playing) return
    let raf = 0
    last.current = performance.now()
    const tick = (now: number) => {
      const dt = now - last.current; last.current = now
      setT((cur) => { const nx = cur + dt * Number(speed) * 60; if (nx >= end) { setPlaying(false); return end } return nx })
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing, speed, end])

  const { plan, trucks, visited, lateSoFar } = useMemo(() => {
    let visited = 0, lateSoFar = 0
    const routes = data.routes.map((r) => ({
      route_id: r.route_id, vehicle_id: r.vehicle_id, total_distance_km: 0, total_time_min: 0, total_cost: 0,
      stops: r.stops.map((s): Stop => {
        const done = ms(s.actual) <= t
        if (done) { visited++; if (s.late) lateSoFar++ }
        return { order_id: s.order_id, lat: s.lat ?? 0, lng: s.lng ?? 0, priority: '', planned_arrival: s.planned, p10: null, p50: null, p90: null,
          window_start: s.planned, window_end: s.window_end, slack_min: null, status: !done ? 'pending' : s.late ? 'late' : 'on_time' }
      }),
    }))
    const trucks = data.routes.map((r) => {
      const pts = r.stops.filter((s) => s.lat !== null && s.lng !== null)
      const depot = data.depot ?? { lat: pts[0]?.lat ?? 0, lng: pts[0]?.lng ?? 0 }
      let pos = { lat: depot.lat, lng: depot.lng }
      for (let i = 0; i < pts.length; i++) {
        const a = ms(pts[i].actual)
        if (t < a) {
          const prevT = i === 0 ? a - 10 * 60000 : ms(pts[i - 1].actual)
          const from = i === 0 ? depot : { lat: pts[i - 1].lat!, lng: pts[i - 1].lng! }
          const f = Math.min(1, Math.max(0, (t - prevT) / (a - prevT)))
          pos = { lat: from.lat + (pts[i].lat! - from.lat) * f, lng: from.lng + (pts[i].lng! - from.lng) * f }
          break
        }
        pos = { lat: pts[i].lat!, lng: pts[i].lng! }
      }
      return { vehicle_id: r.vehicle_id, ...pos }
    })
    const plan: Plan = { run_id: data.run_id, solver: 'replay', time_model: null, depot: data.depot, routes, unassigned: [] }
    return { plan, trucks, visited, lateSoFar }
  }, [data, t])

  const errors = useMemo(() => [...all].sort((a, b) => ms(a.planned) - ms(b.planned)).map((s, i) => ({ i: i + 1, order: s.order_id, error: s.error_min, late: s.late })), [all])
  const clock = new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Heading level={1} size={32}>Replay</Heading>
        <Text variant="secondary" className="mt-1">Planned versus simulated arrivals for the latest plan. There is no live GPS in v1: actual times are drawn from each leg’s predicted p10–p90 range, reproducibly.</Text>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        <Stat label="Stops completed" value={`${visited} / ${data.summary.stops}`} />
        <Stat label="Late so far" value={lateSoFar} hint={`${data.summary.actual_late} by end of day`} tone={lateSoFar ? 'warning' : 'success'} />
        <Stat label="Planned late" value={data.summary.planned_late} hint="Stops the plan itself already schedules late" />
        <Stat label="Mean abs. error" value={`${fmtNum(data.summary.mae_min)} min`} hint="Actual vs planned arrival" />
      </div>

      <div className="relative">
        <MapCanvas plan={plan} vehicles={trucks} className="h-map-lg" />
        <div className="absolute bottom-4 left-4 right-16 bg-surface-secondary border-1 border-border-default rounded-md p-3 flex flex-wrap items-center gap-4">
          <Button variant="outline" aria-label={playing ? 'Pause' : 'Play'} className="w-control-h px-0" onClick={() => { if (t >= end) setT(start); setPlaying((p) => !p) }}>
            {playing ? <Pause className="h-icon w-icon" aria-hidden /> : <Play className="h-icon w-icon" aria-hidden />}
          </Button>
          <input type="range" aria-label="Replay time" className="flex-1 min-w-panel-sm accent-accent" min={start} max={end} step={60000} value={t}
            onChange={(e) => { setPlaying(false); setT(Number(e.target.value)) }} />
          <span className="text-14 font-semibold tabular-nums w-16 text-right">{clock}</span>
          <Tabs tabs={SPEEDS.map((s) => ({ id: s, label: `${s}×` }))} value={speed} onChange={setSpeed} />
        </div>
      </div>

      <ChartCard title="Arrival error per stop" description="Minutes after (+) or before (−) the planned arrival, in route-start order. Amber-red bars missed their window." height="h-chart">
        <BarChart data={errors}>
          <CartesianGrid stroke={chart.grid} vertical={false} />
          <XAxis dataKey="i" {...chart.axis} /><YAxis {...chart.axis} unit=" min" />
          <ReferenceLine y={0} stroke={chart.muted} />
          <Tooltip {...chart.tooltip} formatter={(v) => [`${v} min`, 'error']} labelFormatter={(_, p) => String(p?.[0]?.payload?.order ?? '')} />
          <Bar dataKey="error" radius={[2, 2, 0, 0]}>
            {errors.map((e) => <Cell key={e.order} fill={e.late ? statusStyle.late.color : chart.accent} />)}
          </Bar>
        </BarChart>
      </ChartCard>
    </div>
  )
}
