import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/endpoints'
import type { Role, UserRow } from '../api/types'
import { Card, CardHeader, DataTable, Heading, QueryBoundary, Skeleton, Text, errorMessage, toast, type Column } from '../components/ui'
import { useAuthStore } from '../store/authStore'

const ROLES: Role[] = ['manager', 'researcher', 'admin']

export function UsersView() {
  const qc = useQueryClient()
  const me = useAuthStore((s) => s.email)
  const users = useQuery({ queryKey: ['users'], queryFn: api.users })
  const setRole = useMutation({
    mutationFn: ({ id, role }: { id: string; role: Role }) => api.setRole(id, role),
    onSuccess: () => { toast('success', 'Role updated.'); void qc.invalidateQueries({ queryKey: ['users'] }) },
    onError: (e) => toast('error', errorMessage(e)),
  })
  const columns: Column<UserRow>[] = [
    { key: 'email', header: 'User' },
    { key: 'role', header: 'Role', render: (u) => (
      <select aria-label={`Role for ${u.email}`} value={u.role} disabled={u.email === me || setRole.isPending}
        onChange={(e) => setRole.mutate({ id: u.id, role: e.target.value as Role })}
        className="h-8 bg-surface-dominant border-1 border-border-default rounded-md px-2 text-14 capitalize disabled:opacity-60">
        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
      </select>) },
  ]
  return (
    <div className="flex flex-col gap-6">
      <div>
        <Heading level={1} size={32}>Users &amp; roles</Heading>
        <Text variant="secondary" className="mt-1">Managers run and review plans; researchers also see experiment controls; admins manage roles. Enforced server-side. You cannot change your own role.</Text>
      </div>
      <Card><CardHeader title="Accounts" />
        <QueryBoundary query={users} skeleton={<Skeleton className="h-chart m-4" />}>{(rows) => <DataTable columns={columns} data={rows} rowKey={(u) => u.id} />}</QueryBoundary></Card>
    </div>
  )
}
