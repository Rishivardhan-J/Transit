import type { PlanStatus } from '../design-system/tokens'

export type Role = 'manager' | 'researcher' | 'admin'

export interface Stop {
  order_id: string; lat: number; lng: number; priority: string
  planned_arrival: string; p10: string | null; p50: string | null; p90: string | null
  window_start: string; window_end: string; slack_min: number | null
  status: Exclude<PlanStatus, 'unassigned'>  // 'pending' is only used by the replay view
}
export interface PlanRoute { route_id: string; vehicle_id: string; total_distance_km: number; total_time_min: number; total_cost: number; stops: Stop[] }
export interface Unassigned { order_id: string; reason: string; lat?: number; lng?: number; priority?: string }
export interface Metrics {
  total_distance: number; total_time_min: number; total_cost: number; vehicles_used: number; late_deliveries: number
  utilization_pct: number; orders_assigned: number; orders_unassigned: number; predicted_late: number
  predicted_late_ids?: string[]; violations: string[]; feasible: boolean; runtime_s: number; cost_per_order: number | null
}
export interface Plan {
  run_id: string; solver: string; time_model: string | null; depot: { lat: number; lng: number } | null
  routes: PlanRoute[]; unassigned: Unassigned[]; metrics?: Metrics; baseline_metrics?: Metrics | null
  parent_run_id?: string | null; event?: { type: string } | null; created_at?: string
}
export interface ModelSummary { version: string; unit: string; mae: number; r2: number; coverage80: number }
export interface Kpis {
  fleet_utilization_pct: number; active_routes: number; late_deliveries: number; predicted_late: number
  cost_vs_baseline_pct: number | null; baseline: string; benchmark_hgs_vs_ortools_pct: number | null
  latest_run: { id: string; solver: string; time_model: string | null; created_at: string | null; unassigned: number } | null
  model: { leg: ModelSummary | null; order: ModelSummary | null }
}
export interface Vehicle { vehicle_id: string; capacity: number; vehicle_type: string; fuel_efficiency: number; available_from: string; available_until: string; current_lat: number | null; current_lng: number | null }
export interface RunSummary { id: string; created_at: string | null; solver: string; status: string; parent_run_id: string | null; event: { type: string } | null; runtime_s: number | null; time_model: string | null; metrics: Metrics | null; unassigned_count: number }
export interface Weights { w_distance: number; w_time: number; w_fuel: number; w_delay: number }
export interface WhatIfResponse {
  committed: boolean; weights: Weights; plan: Plan; metrics: Metrics; baseline: Metrics | null
  current_metrics: Metrics | null; delta_vs_current: Record<string, number> | null
}
export interface Explanation {
  order_id: string; status?: PlanStatus; model_version: string; route_id?: string; stop_index?: number; n_stops?: number
  arrival?: { p10: string; p50: string; p90: string }; window_end?: string | null
  leg_minutes?: { p10: number; p50: number; p90: number }
  predicted_eta_mins: number; p10_mins: number; p50_mins: number; p90_mins: number
  shap_values: { feature: string; value: number; text?: string }[]
}
export interface SolverRow { solver: string; total_distance: number; total_time_min: number; total_cost: number; vehicles_used: number; predicted_late: number; late_deliveries: number; utilization_pct: number; orders_assigned: number; orders_unassigned: number; runtime_s: number; feasible: boolean }
export interface BenchmarkRow { Instance: string; HGS_Dist: number; HGS_Veh: number; HGS_Gap: number; ORT_Dist: number; ORT_Veh: number; ORT_Gap: number; NN_Dist: number; NN_Veh: number; NN_Gap: number; NN_Unassigned: number; Best_Known_Dist: number; Best_Known_Veh: number; HGS_Viol: number; ORT_Viol: number; NN_Viol: number }
export interface ReplayStop { order_id: string; stop_index: number; lat: number | null; lng: number | null; planned: string; actual: string; window_end: string; late: boolean; error_min: number }
export interface Replay { run_id: string; simulated: boolean; depot: { lat: number; lng: number } | null; routes: { route_id: string; vehicle_id: string; stops: ReplayStop[] }[]; summary: { stops: number; mae_min: number | null; planned_late: number; actual_late: number } }
export interface Quantile { MAE: number; RMSE: number; R2: number; WAPE: number }
export interface Bundle { version: string; kind: string; dataset: string; unit: string; active: boolean; created_at: string; metrics: Record<string, number>; baselines: Record<string, Quantile>; comparison: Record<string, Quantile>; rows: { train: number; val: number; test: number }; leakage_audit?: { note: string; r2_above_0_97?: boolean } }
export interface ModelPerformance { runs: { run_id: string; dataset: string | null; bundle: string | null; metrics: Record<string, number>; timestamp: string }[]; bundles: Bundle[] }
export interface Hist { bin: string; lo: number; hi: number; count: number }
export interface EdaSummary {
  available: string[]; dataset: string
  summary: null | {
    title: string; rows: number; target: string
    distributions: Record<string, Hist[]>
    boxplots: Record<string, { min: number; q1: number; median: number; q3: number; max: number; outliers: number; n: number }>
    correlation: { x: string; y: string; value: number }[]
    categories: Record<string, { category: string; count: number }[]>
    traffic_vs_time?: Record<string, number | string>[]
  }
  importance: null | { version: string; spearman: number; features: { feature: string; impurity: number; permutation: number; shap_mean_abs: number }[] }
}
export interface UploadReport { filename: string; total: number; valid: number; error_count: number; errors: { row_index: number; field: string; message: string }[]; committed: boolean; created: number }
export interface UserRow { id: string; email: string; role: Role }
export type DisruptionEvent =
  | { type: 'new_order'; order: Record<string, unknown> }
  | { type: 'cancel_order'; order_id: string }
  | { type: 'vehicle_down'; vehicle_id: string }
  | { type: 'traffic_change'; time_multiplier: number }
export interface Diagnostics {
  version: string; unit: string; n: number
  points: { actual: number; p50: number; p10: number; p90: number }[]
  residual_hist: { bin: string; count: number }[]
  coverage: { raw: number; calibrated: number; target: number }
}
