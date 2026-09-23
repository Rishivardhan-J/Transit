import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { RoleGate } from '../components/RoleGate'
import { Heading, Text, Card } from '../components/ui'
import { DataTable } from '../components/DataTable'

export function ModelsView() {
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const { data: models, isLoading: modelsLoading } = useQuery({
    queryKey: ['models'],
    queryFn: async () => {
      const res = await apiClient.get('/models')
      return res.data
    },
    retry: false
  })

  const { data: performance, isLoading: perfLoading } = useQuery({
    queryKey: ['models_performance'],
    queryFn: async () => {
      try {
        const res = await apiClient.get('/models/performance')
        return res.data
      } catch (err: any) {
        if (err.response?.status === 403) {
          setErrorMsg('403 Forbidden: You do not have permission to access model performance data.')
        } else {
          setErrorMsg('Error fetching performance data.')
        }
        throw err
      }
    },
    retry: false
  })

  // We show error inline to prove RBAC works if somehow a non-researcher accesses this component
  // (though RoleGate should prevent it)
  
  const columns = [
    { key: 'run_id', header: 'Run ID', render: (r: any) => <Text size={12} className="font-mono">{r.run_id.substring(0, 8)}...</Text> },
    { key: 'model_type', header: 'Model Type' },
    { key: 'rmse', header: 'RMSE', render: (r: any) => r.metrics?.rmse?.toFixed(3) || 'N/A' },
    { key: 'mae', header: 'MAE', render: (r: any) => r.metrics?.mae?.toFixed(3) || 'N/A' },
    { key: 'r2', header: 'R²', render: (r: any) => r.metrics?.r2?.toFixed(3) || 'N/A' },
  ]

  return (
    <RoleGate allowedRoles={['researcher', 'admin']} requireResearchMode>
      <div className="space-y-6">
        <div className="mb-6">
          <Heading level={1} size={32}>Model Performance</Heading>
          <Text variant="secondary">View active MLflow runs and model evaluation metrics.</Text>
        </div>

        {errorMsg && (
          <Card className="p-4 bg-status-error-bg border-status-error-text">
            <Text variant="primary" className="text-status-error-text">{errorMsg}</Text>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="flex flex-col space-y-4">
            <Heading level={2} size={20}>Active Models Metadata</Heading>
            {modelsLoading ? (
              <Card className="p-4"><Text variant="muted">Loading models...</Text></Card>
            ) : (
              <Card className="p-4">
                <pre className="text-12 font-mono overflow-auto text-text-secondary bg-surface-dominant p-4">
                  {JSON.stringify(models, null, 2)}
                </pre>
              </Card>
            )}
          </div>

          <div className="flex flex-col space-y-4">
            <Heading level={2} size={20}>Performance Metrics</Heading>
            {perfLoading ? (
              <Card className="p-4"><Text variant="muted">Loading metrics...</Text></Card>
            ) : performance ? (
              <DataTable data={performance} columns={columns} />
            ) : null}
          </div>
        </div>
      </div>
    </RoleGate>
  )
}
