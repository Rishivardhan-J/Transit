import axios from 'axios'
import { useAuthStore } from '../store/authStore'

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to attach the JWT token
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

// Response interceptor to handle 401s globally
apiClient.interceptors.response.use((response) => {
  return response
}, (error) => {
  if (error.response?.status === 401) {
    useAuthStore.getState().logout()
    window.location.href = '/login'
  }
  return Promise.reject(error)
})
