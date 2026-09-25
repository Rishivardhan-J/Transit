import { useMemo } from 'react'
import Map, { Source, Layer } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Card } from './ui'

interface RouteMapProps {
  routes: any[]
  orders: any[]
  onStopClick?: (orderId: string) => void
  className?: string
}

const MAP_STYLE = 'https://tiles.openfreemap.org/styles/dark'

// Categorical colors from tokens
const COLORS = [
  '#38BDF8', '#F59E0B', '#A78BFA', '#EC4899',
  '#10B981', '#F43F5E', '#8B5CF6', '#14B8A6'
]

export function RouteMap({ routes, orders, onStopClick, className }: RouteMapProps) {
  const geojsonData = useMemo(() => {
    const features: any[] = []
    
    // Add lines for routes
    routes.forEach((route, idx) => {
      const color = COLORS[idx % COLORS.length]
      if (route.ordered_stops && route.ordered_stops.length > 0) {
        const coordinates = route.ordered_stops.map((stopId: string) => {
          const order = orders.find(o => o.order_id === stopId)
          if (order && order.delivery_lng !== undefined && order.delivery_lat !== undefined) {
            return [order.delivery_lng, order.delivery_lat]
          }
          return null
        }).filter(Boolean)
        
        if (coordinates.length > 1) {
          features.push({
            type: 'Feature',
            geometry: {
              type: 'LineString',
              coordinates
            },
            properties: {
              route_id: route.route_id,
              color
            }
          })
        }
      }
    })
    
    // Add points for orders
    orders.forEach((order) => {
      if (order.delivery_lng !== undefined && order.delivery_lat !== undefined) {
        // Find which route it belongs to
        const routeIdx = routes.findIndex(r => r.ordered_stops.includes(order.order_id))
        const color = routeIdx >= 0 ? COLORS[routeIdx % COLORS.length] : '#94A3B8'
        
        features.push({
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [order.delivery_lng, order.delivery_lat]
          },
          properties: {
            order_id: order.order_id,
            status: order.status,
            color
          }
        })
      }
    })
    
    return {
      type: 'FeatureCollection',
      features
    }
  }, [routes, orders])

  const onClick = (event: any) => {
    const feature = event.features?.[0]
    if (feature && feature.geometry.type === 'Point' && onStopClick) {
      onStopClick(feature.properties.order_id)
    }
  }

  return (
    <Card className={`relative overflow-hidden ${className}`}>
      <Map
        style={{ width: '100%', height: '100%' }}
        initialViewState={{
          longitude: -122.4194, // SF coordinates to match seed data
          latitude: 37.7749,
          zoom: 11
        }}
        mapStyle={MAP_STYLE}
        interactiveLayerIds={['points-layer']}
        onClick={onClick}
        cursor="pointer"
      >
        <Source id="routes-source" type="geojson" data={geojsonData}>
          <Layer 
            id="lines-layer"
            type="line"
            filter={['==', '$type', 'LineString']}
            paint={{
              'line-color': ['get', 'color'],
              'line-width': 3,
              'line-opacity': 0.8
            }}
          />
          <Layer 
            id="points-layer"
            type="circle"
            filter={['==', '$type', 'Point']}
            paint={{
              'circle-color': ['get', 'color'],
              'circle-radius': 6,
              'circle-stroke-width': 2,
              'circle-stroke-color': '#0F172A' // surface-dominant
            }}
          />
        </Source>
      </Map>
    </Card>
  )
}
