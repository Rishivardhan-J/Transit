# Implementation notes

What was wrong, what changed, and what to be careful about.

## What the first version got wrong (found in the audit)

| Area | Problem | Fix |
|---|---|---|
| Optimizer benchmark | Solomon coordinates were divided by 10 and times set equal to distance, so travel was 10× too short; HGS "beat" best-known R101 by 15% with 14 vehicles (best known: 19). | Raw-unit problems plus a solver-independent route simulator. Benchmarks now match best-known; every violation count is 0. |
| HGS | `w_delay` always 0, one vehicle type, same total cost on every route, infeasible runs returned `[]`. | Mixed fleets, per-route cost from the cost engine, optional clients with an explicit unassigned set, feasibility repair when PyVRP's best is infeasible (found by a property test). |
| ML target | Amazon target was `stops × 3.5` with random coordinates; coordinates and vehicle type identified the source dataset; `status` (a post-outcome field) was a feature; R² ≈ 0.75 measured dataset classification. | 898k real stop-to-stop legs, pre-trip features only, grouped chronological split, naive baselines, conformal calibration. |
| Backend | Jobs only `sleep()`ed and wrote no routes; `/models` and `/eda` were hard-coded; any user with password `admin` could log in; anyone could register as admin; WebSockets were unauthenticated. | Real pipeline (solve, persist routes, predictions, SHAP) and all of the above fixed. |
| UI | 4 of 8 screens; many Tailwind classes produced no CSS; Inter never loaded; categorical colours reused status green/red. | Rebuilt on tokens; all screens present; named layout tokens. |

## Models: how to read the numbers

* **Leg model** (drives routing): test R² 0.946 is plausible rather than suspicious because Amazon's matrix is largely a function of geometry (haversine alone correlates 0.935). The meaningful numbers are the lift over naive speed baselines (56% lower MAE: 20.9 s vs 47 s) and calibration (79.6% coverage at a nominal 80%).
* **Top features** (permutation): `direct_km`, `dlng`, `stop_idx`, `to_lng`, `to_station_km`. All are known before the leg is driven. `stop_idx` ranking third deserves a skeptical look (PRD checkpoint 18.1): it is plan-time information but may proxy route structure.
* **Order model** (Food Delivery): distance, prep time, weather, traffic, courier experience, as expected. Only 1,000 rows, so test coverage (75%) is noisy.
* Leakage guards: the delay-history feature uses strictly earlier dates from a train-only table (tested); post-outcome columns are asserted absent; R² > 0.97 is flagged for manual review.

## Routing

* Benchmarks use a hierarchical objective (vehicle fixed cost much larger than distance). Nearest-neighbour "negative gaps" in raw distance only occur where it leaves orders unrouted; the table shows unrouted counts.
* Warm start: repair (cheapest feasible insertion), then PyVRP `initial_solution`, then a short HGS pass. 60 orders: new order / cancel / vehicle down ≈ 0.7 s, traffic change ≈ 1.5 s.
* Not measured: a realistic 200-order demo-city solve with ML travel times. The existing 200-order timing script duplicates a Solomon instance and measures wall clock only.

## Known limitations

* Single depot; accumulated arrival uncertainty assumes independent leg errors; a fixed -20%/+30% band is used when no leg model exists.
* No Redis in the development sandbox: integration tests run tasks eagerly, and the WebSocket path is covered by a mocked Redis plus the polling fallback.
* The Mapbox map could not be exercised end to end without a token. The component, runtime retint and route morph are implemented and typechecked, and every non-map screen was walked with Playwright as each role with no console errors.
* `results/models` and processed data are git-ignored; regenerate with `make data train`.
