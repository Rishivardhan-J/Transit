import React from 'react'
import { cn, Text } from './ui'

type StatusType = 'success' | 'warning' | 'error' | 'neutral'

interface StatusBadgeProps {
  status: StatusType
  label: string
  className?: string
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-1',
        {
          'bg-status-success-bg': status === 'success',
          'bg-status-warning-bg': status === 'warning',
          'bg-status-error-bg': status === 'error',
          'bg-surface-secondary': status === 'neutral',
        },
        className
      )}
    >
      <Text
        size={12}
        weight="medium"
        className={cn({
          'text-status-success-text': status === 'success',
          'text-status-warning-text': status === 'warning',
          'text-status-error-text': status === 'error',
          'text-text-secondary': status === 'neutral',
        })}
      >
        {label}
      </Text>
    </span>
  )
}
