import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './components/Layout'
import { RoleGate } from './components/RoleGate'
import { Toaster } from './components/ui'
import { useAuthStore } from './store/authStore'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { MapView } from './pages/MapView'
import { WhatIf } from './pages/WhatIf'
import { Compare } from './pages/Compare'
import { Replay } from './pages/Replay'
import { EDAView } from './pages/EDAView'
import { ModelsView } from './pages/ModelsView'
import { UsersView } from './pages/UsersView'

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 5000 } } })

function Protected({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Protected><Layout /></Protected>}>
            <Route index element={<Dashboard />} />
            <Route path="map" element={<MapView />} />
            <Route path="what-if" element={<WhatIf />} />
            <Route path="compare" element={<Compare />} />
            <Route path="replay" element={<Replay />} />
            <Route path="eda" element={<RoleGate><EDAView /></RoleGate>} />
            <Route path="models" element={<RoleGate><ModelsView /></RoleGate>} />
            <Route path="users" element={<RoleGate need="admin"><UsersView /></RoleGate>} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster />
    </QueryClientProvider>
  )
}
