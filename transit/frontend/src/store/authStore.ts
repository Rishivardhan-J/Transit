import { create } from 'zustand'

export type Role = 'manager' | 'researcher' | 'admin'

interface AuthState {
  token: string | null
  role: Role | null
  isResearchMode: boolean
  setAuth: (token: string, role: Role) => void
  logout: () => void
  toggleResearchMode: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  role: localStorage.getItem('role') as Role | null,
  isResearchMode: localStorage.getItem('isResearchMode') === 'true',
  setAuth: (token, role) => {
    localStorage.setItem('token', token)
    localStorage.setItem('role', role)
    // Research mode is off by default when logging in, unless they are already in it.
    // Let's reset it to false on new login.
    localStorage.setItem('isResearchMode', 'false')
    set({ token, role, isResearchMode: false })
  },
  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    localStorage.removeItem('isResearchMode')
    set({ token: null, role: null, isResearchMode: false })
  },
  toggleResearchMode: () => {
    set((state) => {
      // Only researchers or admins can use research mode
      if (state.role === 'researcher' || state.role === 'admin') {
        const newValue = !state.isResearchMode
        localStorage.setItem('isResearchMode', String(newValue))
        return { isResearchMode: newValue }
      }
      return state
    })
  }
}))
