import { useEffect, useMemo, useRef, useState } from 'react'
import MapboxMap, { Layer as MbLayer, NavigationControl as MbNav, Source as MbSource, type MapRef } from 'react-map-gl/mapbox'
import MaplibreMap, { Layer as MlLayer, NavigationControl as MlNav, Source as MlSource } from 'react-map-gl/maplibre'
import type { MapMouseEvent } from 'mapbox-gl'
import type { FeatureCollection } from 'geojson'
import 'mapbox-gl/dist/mapbox-gl.css'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { Plan } from '../api/types'
import { colors, statusStyle, vehicleColor, vehicleDashed, type PlanStatus } from '../design-system/tokens'
import { blend, easeInOut, resample, type LngLat } from '../lib/geo'
import { cn } from '../components/ui'
import { retintToCommandNavy } from './navyStyle'

export const MAPBOX_TOKEN: string | undefined = import.meta.env.VITE_MAPBOX_TOKEN
export const MAP_STYLE = 'mapbox://styles/mapbox/dark-v11'
// Keyless fallback so the map still renders when no Mapbox token is configured.
export const FALLBACK_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'
const FALLBACK_FONT = ['Montserrat Regular']
const MORPH_POINTS = 64
const MORPH_MS = 600

export interface LayerToggles { routes: boolean; stops: boolean; unassigned: boolean }
export const ALL_LAYERS: LayerToggles = { routes: true, stops: true, unassigned: true }

interface Props {
  plan: Plan | null
  className?: string
  selectedOrderId?: string | null
  hiddenVehicles?: Set<string>
  layers?: LayerToggles
  /** Morph route lines between successive plans (what-if). */
  animate?: boolean
  focus?: { lat: number; lng: number } | null
  /** Live vehicle markers (replay). */
  vehicles?: { vehicle_id: string; lat: number; lng: number }[]
  onStopClick?: (orderId: string) => void
  children?: React.ReactNode
}

type Fc = FeatureCollection

const BaseMap = (MAPBOX_TOKEN ? MapboxMap : MaplibreMap) as typeof MapboxMap
const Layer = (MAPBOX_TOKEN ? MbLayer : MlLayer) as typeof MbLayer
const Source = (MAPBOX_TOKEN ? MbSource : MlSource) as typeof MbSource
const NavigationControl = (MAPBOX_TOKEN ? MbNav : MlNav) as typeof MbNav
const textFont = MAPBOX_TOKEN ? {} : { 'text-font': FALLBACK_FONT }

const prefersReducedMotion = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

export function MapCanvas({ plan, className, selectedOrderId, hiddenVehicles, layers = ALL_LAYERS, animate, focus, vehicles, onStopClick, children }: Props) {
  const mapRef = useRef<MapRef>(null)
  const fitted = useRef(false)
  const prevLines = useRef<Record<string, LngLat[]>>({})
  const [morphT, setMorphT] = useState(1)
  const [fromLines, setFromLines] = useState<Record<string, LngLat[]>>({})

  const vehicleOrder = useMemo(() => [...new Set((plan?.routes ?? []).map((r) => r.vehicle_id))].sort(), [plan])

  const targetLines = useMemo(() => {
    const out: Record<string, LngLat[]> = {}
    for (const r of plan?.routes ?? []) {
      const pts: LngLat[] = r.stops.map((s) => [s.lng, s.lat])
      if (plan?.depot) { const d: LngLat = [plan.depot.lng, plan.depot.lat]; pts.unshift(d); pts.push(d) }
      out[r.route_id] = pts
    }
    return out
  }, [plan])

  // Morph: start from the previous plan's line for the same vehicle (or a collapsed line at the depot).
  useEffect(() => {
    if (!plan) return
    const vehicleOf: Record<string, string> = Object.fromEntries(plan.routes.map((r) => [r.route_id, r.vehicle_id]))
    const previous = prevLines.current
    if (animate && !prefersReducedMotion() && Object.keys(previous).length) {
      const from: Record<string, LngLat[]> = {}
      for (const [rid, pts] of Object.entries(targetLines)) {
        const prev = previous[vehicleOf[rid]]
        from[rid] = prev ?? pts.map(() => (plan.depot ? [plan.depot.lng, plan.depot.lat] as LngLat : pts[0]))
      }
      setFromLines(from)
      let raf = 0
      const t0 = performance.now()
      const tick = (now: number) => {
        const t = Math.min(1, (now - t0) / MORPH_MS)
        setMorphT(easeInOut(t))
        if (t < 1) raf = requestAnimationFrame(tick)
      }
      setMorphT(0)
      raf = requestAnimationFrame(tick)
      prevLines.current = Object.fromEntries(Object.entries(targetLines).map(([rid, pts]) => [vehicleOf[rid], pts]))
      return () => cancelAnimationFrame(raf)
    }
    setMorphT(1)
    prevLines.current = Object.fromEntries(Object.entries(targetLines).map(([rid, pts]) => [vehicleOf[rid], pts]))
  }, [plan, targetLines, animate])

  const data = useMemo(() => {
    const lines: Fc = { type: 'FeatureCollection', features: [] }
    const stops: Fc = { type: 'FeatureCollection', features: [] }
    const unassigned: Fc = { type: 'FeatureCollection', features: [] }
    const depot: Fc = { type: 'FeatureCollection', features: [] }
    const none: Fc = { type: 'FeatureCollection', features: [] }
    if (!plan) return { lines, stops, unassigned, depot, trucks: none }
    for (const r of plan.routes) {
      if (hiddenVehicles?.has(r.vehicle_id)) continue
      const idx = vehicleOrder.indexOf(r.vehicle_id)
      const to = targetLines[r.route_id]
      const from = fromLines[r.route_id]
      const coords = morphT < 1 && from && to ? blend(resample(from, MORPH_POINTS), resample(to, MORPH_POINTS), morphT) : to
      if (coords.length > 1) {
        lines.features.push({ type: 'Feature', geometry: { type: 'LineString', coordinates: coords },
          properties: { route_id: r.route_id, vehicle_id: r.vehicle_id, color: vehicleColor(idx), dashed: vehicleDashed(idx) } })
      }
      r.stops.forEach((s, k) => {
        const st = statusStyle[s.status as PlanStatus]
        stops.features.push({ type: 'Feature', geometry: { type: 'Point', coordinates: [s.lng, s.lat] },
          properties: { order_id: s.order_id, vehicle_id: r.vehicle_id, seq: k + 1, color: vehicleColor(idx), ring: st.color, glyph: st.glyph, selected: s.order_id === selectedOrderId } })
      })
    }
    for (const u of plan.unassigned) {
      if (u.lat === undefined || u.lng === undefined) continue
      unassigned.features.push({ type: 'Feature', geometry: { type: 'Point', coordinates: [u.lng, u.lat] },
        properties: { order_id: u.order_id, ring: statusStyle.unassigned.color, glyph: statusStyle.unassigned.glyph, selected: u.order_id === selectedOrderId } })
    }
    if (plan.depot) depot.features.push({ type: 'Feature', geometry: { type: 'Point', coordinates: [plan.depot.lng, plan.depot.lat] }, properties: {} })
    const trucks: Fc = { type: 'FeatureCollection', features: (vehicles ?? []).map((v) => ({ type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [v.lng, v.lat] },
      properties: { color: vehicleColor(Math.max(0, vehicleOrder.indexOf(v.vehicle_id))) } })) }
    return { lines, stops, unassigned, depot, trucks }
  }, [vehicles, plan, hiddenVehicles, vehicleOrder, targetLines, fromLines, morphT, selectedOrderId])

  const fit = () => {
    const map = mapRef.current?.getMap()
    if (!map || !plan) return
    const pts: LngLat[] = [...plan.routes.flatMap((r) => r.stops.map((s) => [s.lng, s.lat] as LngLat)), ...(plan.depot ? [[plan.depot.lng, plan.depot.lat] as LngLat] : [])]
    if (!pts.length) return
    const lngs = pts.map((p) => p[0]), lats = pts.map((p) => p[1])
    map.fitBounds([[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]], { padding: 64, duration: prefersReducedMotion() ? 0 : 600, maxZoom: 14 })
  }
  useEffect(() => { if (plan && !fitted.current && mapRef.current?.getMap()?.isStyleLoaded()) { fit(); fitted.current = true } }, [plan]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (focus) mapRef.current?.flyTo({ center: [focus.lng, focus.lat], zoom: 14, duration: prefersReducedMotion() ? 0 : 500 }) }, [focus])

  const onClick = (e: MapMouseEvent) => {
    const f = e.features?.[0] as { properties?: Record<string, unknown> } | undefined
    const id = f?.properties?.order_id as string | undefined
    if (id && onStopClick) onStopClick(id)
  }

  return (
    <div className={cn('relative overflow-hidden rounded-md border-1 border-border-default', className)}>
      <BaseMap
        ref={mapRef}
        {...(MAPBOX_TOKEN ? { mapboxAccessToken: MAPBOX_TOKEN } : {})}
        mapStyle={MAPBOX_TOKEN ? MAP_STYLE : FALLBACK_STYLE}
        initialViewState={{ longitude: -118.2468, latitude: 34.0407, zoom: 10.5 }}
        style={{ width: '100%', height: '100%' }}
        interactiveLayerIds={['stops-circle', 'unassigned-circle']}
        onClick={onClick}
        onLoad={(e) => { if (MAPBOX_TOKEN) retintToCommandNavy(e.target as never); if (plan && !fitted.current) { fit(); fitted.current = true } }}
        cursor="default"
      >
        <NavigationControl position="top-right" showCompass={false} />
        {layers.routes && (
          <Source id="lines" type="geojson" data={data.lines}>
            <Layer id="lines-solid" type="line" filter={['==', ['get', 'dashed'], false]} layout={{ 'line-cap': 'round', 'line-join': 'round' }}
              paint={{ 'line-color': ['get', 'color'], 'line-width': 3, 'line-opacity': 0.85 }} />
            <Layer id="lines-dashed" type="line" filter={['==', ['get', 'dashed'], true]} layout={{ 'line-join': 'round' }}
              paint={{ 'line-color': ['get', 'color'], 'line-width': 3, 'line-opacity': 0.85, 'line-dasharray': [2, 2] }} />
          </Source>
        )}
        {layers.stops && (
          <Source id="stops" type="geojson" data={data.stops}>
            <Layer id="stops-circle" type="circle" paint={{
              'circle-radius': ['case', ['get', 'selected'], 12, 9], 'circle-color': ['get', 'color'],
              'circle-stroke-width': 3, 'circle-stroke-color': ['get', 'ring'] }} />
            <Layer id="stops-glyph" type="symbol" layout={{ 'text-field': ['get', 'glyph'], 'text-size': 12, 'text-allow-overlap': true, 'text-ignore-placement': true, ...textFont }}
              paint={{ 'text-color': colors.surface.dominant }} />
          </Source>
        )}
        {layers.unassigned && (
          <Source id="unassigned" type="geojson" data={data.unassigned}>
            <Layer id="unassigned-circle" type="circle" paint={{
              'circle-radius': ['case', ['get', 'selected'], 12, 9], 'circle-color': colors.surface.secondary,
              'circle-stroke-width': 3, 'circle-stroke-color': ['get', 'ring'] }} />
            <Layer id="unassigned-glyph" type="symbol" layout={{ 'text-field': ['get', 'glyph'], 'text-size': 12, 'text-allow-overlap': true, 'text-ignore-placement': true, ...textFont }}
              paint={{ 'text-color': colors.text.secondary }} />
          </Source>
        )}
        <Source id="trucks" type="geojson" data={data.trucks}>
          <Layer id="trucks-circle" type="circle" paint={{ 'circle-radius': 8, 'circle-color': colors.text.primary, 'circle-stroke-width': 4, 'circle-stroke-color': ['get', 'color'] }} />
        </Source>
        <Source id="depot" type="geojson" data={data.depot}>
          <Layer id="depot-circle" type="circle" paint={{ 'circle-radius': 12, 'circle-color': colors.text.primary, 'circle-stroke-width': 3, 'circle-stroke-color': colors.accent }} />
          <Layer id="depot-glyph" type="symbol" layout={{ 'text-field': 'D', 'text-size': 12, 'text-allow-overlap': true, ...textFont }} paint={{ 'text-color': colors.surface.dominant }} />
        </Source>
      </BaseMap>
      {children}
    </div>
  )
}
