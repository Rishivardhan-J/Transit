import React from 'react'
import { Card, Text, Heading, cn } from './ui'

interface KPICardProps {
  label: string
  value: string | number
  trend?: string
  trendDirection?: 'up' | 'down' | 'neutral'
  className?: string
}

export function KPICard({ label, value, trend, trendDirection, className }: KPICardProps) {
  return (
    <Card className={cn('p-4 justify-between h-full', className)}>
      <Text variant="secondary" size={14} className="mb-2 uppercase tracking-wide">
        {label}
      </Text>
      <div className="flex items-baseline space-x-2">
        <Heading size={32} weight="bold" className="tabular-nums">
          {value}
        </Heading>
        {trend && (
          <Text
            size={14}
            weight="medium"
            className={cn({
              'text-status-success-text': trendDirection === 'up',
              'text-status-error-text': trendDirection === 'down',
              'text-text-muted': trendDirection === 'neutral',
            })}
          >
            {trend}
          </Text>
        )}
      </div>
    </Card>
  )
}
