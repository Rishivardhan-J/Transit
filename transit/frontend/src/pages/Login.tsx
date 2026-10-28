import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/endpoints'
import { Button, Card, Heading, Text, errorMessage } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import type { Role } from '../api/types'
import { apiClient } from '../api/client'

const DEMO: { label: string; email: string }[] = [
  { label: 'Manager', email: 'manager@transit.com' },
  { label: 'Researcher', email: 'researcher@transit.com' },
  { label: 'Admin', email: 'admin@transit.com' },
]

export function Login() {
  const nav = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      const token = await api.login(email.trim(), password)
      const me = await apiClient.get<{ role: Role }>('/users/me', { headers: { Authorization: `Bearer ${token}` } })
      setAuth(token, me.data.role, email.trim())
      nav('/', { replace: true })
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status
      setError(status === 401 ? 'Incorrect email or password.' : errorMessage(err))
    } finally { setBusy(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-surface-dominant">
      <Card className="w-panel-md max-w-full p-6 gap-6">
        <div>
          <span className="text-20 font-bold tracking-widest uppercase text-accent">Transit</span>
          <Heading level={1} size={24} className="mt-2">Sign in</Heading>
          <Text variant="secondary" size={14} className="mt-1">Explainable, constraint-aware routing.</Text>
        </div>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-2 text-14 font-medium">
            Email
            <input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)}
              className="h-control-h bg-surface-dominant border-1 border-border-default rounded-md px-3 text-14 font-normal" />
          </label>
          <label className="flex flex-col gap-2 text-14 font-medium">
            Password
            <input type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="h-control-h bg-surface-dominant border-1 border-border-default rounded-md px-3 text-14 font-normal" />
          </label>
          {error && <p role="alert" className="text-14 text-status-error-text">{error}</p>}
          <Button type="submit" loading={busy}>Sign in</Button>
        </form>
        <div className="flex flex-col gap-2">
          <Text variant="muted" size={12}>Demo accounts (password: transit-demo)</Text>
          <div className="flex flex-wrap gap-2">
            {DEMO.map((d) => (
              <Button key={d.email} type="button" variant="outline" className="h-8 px-3 text-12"
                onClick={() => { setEmail(d.email); setPassword('transit-demo') }}>{d.label}</Button>
            ))}
          </div>
        </div>
      </Card>
    </div>
  )
}
