import React from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { Text, Button, cn } from './ui'

export function Layout() {
  const { role, isResearchMode, logout, toggleResearchMode } = useAuthStore()
  
  const canToggleResearch = role === 'researcher' || role === 'admin'

  return (
    <div className="min-h-screen flex flex-col">
      <header className="h-16 border-b-1 border-border-default bg-surface-dominant flex items-center justify-between px-6 shrink-0">
        <div className="flex items-center space-x-8">
          <Text weight="bold" size={20} className="text-accent tracking-widest uppercase">Transit</Text>
          <nav className="flex space-x-4">
            <NavLink to="/" className={({ isActive }) => cn("px-3 py-2 text-14 font-medium transition-colors", isActive ? "text-accent" : "text-text-secondary hover:text-text-primary")}>Dashboard</NavLink>
            <NavLink to="/map" className={({ isActive }) => cn("px-3 py-2 text-14 font-medium transition-colors", isActive ? "text-accent" : "text-text-secondary hover:text-text-primary")}>Route Map</NavLink>
            
            {canToggleResearch && isResearchMode && (
              <>
                <NavLink to="/eda" className={({ isActive }) => cn("px-3 py-2 text-14 font-medium transition-colors", isActive ? "text-accent" : "text-text-secondary hover:text-text-primary")}>EDA</NavLink>
                <NavLink to="/models" className={({ isActive }) => cn("px-3 py-2 text-14 font-medium transition-colors", isActive ? "text-accent" : "text-text-secondary hover:text-text-primary")}>Models</NavLink>
              </>
            )}
          </nav>
        </div>
        
        <div className="flex items-center space-x-4">
          {canToggleResearch && (
            <div className="flex items-center space-x-2 mr-4 bg-surface-secondary px-3 py-1.5 rounded-full border-1 border-border-default">
              <Text size={12} variant={isResearchMode ? 'primary' : 'muted'} className="uppercase">Researcher Mode</Text>
              <button 
                onClick={toggleResearchMode}
                className={cn(
                  "relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent",
                  isResearchMode ? 'bg-accent' : 'bg-border-hover'
                )}
              >
                <span className={cn(
                  "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                  isResearchMode ? 'translate-x-2' : '-translate-x-2'
                )} />
              </button>
            </div>
          )}
          
          <Text size={14} variant="secondary">Role: <span className="text-text-primary capitalize">{role}</span></Text>
          <Button variant="outline" onClick={logout} className="ml-4">Logout</Button>
        </div>
      </header>
      
      <main className="flex-1 overflow-auto bg-surface-dominant p-6">
        <Outlet />
      </main>
    </div>
  )
}
