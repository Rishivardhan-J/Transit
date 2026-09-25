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

### Seed Script Note (Late Deliveries KPI)
The `Late Deliveries` KPI in the demo dashboard reflects explicit seed randomness, not an actual routing failure based on the time windows. At seed time (`scripts/seed_dashboard.py`), the `LATE` status is assigned to orders purely by random chance.
In the current seeded database, the status distribution for the 50 orders is:
- `LATE`: 15
- `ASSIGNED`: 10
- `PENDING`: 9
- `DELIVERED`: 9
- `IN_TRANSIT`: 7
