import { useMemo } from 'react'
import Map, { Source, Layer, NavigationControl } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Card } from './ui'

interface RouteMapProps {
  routes: any[]
  orders: any[]
  vehicles?: any[]
  onStopClick?: (orderId: string) => void
  className?: string
}

const MAP_STYLE = 'https://tiles.openfreemap.org/styles/dark'

// Categorical colors from tokens
const COLORS = [
  '#38BDF8', '#F59E0B', '#A78BFA', '#EC4899',
  '#10B981', '#F43F5E', '#8B5CF6', '#14B8A6'
]

export function RouteMap({ routes, orders, vehicles = [], onStopClick, className }: RouteMapProps) {
    const getStatusColor = (status: string) => {
      switch (status) {
        case 'late': return '#FCA5A5'; // red
        case 'in_transit': 
        case 'assigned': return '#FCD34D'; // amber
        case 'delivered': return '#4ADE80'; // green
        case 'pending': return '#EF4444'; // red for unassigned
        default: return '#94A3B8';
      }
    };

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
        
        // Add vehicle depot as starting point for line
        const vehicle = vehicles.find(v => v.vehicle_id === route.vehicle_id)
        if (vehicle && vehicle.current_lng !== undefined) {
           coordinates.unshift([vehicle.current_lng, vehicle.current_lat])
           // Also add depot marker
           features.push({
             type: 'Feature',
             geometry: {
               type: 'Point',
               coordinates: [vehicle.current_lng, vehicle.current_lat]
             },
             properties: {
               is_depot: true,
               color: '#FFFFFF'
             }
           })
        }
        
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
        const isUnassigned = order.status === 'pending';
        const color = getStatusColor(order.status);
        
        features.push({
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [order.delivery_lng, order.delivery_lat]
          },
          properties: {
            order_id: order.order_id,
            status: order.status,
            color,
            is_unassigned: isUnassigned
          }
        })
      }
    })
    
    return {
      type: 'FeatureCollection',
      features
    }
  }, [routes, orders, vehicles])

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
        <NavigationControl position="top-right" />
        <Source id="routes-source" type="geojson" data={geojsonData}>
          <Layer 
            id="lines-layer"
            type="line"
            filter={['==', ['geometry-type'], 'LineString']}
            paint={{
              'line-color': ['get', 'color'],
              'line-width': 3,
              'line-opacity': 0.8
            }}
          />
          {/* Regular assigned stops */}
          <Layer 
            id="points-layer"
            type="circle"
            filter={['all', ['==', ['geometry-type'], 'Point'], ['!', ['has', 'is_depot']], ['!=', ['get', 'is_unassigned'], true]]}
            paint={{
              'circle-color': ['get', 'color'],
              'circle-radius': 6,
              'circle-stroke-width': 2,
              'circle-stroke-color': '#0F172A' // surface-dominant
            }}
          />
          {/* Unassigned/Pending Stops (Distinct Hollow dots) */}
          <Layer 
            id="unassigned-layer"
            type="circle"
            filter={['all', ['==', ['geometry-type'], 'Point'], ['==', ['get', 'is_unassigned'], true]]}
            paint={{
              'circle-color': '#1E293B', // surface-secondary inside
              'circle-radius': 6,
              'circle-stroke-width': 3,
              'circle-stroke-color': '#EF4444' // red stroke
            }}
          />
          {/* Depot markers (Distinct square/symbol) */}
          <Layer 
            id="depots-layer"
            type="symbol"
            filter={['has', 'is_depot']}
            layout={{
              'icon-image': 'marker-15', // maplibre default icon, or text if none
              'text-field': '★',
              'text-size': 20
            }}
            paint={{
              'text-color': '#FFFFFF',
              'text-halo-color': '#0F172A',
              'text-halo-width': 2
            }}
          />
        </Source>
      </Map>
    </Card>
  )
}
