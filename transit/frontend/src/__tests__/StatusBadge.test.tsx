import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PlanStatusBadge, StatusBadge } from '../components/ui'

describe('StatusBadge', () => {
  it('never relies on colour alone: text and an icon are always rendered', () => {
    const { container } = render(<StatusBadge tone="error" label="Late" />)
    expect(screen.getByText('Late')).toBeInTheDocument()
    expect(container.querySelector('svg')).not.toBeNull()
  })

  it('maps plan statuses to the fixed semantic labels', () => {
    render(<><PlanStatusBadge status="on_time" /><PlanStatusBadge status="at_risk" /><PlanStatusBadge status="late" /></>)
    for (const label of ['On time', 'At risk', 'Late']) expect(screen.getByText(label)).toBeInTheDocument()
  })
})
