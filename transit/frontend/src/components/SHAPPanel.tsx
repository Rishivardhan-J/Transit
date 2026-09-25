import React, { useEffect, useState } from 'react'
import { Card, Text, Heading, Button, cn } from './ui'
import { apiClient } from '../api/client'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

interface SHAPPanelProps {
  orderId: string
  onClose: () => void
  className?: string
}

export function SHAPPanel({ orderId, onClose, className }: SHAPPanelProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    const fetchData = async () => {
      setLoading(true)
      try {
        // Assume GET /predictions/{order_id}/explain exists from Phase 2/4
        const res = await apiClient.get(`/predictions/${orderId}/explain`)
        if (mounted) {
          setData(res.data)
          setError(null)
        }
      } catch (err: any) {
        if (mounted) {
          setError(err.response?.data?.detail || 'Failed to load SHAP values')
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }
    fetchData()
    return () => { mounted = false }
  }, [orderId])

  return (
    <Card className={cn('p-4 flex flex-col z-10 absolute right-4 top-4 w-80 bg-surface-secondary shadow-2xl border-border-default/50', className)}>
      <div className="flex justify-between items-center mb-4">
        <Heading size={16} weight="semibold">AI Prediction Explainability</Heading>
        <button onClick={onClose} className="text-text-muted hover:text-text-primary">&times;</button>
      </div>
      
      {loading ? (
        <Text variant="muted">Loading SHAP data...</Text>
      ) : error ? (
        <Text variant="secondary" className="text-red-500">{error}</Text>
      ) : data ? (
        <div className="flex flex-col space-y-4">
          <div className="flex justify-between border-b-1 border-border-default pb-2">
            <Text variant="secondary">Predicted ETA</Text>
            <Text weight="bold" className="text-accent">{data.predicted_eta_mins} mins</Text>
          </div>
          
          <Text size={12} variant="secondary" className="uppercase">Feature Contributions (SHAP)</Text>
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.shap_values} layout="vertical" margin={{ left: -20, right: 10, top: 0, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="feature" type="category" width={100} tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
                  itemStyle={{ color: '#F1F5F9' }}
                  cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {data.shap_values.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.value > 0 ? '#F59E0B' : '#38BDF8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <Text size={12} variant="muted">
            Positive values (Orange) increase ETA. Negative (Blue) decrease ETA.
          </Text>
        </div>
      ) : null}
    </Card>
  )
}
