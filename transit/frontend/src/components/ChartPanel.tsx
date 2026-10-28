
import { Card, Text, cn } from './ui'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'

interface ChartPanelProps {
  title: string
  data: any[]
  xKey: string
  yKey: string
  color?: string
  className?: string
  domain?: [number | string, number | string]
  isLoading?: boolean
  error?: string | null
}

export function ChartPanel({ title, data, xKey, yKey, color = '#38BDF8', className, domain, isLoading, error }: ChartPanelProps) {
  return (
    <Card className={cn("p-4 flex flex-col", className)}>
      <Text variant="secondary" size={14} className="mb-4 uppercase tracking-wide font-semibold">{title}</Text>
      <div className="w-full flex-1 flex items-center justify-center" style={{ height: '280px', minHeight: '280px' }}>
        {isLoading ? (
          <div className="flex flex-col items-center justify-center space-y-2">
            <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <Text variant="secondary" size={14}>Loading distribution data...</Text>
          </div>
        ) : error ? (
          <div className="p-4 bg-status-error-bg rounded border border-status-error-text text-center max-w-sm">
            <Text variant="primary" className="text-status-error-text text-14 font-medium mb-1">Failed to load chart</Text>
            <Text variant="muted" size={12}>{error}</Text>
          </div>
        ) : !data || data.length === 0 ? (
          <div className="text-center p-4">
            <Text variant="muted" size={14}>No distribution data available</Text>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis dataKey={xKey} stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} domain={domain} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', color: '#F1F5F9' }}
                itemStyle={{ color: '#F1F5F9' }}
                cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
              />
              <Bar dataKey={yKey} fill={color} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  )
}
