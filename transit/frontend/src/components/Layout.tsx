import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Brain, ChevronDown, FlaskConical, History, LayoutDashboard, LogOut, Map, Menu, Play, Scale, SlidersHorizontal, Users } from 'lucide-react'
import { apiClient } from '../api/client'
import { canUseResearch, useAuthStore } from '../store/authStore'
import { Button, cn, Drawer, IconButton, Switch, Text } from './ui'
import { RunOptimizationModal } from './RunOptimizationModal'

interface NavItem { to: string; label: string; icon: React.ElementType; end?: boolean; show: boolean }

function useNav(): NavItem[] {
  const { role, isResearchMode } = useAuthStore()
  const research = canUseResearch(role) && isResearchMode
  return [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true, show: true },
    { to: '/map', label: 'Route map', icon: Map, show: true },
    { to: '/what-if', label: 'What-if', icon: SlidersHorizontal, show: true },
    { to: '/compare', label: 'Compare', icon: Scale, show: true },
    { to: '/replay', label: 'Replay', icon: History, show: true },
    { to: '/eda', label: 'EDA', icon: FlaskConical, show: research },
    { to: '/models', label: 'Models', icon: Brain, show: research },
    { to: '/users', label: 'Users', icon: Users, show: role === 'admin' },
  ].filter((n) => n.show)
}

function LiveIndicator() {
  const { isError, isSuccess } = useQuery({ queryKey: ['health'], queryFn: async () => (await apiClient.get('/health')).data, refetchInterval: 15000, retry: 0 })
  const label = isError ? 'Offline' : isSuccess ? 'Live' : 'Connecting'
  return (
    <span className="inline-flex items-center gap-2 text-12 text-text-secondary" role="status">
      <span className={cn('h-2 w-2 rounded-full', isError ? 'bg-status-error-text' : isSuccess ? 'bg-status-success-text' : 'bg-text-muted')} aria-hidden />
      {label}
    </span>
  )
}

function UserMenu() {
  const { role, email, isResearchMode, setResearchMode, logout } = useAuthStore()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const onDoc = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} aria-haspopup="menu" aria-expanded={open}
        className="inline-flex items-center gap-2 h-control-h px-3 rounded-md border-1 border-border-default hover:border-border-hover text-14">
        <span className="hidden sm:inline max-w-panel-sm truncate">{email}</span>
        <span className="text-12 text-text-secondary capitalize">{role}</span>
        <ChevronDown className="h-icon w-icon text-text-muted" aria-hidden />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-full mt-2 w-panel-sm bg-surface-secondary border-1 border-border-default rounded-md p-3 z-40 flex flex-col gap-3">
          {canUseResearch(role) && (
            <div className="flex items-center justify-between gap-3">
              <div>
                <Text weight="medium">Research mode</Text>
                <Text variant="secondary" size={12}>Show EDA and model controls</Text>
              </div>
              <Switch checked={isResearchMode} onChange={setResearchMode} label="Research mode" />
            </div>
          )}
          <Button variant="outline" icon={<LogOut className="h-icon w-icon" aria-hidden />} onClick={logout}>Sign out</Button>
        </div>
      )}
    </div>
  )
}

function NavLinks({ items, compact, onNavigate }: { items: NavItem[]; compact?: boolean; onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="flex flex-col gap-1">
      {items.map(({ to, label, icon: Icon, end }) => (
        <NavLink key={to} to={to} end={end} onClick={onNavigate} title={label} aria-label={label}
          className={({ isActive }) => cn('flex items-center gap-3 h-control-h rounded-md transition-colors duration-150',
            compact ? 'justify-center w-control-h' : 'px-3', isActive ? 'bg-surface-dominant text-accent' : 'text-text-secondary hover:text-text-primary hover:bg-surface-dominant')}>
          <Icon className="h-icon-lg w-icon-lg shrink-0" aria-hidden />
          {!compact && <span className="text-14 font-medium">{label}</span>}
        </NavLink>
      ))}
    </nav>
  )
}

export function Layout() {
  const items = useNav()
  const [menu, setMenu] = useState(false)
  const [run, setRun] = useState(false)
  const loc = useLocation()
  useEffect(() => setMenu(false), [loc.pathname])
  const fullBleed = loc.pathname === '/map' || loc.pathname === '/what-if' || loc.pathname === '/replay'

  return (
    <div className="min-h-screen flex">
      <aside className="hidden lg:flex flex-col items-center w-rail shrink-0 border-r-1 border-border-default bg-surface-dominant py-4 gap-6 sticky top-0 h-screen">
        <span className="text-accent font-bold text-20" aria-hidden>T</span>
        <NavLinks items={items} compact />
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="h-topbar border-b-1 border-border-default bg-surface-dominant flex items-center justify-between gap-4 px-4 md:px-6 shrink-0 sticky top-0 z-30">
          <div className="flex items-center gap-4">
            <IconButton aria-label="Open navigation" className="lg:hidden" onClick={() => setMenu(true)}><Menu className="h-icon-lg w-icon-lg" aria-hidden /></IconButton>
            <span className="text-20 font-bold tracking-widest uppercase text-accent">Transit</span>
            <span className="hidden sm:inline"><LiveIndicator /></span>
          </div>
          <div className="flex items-center gap-3">
            <Button icon={<Play className="h-icon w-icon" aria-hidden />} onClick={() => setRun(true)}>
              <span className="hidden sm:inline">Run optimization</span><span className="sm:hidden">Run</span>
            </Button>
            <UserMenu />
          </div>
        </header>

        <main className={cn('flex-1 min-w-0', fullBleed ? 'p-4 md:p-6' : 'p-4 md:p-6')}>
          <div className="mx-auto w-full max-w-container"><Outlet /></div>
        </main>
      </div>

      <Drawer open={menu} onClose={() => setMenu(false)} title="Navigation" side="left" className="w-panel-sm">
        <div className="p-3"><NavLinks items={items} onNavigate={() => setMenu(false)} /></div>
      </Drawer>
      <RunOptimizationModal open={run} onClose={() => setRun(false)} />
    </div>
  )
}
