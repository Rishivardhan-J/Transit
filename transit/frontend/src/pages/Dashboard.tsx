
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { KPICard } from '../components/KPICard'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'
import { Heading, Text, Card } from '../components/ui'
import { RouteMap } from '../components/RouteMap'

export function Dashboard() {
  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ['kpis'],
    queryFn: async () => {
      const res = await apiClient.get('/dashboard/kpis')
      return res.data
    },
    refetchInterval: 10000 // Polling
  })

  const { data: vehicles, isLoading: vehiclesLoading } = useQuery({
    queryKey: ['vehicles'],
    queryFn: async () => {
      const res = await apiClient.get('/vehicles')
      return res.data
    }
  })

  const { data: routes } = useQuery({
    queryKey: ['routes'],
    queryFn: async () => {
      const res = await apiClient.get('/routes')
      return res.data
    },
    refetchInterval: 10000 // Polling
  })

  const { data: orders } = useQuery({
    queryKey: ['orders'],
    queryFn: async () => {
      const res = await apiClient.get('/orders')
      return res.data
    },
    refetchInterval: 10000 // Polling
  })

  const columns = [
    { key: 'vehicle_id', header: 'Vehicle ID' },
    { key: 'vehicle_type', header: 'Type' },
    { key: 'capacity', header: 'Capacity' },
    { 
      key: 'status', 
      header: 'Status',
      render: (row: any) => {
        // Mock status based on routes
        const isAssigned = routes?.some((r: any) => r.vehicle_id === row.vehicle_id)
        return <StatusBadge status={isAssigned ? 'success' : 'neutral'} label={isAssigned ? 'Active' : 'Idle'} />
      }
    }
  ]

  return (
    <div className="space-y-6">
      <Heading level={1} size={32} className="mb-6">Operations Overview</Heading>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard 
          label="Fleet Utilization" 
          value={kpisLoading ? '...' : `${kpis?.fleet_utilization_pct}%`}
          trend={kpis?.fleet_utilization_pct > 80 ? '+2.4%' : undefined}
          trendDirection="up"
        />
        <KPICard 
          label="Active Routes" 
          value={kpisLoading ? '...' : kpis?.active_routes}
        />
        <KPICard 
          label="Late Deliveries" 
          value={kpisLoading ? '...' : kpis?.late_deliveries}
          trend={kpis?.late_deliveries > 0 ? 'Action Required' : 'On Track'}
          trendDirection={kpis?.late_deliveries > 0 ? 'down' : 'neutral'}
        />
        <KPICard 
          label="Cost vs Baseline" 
          value={kpisLoading ? '...' : `${kpis?.cost_vs_baseline_pct}%`}
          trend="vs OR-Tools"
          trendDirection="up"
          className="border-accent/50 bg-accent/5"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 flex flex-col">
          <Heading level={2} size={20} className="mb-4">Active Route Map</Heading>
          <div className="h-[400px]">
            {routes && orders && vehicles ? (
              <RouteMap routes={routes} orders={orders} vehicles={vehicles} className="h-full" />
            ) : (
              <Card className="h-full items-center justify-center">
                <Text variant="muted">Loading map data...</Text>
              </Card>
            )}
          </div>
        </div>
        
        <div className="flex flex-col">
          <Heading level={2} size={20} className="mb-4">Fleet Status</Heading>
          {vehiclesLoading ? (
            <Card className="flex-1 p-4"><Text variant="muted">Loading vehicles...</Text></Card>
          ) : (
            <DataTable data={vehicles || []} columns={columns} className="flex-1" />
          )}
        </div>
      </div>
    </div>
  )
}
