import React from 'react'
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
}

export function ChartPanel({ title, data, xKey, yKey, color = '#38BDF8', className, domain }: ChartPanelProps) {
  return (
    <Card className={cn("p-4", className)}>
      <Text variant="secondary" size={14} className="mb-4 uppercase tracking-wide">{title}</Text>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
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
      </div>
    </Card>
  )
}
