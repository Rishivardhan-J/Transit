import { apiClient } from './client'
import type {
  Diagnostics,
  BenchmarkRow, DisruptionEvent, EdaSummary, Explanation, Kpis, ModelPerformance, Plan, Replay, RunSummary,
  SolverRow, UploadReport, UserRow, Vehicle, Weights, WhatIfResponse,
} from './types'

const get = async <T,>(url: string, params?: object) => (await apiClient.get<T>(url, { params })).data

export const api = {
  login: async (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password })
    const { data } = await apiClient.post<{ access_token: string }>('/auth/login', body, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
    return data.access_token
  },
  me: () => get<UserRow>('/users/me'),
  kpis: () => get<Kpis>('/dashboard/kpis'),
  vehicles: () => get<Vehicle[]>('/vehicles'),
  runs: (limit = 25) => get<RunSummary[]>('/optimizer-runs', { limit }),
  plan: (runId: string) => get<Plan>(`/optimizer-runs/${runId}`),
  latestPlan: async (): Promise<Plan | null> => {
    const runs = await get<RunSummary[]>('/optimizer-runs', { limit: 10 })
    const latest = runs.find((r) => r.status === 'completed')
    return latest ? get<Plan>(`/optimizer-runs/${latest.id}`) : null
  },
  optimize: async (body: { solver_type: string; weight_config: object; risk_lambda?: number; max_runtime_s?: number }) =>
    (await apiClient.post<{ job_id: string }>('/routes/optimize', body)).data,
  job: (id: string) => get<{ status: string; optimizer_run_id?: string; error?: string; result?: Record<string, unknown> }>(`/jobs/${id}`),
  whatIf: async (w: Weights, opts: { commit?: boolean; max_runtime_s?: number } = {}) =>
    (await apiClient.post<WhatIfResponse>('/routes/whatif', { ...w, ...opts })).data,
  disrupt: async (event: DisruptionEvent) => (await apiClient.post<{ job_id: string }>('/routes/disrupt', { event })).data,
  explain: (orderId: string) => get<Explanation>(`/predictions/${orderId}/explain`),
  replay: (runId: string) => get<Replay>(`/replay/${runId}`),
  benchmarks: () => get<BenchmarkRow[]>('/benchmarks/solver-comparison'),
  compareLive: async (w: Weights, max_runtime_s = 10) =>
    (await apiClient.post<{ orders: number; vehicles: number; time_model: string; solvers: SolverRow[] }>('/benchmarks/compare-live', { ...w, max_runtime_s })).data,
  models: () => get<ModelPerformance>('/models/performance'),
  diagnostics: (kind: string) => get<Diagnostics>('/models/diagnostics', { kind }),
  eda: (dataset: string) => get<EdaSummary>('/eda/summary', { dataset }),
  upload: async (file: File, commit: boolean) => {
    const form = new FormData()
    form.append('file', file)
    return (await apiClient.post<UploadReport>('/orders/upload', form, { params: { commit }, headers: { 'Content-Type': 'multipart/form-data' } })).data
  },
  users: () => get<UserRow[]>('/users'),
  setRole: async (id: string, role: string) => (await apiClient.patch<UserRow>(`/users/${id}/role`, { role })).data,
}
