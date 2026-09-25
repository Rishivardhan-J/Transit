import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { RouteMap } from '../components/RouteMap'
import { SHAPPanel } from '../components/SHAPPanel'
import { Heading, Text, Card } from '../components/ui'

export function MapView() {
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null)

  const { data: routes, isLoading: routesLoading } = useQuery({
    queryKey: ['routes'],
    queryFn: async () => {
      const res = await apiClient.get('/routes')
      return res.data
    },
    refetchInterval: 10000
  })

  const { data: orders, isLoading: ordersLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: async () => {
      const res = await apiClient.get('/orders')
      return res.data
    },
    refetchInterval: 10000
  })

  const { data: vehicles } = useQuery({
    queryKey: ['vehicles'],
    queryFn: async () => {
      const res = await apiClient.get('/vehicles')
      return res.data
    },
    refetchInterval: 10000
  })

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col relative">
      <div className="mb-4">
        <Heading level={1} size={32}>Route Map</Heading>
        <Text variant="secondary">Live overview of all active routes and stops. Click on a stop to view AI Prediction Explainability.</Text>
      </div>
      
      {routesLoading || ordersLoading ? (
        <Card className="flex-1 items-center justify-center">
          <Text variant="muted">Loading map data...</Text>
        </Card>
      ) : (
        <RouteMap 
          routes={routes || []} 
          orders={orders || []} 
          vehicles={vehicles || []}
          onStopClick={setSelectedOrderId}
          className="flex-1"
        />
      )}

      {selectedOrderId && (
        <SHAPPanel 
          orderId={selectedOrderId} 
          onClose={() => setSelectedOrderId(null)} 
        />
      )}
    </div>
  )
}
