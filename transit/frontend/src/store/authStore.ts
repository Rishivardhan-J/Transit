import { create } from 'zustand'
import type { Role } from '../api/types'

export type { Role }

const read = (k: string) => { try { return localStorage.getItem(k) } catch { return null } }
const write = (k: string, v: string | null) => {
  try { if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v) } catch { /* storage unavailable */ }
}

interface AuthState {
  token: string | null
  role: Role | null
  email: string | null
  isResearchMode: boolean
  setAuth: (token: string, role: Role, email: string) => void
  logout: () => void
  setResearchMode: (on: boolean) => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: read('token'),
  role: read('role') as Role | null,
  email: read('email'),
  isResearchMode: read('isResearchMode') === 'true',
  setAuth: (token, role, email) => {
    write('token', token); write('role', role); write('email', email); write('isResearchMode', 'false')
    set({ token, role, email, isResearchMode: false })
  },
  logout: () => {
    ;['token', 'role', 'email', 'isResearchMode'].forEach((k) => write(k, null))
    set({ token: null, role: null, email: null, isResearchMode: false })
  },
  // Enforced server-side too (403); this only controls what the UI shows.
  setResearchMode: (on) => {
    const { role } = get()
    if (role !== 'researcher' && role !== 'admin') return
    write('isResearchMode', String(on))
    set({ isResearchMode: on })
  },
}))

export const canUseResearch = (role: Role | null) => role === 'researcher' || role === 'admin'
