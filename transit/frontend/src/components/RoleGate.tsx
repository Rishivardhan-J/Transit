import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { canUseResearch, useAuthStore } from '../store/authStore'
import { EmptyState } from './ui'
import { Lock } from 'lucide-react'

/** Research pages need a researcher/admin role AND research mode switched on (PRD 4). The server enforces the same. */
export function RoleGate({ children, need = 'research' }: { children: ReactNode; need?: 'research' | 'admin' }) {
  const { role, isResearchMode } = useAuthStore()
  if (need === 'admin') {
    if (role !== 'admin') return <EmptyState icon={Lock} title="Admins only" description="User and role management is limited to administrators." />
    return <>{children}</>
  }
  if (!canUseResearch(role)) return <EmptyState icon={Lock} title="Researcher access required" description="Your role does not include experiment and model controls." />
  if (!isResearchMode) return <Navigate to="/" replace />
  return <>{children}</>
}
