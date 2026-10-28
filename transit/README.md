# Transit

Real-time logistics optimization: predict travel times with calibrated uncertainty, route a fleet with Hybrid Genetic Search under capacity and time-window constraints, and explain every flagged stop.

```
Historical data ─► features ─► LightGBM quantiles (p10/p50/p90, conformal-calibrated) ─► versioned model bundle
                                                                                       │
Orders ─► dynamic cost engine (ML travel times + weights) ─► HGS (PyVRP) ─► plan ─► API ─► React dashboard
              ▲                                                  │
              └──────── disruption (new/cancel/vehicle down/traffic) ─► warm-start re-solve
```

## Quick start (no Docker, no Redis)

```bash
python -m venv ../venv && ../venv/bin/pip install -r requirements.txt
make seed                       # SQLite demo DB: users + one real HGS plan on a Los Angeles demo city
make dev                        # API on :8000, jobs run inline
cd frontend && cp .env.example .env   # add VITE_MAPBOX_TOKEN (public pk.* token), then:
npm install && npm run dev      # UI on :5173
```

Demo logins (password `transit-demo`): `manager@transit.com`, `researcher@transit.com`, `admin@transit.com`.
Researchers/admins get a **Research mode** switch in the user menu (EDA and Models screens); admins also get Users.

Full stack: `docker compose up --build`, then `./re_seed.sh` (UI :3000, API :8000, MLflow :5000). Set `VITE_MAPBOX_TOKEN` in the environment before building the frontend image.

## Reproducing the models and benchmarks

| Step | Command | Needs |
|---|---|---|
| Food delivery set | `python -m src.data_processing.process_food_delivery` | Kaggle `Food_Delivery_Times.csv` in `data/raw/food_delivery/` |
| Amazon leg set (~900k legs) | `python -m src.data_processing.build_amazon_legs` | Amazon Last Mile JSON files in `data/raw/amazon_last_mile/` (streamed; ~1 min) |
| Train + register | `make train` | ~5 min for legs on 16 cores |
| Solomon benchmark | `make bench` | `data/benchmark/solomon/*.txt` |
| Tests | `make test` | |

Everything is seeded (`RANDOM_SEED=42`), tracked in MLflow (`results/mlruns.db`), and each model is an immutable bundle under `results/models/<kind>_<time>_<gitsha>/` (pipeline + models + calibration + metrics + importances).

## Results (see `docs/IMPLEMENTATION_NOTES.md` for the full picture and caveats)

* **Routing (Solomon 100-customer, vehicles-first then distance):** HGS matches the best-known solution on C101, C201, R101, R201, RC101 and is +0.05% on RC201, with zero constraint violations on every solver (checked by an independent evaluator). OR-Tools is 0–9% worse; nearest neighbour is far worse or leaves orders unrouted.
* **Travel time (Amazon legs, chronological split):** MAE 20.9 s vs 47 s for the best naive baseline (56% better), R² 0.946, 80% interval covers 79.6%.
* **Delivery time (Food Delivery):** MAE 7.3 min vs 16.5 min naive, R² 0.738.
* Re-solve after a disruption: ~1–2 s for 60 orders; what-if re-solve: ~2 s.

## Design decisions

* **Infeasibility policy:** every order is optional with a large prize, so the solver always returns a feasible plan. Orders that cannot be served are returned in an explicit `unassigned` list with a reason (capacity, unreachable window, no vehicle-time) and shown in the UI. Nothing is dropped silently.
* **Cost engine:** `w_distance·km + w_fuel·fuel + w_time·duration + w_delay·priority-weighted lateness`, weights auto-normalized to 1. `w_delay` also tightens the windows of high/urgent orders and scales the value of serving them.
* **Planning caution:** `risk_lambda` plans on `p50 + λ(p90−p50)` leg times. Per-stop arrival intervals accumulate leg uncertainty as independent errors (an approximation); a stop is "at risk" when its p90 arrival is past the deadline.
* **Scale target:** ≤200 orders / ≤20 vehicles per solve, ~5,000 orders/day. Single depot, documented limitation (the problem dict allows multi-depot later).
* **Roles:** manager, researcher, admin enforced server-side (403), `/auth/register` always creates managers, WebSockets require the JWT.

## Deviations from the PRD

* The Command Navy *muted* text colour (#64748B) is below WCAG AA on both surfaces (3.75:1 / 3.07:1, see `make contrast`). It is used only for icons; text uses the secondary colour.
* Amazon "travel times" are Amazon's modelled matrix, not GPS actuals, and are not time-dependent. Time-of-day effects come from the speed profile / Food Delivery data. NYC Taxi was not available (Kaggle competition download).
* Replay actuals are simulated from the calibrated leg distributions (no live GPS in v1).
* Hyper-parameters are tuned (Optuna) on p50 and shared with p10/p90; tuning uses a 150k-row subsample.
* Map requires your own Mapbox token (`VITE_MAPBOX_TOKEN`); the dark-v11 style is retinted at runtime instead of in Mapbox Studio.
