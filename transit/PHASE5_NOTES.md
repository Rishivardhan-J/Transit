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

### Late Deliveries KPI Instability Fix
- **The Issue**: The `Late Deliveries` metric fluctuated wildly across testing sessions because the initial seed time windows were only 2 to 6 hours in the future. The Celery beat task (`sweep_late_orders`) running every minute would continually sweep these orders into the `LATE` status as testing progressed, inflating the dashboard number unpredictably.
- **The Fix**: The `seed_dashboard.py` script was updated to push the simulated `time_window_start` and `time_window_end` out 5 to 7 days into the future. This safely freezes the beat sweep from automatically modifying the status of the seed data over time, keeping the KPI entirely deterministic and stable for testing and demonstration purposes.
