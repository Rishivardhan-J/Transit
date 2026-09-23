import React from 'react'
import { useAuthStore, type Role } from '../store/authStore'
import { Navigate } from 'react-router-dom'

interface RoleGateProps {
  children: React.ReactNode
  allowedRoles: Role[]
  requireResearchMode?: boolean
}

export function RoleGate({ children, allowedRoles, requireResearchMode = false }: RoleGateProps) {
  const { role, isResearchMode } = useAuthStore()

  if (!role || !allowedRoles.includes(role)) {
    return <Navigate to="/" replace />
  }

  if (requireResearchMode && !isResearchMode) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
