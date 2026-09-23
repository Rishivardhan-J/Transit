import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore, type Role } from '../store/authStore'
import { Card, Text, Heading, Button } from '../components/ui'
import { apiClient } from '../api/client'

export function Login() {
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()
  const [role, setRole] = useState<Role>('manager')
  const [error, setError] = useState<string>('')
  
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const params = new URLSearchParams()
      params.append('username', `${role}@transit.com`)
      params.append('password', 'admin')
      
      const response = await apiClient.post('/auth/login', params, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      })
      
      const token = response.data.access_token
      setAuth(token, role)
      navigate('/')
    } catch (err) {
      setError('Authentication failed. Please check backend logs.')
    }
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-dominant">
      <Card className="w-full max-w-md p-8 shadow-2xl">
        <div className="text-center mb-8">
          <Heading size={32} className="text-accent uppercase tracking-widest mb-2">Transit</Heading>
          <Text variant="secondary">Logistics Optimization Engine</Text>
        </div>
        
        {error && (
          <div className="mb-4 p-3 bg-red-900/30 border border-red-500 text-red-200 text-sm rounded">
            {error}
          </div>
        )}
        
        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-14 text-text-secondary mb-2 uppercase tracking-wide">Select Role</label>
            <select 
              value={role} 
              onChange={(e) => setRole(e.target.value as Role)}
              className="w-full bg-surface-dominant border-1 border-border-default text-text-primary p-3 focus:outline-none focus:border-accent appearance-none rounded-none"
            >
              <option value="manager">Manager (Operations)</option>
              <option value="researcher">Researcher (Data Science)</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          
          <Button type="submit" className="w-full py-3 text-16">
            Enter System
          </Button>
        </form>
      </Card>
    </div>
  )
}
