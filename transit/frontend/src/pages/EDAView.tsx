import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { RoleGate } from '../components/RoleGate'
import { Heading, Text, Card, Button } from '../components/ui'
import { ChartPanel } from '../components/ChartPanel'

export function EDAView() {
  const [jsonText, setJsonText] = useState('')
  const [importStatus, setImportStatus] = useState<string | null>(null)

  const { data: summary } = useQuery({
    queryKey: ['eda_summary'],
    queryFn: async () => {
      const res = await apiClient.get('/eda/summary')
      return res.data
    }
  })

  const handleImport = async () => {
    try {
      setImportStatus('Importing...')
      const parsed = JSON.parse(jsonText)
      const res = await apiClient.post('/orders/batch', parsed)
      setImportStatus(res.data.message || 'Import successful')
      setJsonText('')
    } catch (e: any) {
      if (e.response?.data?.detail) {
        // Detailed validation errors from Phase 1 DataProcessor
        const errors = e.response.data.detail.errors || e.response.data.detail
        setImportStatus(`Validation failed: ${JSON.stringify(errors, null, 2)}`)
      } else {
        setImportStatus(`Error: ${e.message}`)
      }
    }
  }

  return (
    <RoleGate allowedRoles={['researcher', 'admin']} requireResearchMode>
      <div className="space-y-6">
        <div className="mb-6">
          <Heading level={1} size={32}>Exploratory Data Analysis</Heading>
          <Text variant="secondary">Dataset distributions, correlation matrices, and bulk data import.</Text>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="p-4">
            <Heading level={3} size={20} className="mb-4">Batch Data Import</Heading>
            <textarea
              className="w-full h-32 bg-surface-dominant border-1 border-border-default p-2 text-text-primary text-14 mb-4 font-mono focus:outline-none focus:border-accent"
              placeholder="Paste JSON array of orders here..."
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
            />
            <Button onClick={handleImport} className="w-full">Run Batch Validation & Import</Button>
            {importStatus && (
              <pre className="mt-4 p-2 bg-surface-dominant border-1 border-border-default text-12 text-text-secondary overflow-auto max-h-40">
                {importStatus}
              </pre>
            )}
          </Card>
          
          <ChartPanel 
            title="Mean Absolute Feature Importance (Global SHAP)" 
            data={(summary?.feature_importance || []).map((d: any) => ({
              ...d,
              importance: Math.abs(d.importance)
            }))}
            xKey="feature" 
            yKey="importance" 
            color="#F59E0B"
            domain={[0, 'auto']} 
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ChartPanel 
            title="Demand Weight Distribution" 
            data={summary?.distributions?.demand_weight || []} 
            xKey="bin" 
            yKey="count" 
          />
          <ChartPanel 
            title="Priority Distribution" 
            data={summary?.distributions?.priority || []} 
            xKey="category" 
            yKey="count" 
            color="#10B981"
          />
        </div>
      </div>
    </RoleGate>
  )
}
