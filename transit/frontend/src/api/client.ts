import axios from 'axios'
import { useAuthStore } from '../store/authStore'

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const apiClient = axios.create({ baseURL: API_URL, headers: { 'Content-Type': 'application/json' } })

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

apiClient.interceptors.response.use((r) => r, (error) => {
  // A rejected login is a normal 401: only an expired/invalid session elsewhere should log the user out.
  if (error.response?.status === 401 && !String(error.config?.url ?? '').includes('/auth/login')) {
    useAuthStore.getState().logout()
    window.location.assign('/login')
  }
  return Promise.reject(error)
})

/** ws:// URL for a backend WebSocket path; the JWT travels as a query param (browsers cannot set WS headers). */
export function wsUrl(path: string): string {
  const token = useAuthStore.getState().token ?? ''
  return `${API_URL.replace(/^http/, 'ws')}${path}?token=${encodeURIComponent(token)}`
}
