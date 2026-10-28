import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Layers, Search } from 'lucide-react'
import { api } from '../api/endpoints'
import { ALL_LAYERS, MapCanvas, type LayerToggles } from '../map/MapCanvas'
import { StopDetailCard } from '../components/StopDetail'
import { Card, EmptyState, ErrorState, Skeleton, Text, cn } from '../components/ui'
import { statusStyle, vehicleColor, type PlanStatus } from '../design-system/tokens'

const LAYER_LABELS: [keyof LayerToggles, string][] = [['routes', 'Routes'], ['stops', 'Stops'], ['unassigned', 'Unassigned']]

export function MapView() {
  const [params, setParams] = useSearchParams()
  const selected = params.get('order')
  const plan = useQuery({ queryKey: ['plan', 'latest'], queryFn: api.latestPlan })
  const [layers, setLayers] = useState<LayerToggles>(ALL_LAYERS)
  const [hidden, setHidden] = useState<Set<string>>(new Set())
  const [query, setQuery] = useState('')
  const [showLayers, setShowLayers] = useState(false)

  const vehicles = useMemo(() => [...new Set((plan.data?.routes ?? []).map((r) => r.vehicle_id))].sort(), [plan.data])
  const index = useMemo(() => {
    const idx: { id: string; kind: string; lat?: number; lng?: number }[] = []
    plan.data?.routes.forEach((r) => { idx.push({ id: r.vehicle_id, kind: 'vehicle' }); r.stops.forEach((s) => idx.push({ id: s.order_id, kind: 'stop', lat: s.lat, lng: s.lng })) })
    plan.data?.unassigned.forEach((u) => idx.push({ id: u.order_id, kind: 'unassigned', lat: u.lat, lng: u.lng }))
    return idx
  }, [plan.data])
  const matches = query.trim() ? index.filter((i) => i.id.toLowerCase().includes(query.trim().toLowerCase())).slice(0, 6) : []
  const focus = useMemo(() => { const m = index.find((i) => i.id === selected); return m?.lat !== undefined && m.lng !== undefined ? { lat: m.lat, lng: m.lng } : null }, [index, selected])

  const select = (id: string | null) => {
    const next = new URLSearchParams(params)
    if (id) next.set('order', id); else next.delete('order')
    setParams(next, { replace: true })
  }
  const toggleVehicle = (v: string) => setHidden((h) => {
    const n = new Set(h)
    if (n.has(v)) n.delete(v); else n.add(v)
    return n
  })

  if (plan.isLoading) return <Skeleton className="h-map-lg w-full" />
  if (plan.error) return <Card><ErrorState error={plan.error} onRetry={() => plan.refetch()} /></Card>
  if (!plan.data) return <Card><EmptyState title="No plan yet" description="Run an optimization to see routes on the map." /></Card>

  return (
    <div className="relative h-map-lg max-h-screen">
      <MapCanvas plan={plan.data} selectedOrderId={selected} hiddenVehicles={hidden} layers={layers} focus={focus} onStopClick={select} className="h-full">
        <div className="absolute top-4 left-4 w-panel-sm max-w-full flex flex-col gap-2">
          <div className="flex items-center gap-2 bg-surface-secondary border-1 border-border-default rounded-md px-3 h-control-h">
            <Search className="h-icon w-icon text-text-muted shrink-0" aria-hidden />
            <input aria-label="Search orders or vehicles" placeholder="Search order or vehicle" value={query} onChange={(e) => setQuery(e.target.value)}
              className="bg-transparent w-full text-14 placeholder:text-text-secondary outline-none" />
          </div>
          {matches.length > 0 && (
            <ul className="bg-surface-secondary border-1 border-border-default rounded-md overflow-hidden">
              {matches.map((m) => (
                <li key={m.kind + m.id}>
                  <button className="w-full flex justify-between px-3 py-2 text-14 hover:bg-surface-dominant text-left" onClick={() => { if (m.kind !== 'vehicle') select(m.id); setQuery('') }}>
                    <span>{m.id}</span><span className="text-12 text-text-secondary">{m.kind}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="flex flex-wrap gap-1" aria-label="Filter vehicles">
            {vehicles.map((v, i) => (
              <button key={v} aria-pressed={!hidden.has(v)} onClick={() => toggleVehicle(v)}
                className={cn('inline-flex items-center gap-1 h-8 px-2 rounded-full border-1 text-12', hidden.has(v) ? 'border-border-default text-text-secondary bg-surface-secondary' : 'border-border-hover text-text-primary bg-surface-secondary')}>
                <span className="h-2 w-2 rounded-full" style={{ background: vehicleColor(i), opacity: hidden.has(v) ? 0.3 : 1 }} aria-hidden />{v}
              </button>
            ))}
          </div>
        </div>

        <div className="absolute top-4 right-16 flex flex-col items-end gap-2">
          <button aria-expanded={showLayers} onClick={() => setShowLayers((s) => !s)}
            className="inline-flex items-center gap-2 h-control-h px-3 rounded-md bg-surface-secondary border-1 border-border-default text-14 hover:border-border-hover"><Layers className="h-icon w-icon" aria-hidden />Layers</button>
          {showLayers && (
            <div className="bg-surface-secondary border-1 border-border-default rounded-md p-3 flex flex-col gap-2">
              {LAYER_LABELS.map(([k, label]) => (
                <label key={k} className="flex items-center gap-2 text-14"><input type="checkbox" checked={layers[k]} onChange={() => setLayers((l) => ({ ...l, [k]: !l[k] }))} className="accent-accent" />{label}</label>
              ))}
            </div>
          )}
        </div>

        <Legend />
        {selected && <div className="absolute bottom-4 right-4 top-16 flex items-end"><StopDetailCard plan={plan.data} orderId={selected} onClose={() => select(null)} /></div>}
      </MapCanvas>
    </div>
  )
}

function Legend() {
  const items: PlanStatus[] = ['on_time', 'at_risk', 'late', 'unassigned']
  return (
    <div className="absolute bottom-4 left-4 bg-surface-secondary border-1 border-border-default rounded-md p-3 flex flex-col gap-2 pointer-events-none">
      <Text size={12} weight="semibold" className="uppercase tracking-wide">Stop status</Text>
      {items.map((s) => (
        <div key={s} className="flex items-center gap-2 text-12 text-text-secondary">
          <span className="inline-flex items-center justify-center h-4 w-4 rounded-full text-12 font-bold text-surface-dominant" style={{ background: statusStyle[s].color }} aria-hidden>{statusStyle[s].glyph}</span>{statusStyle[s].label}
        </div>
      ))}
      <div className="flex items-center gap-2 text-12 text-text-secondary"><span className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-text-primary text-surface-dominant font-bold" aria-hidden>D</span>Depot</div>
    </div>
  )
}
