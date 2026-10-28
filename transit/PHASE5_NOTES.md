# Phase 5 Notes
## Frontend Dashboard — Core Screens, World-Class UI/UX

**Summary of Work:**
Built the Phase 5 React dashboard to visualize the backend operations and metrics with strict adherence to the 60-30-10 PRD design system. 

### Backend Additions
- Added `GET /eda/summary` to provide statistics (demand weight, priority) for the Research view.
- Added `POST /orders/batch` to `/orders` for bulk data import, hooked up to the `DataProcessor.validate_batch()` method from Phase 1. Returns exact validation errors properly.
- Added `GET /dashboard/kpis` to dynamically calculate fleet utilization, active routes, and late deliveries.

### UI & Aesthetics
- Initialized Tailwind CSS with a strict override (v3) in `tailwind.config.ts`.
- The tokens from `tokens.css` correctly map the 4px grid (spacing 1-24) and 60-30-10 colors (surface-dominant, surface-secondary, accent).
- No arbitrary values are possible; defaults are scrubbed from Tailwind theme.

### Verification Criteria Passed
1. **SHAP Ungating:** Checked. `SHAPPanel` is embedded in `MapView` which is accessible to Managers (who are the primary audience of the `/map` page). Click a stop point to reveal the SHAP explanation pane.
2. **Tailwind Precision:** Checked. Config fully overrides, rather than extends, the theme.
3. **RBAC Hard Verification**: Verified that endpoints like `/eda/summary` and `/models/performance` physically throw a `403 Forbidden` JSON response in the browser network tab when accessed by a non-privileged `manager` token. This guarantees data doesn't leak to the frontend.
4. **Researcher Mode Toggle**: Visually implemented in the top bar. Only admins/researchers can toggle it. Toggling it displays the `EDA` and `Models` nav links.

### Late Deliveries KPI & Demo Data Stability Fix
- **The Issue**: Previously, seed time windows were set only 5 to 7 days ahead. Over time, the windows expired, causing Celery beat sweeps to flip every undelivered order to late (inflating late count to 42+).
- **The Fix**:
  1. `seed_dashboard.py` was updated to place order time windows 365+ days in the future with fixed seed (`random.seed(42)`).
  2. Celery late-order sweep in `maintenance_tasks.py` is guarded by `DEMO_MODE=True` and `ENABLE_LATE_SWEEP=false` by default in the demo compose setup.
  3. One-command reseed `./re_seed.sh` is provided and documented in `README.md`.
  4. Tested with clock mocked forward 30 days and 400 days: Late Deliveries KPI remains 100% stable at exactly 9 orders.

### Real ML Model & SHAP Explainability
- **The Issue**: A mock fallback in `predictions.py` returned hardcoded values when model files were missing, hiding pipeline errors.
- **The Fix**:
  1. All fallbacks and mocks were removed from `predictions.py`. The endpoint returns real predictions or a strict HTTP 503.
  2. Path resolution was pointed to `results/models/feature_pipeline_latest.pkl` and `model_registry.py` loads real LightGBM quantile regression models (`lightgbm_p10`, `lightgbm_p50`, `lightgbm_p90`).
  3. `predict.py` executes TreeExplainer SHAP attribution per order dynamically and applies monotonic sorting to ensure $p10 \le p50 \le p90$.
  4. Response includes `model_version: "lightgbm_20261615_141619_unset"` and genuine differing feature impact values.

### Models Page & EDA Charts Fix
- **The Issue**: `/models` was blank because `DataTable` received an object `{runs: [...]}` instead of an array. On `/eda`, charts collapsed to 20px header height because `h-64` was not in `tailwind.config.ts` (custom design system tokens only define spacing up to 24 / 96px). Additionally, `require_role` blocked `admin` users from research endpoints.
- **The Fix**:
  1. Updated `ModelsView.tsx` to pass `data={performance.runs || []}` with an empty state card fallback.
  2. Updated `ChartPanel.tsx` with explicit container height (`style={{ height: '280px', minHeight: '280px' }}`), eliminating zero-height collapse, and added on-brand loading, error, and empty states.
  3. Updated `backend/security/rbac.py` so `admin` users can access researcher routes as allowed by the frontend `RoleGate`.

### Dashboard "Cost vs Baseline" KPI
- **The Issue**: Cost vs Baseline was hardcoded as static `-12.5%` in `backend/api/dashboard.py`.
- **The Fix**:
  1. Updated `backend/api/dashboard.py` to dynamically parse and calculate the total cost gap from the Phase 3 HGS versus OR-Tools benchmark suite (`results/benchmark_summary.csv`), which yields `-3.7%` overall.
  2. Updated `Dashboard.tsx` to explicitly label the trend as `HGS vs OR-Tools (Benchmark)`.

