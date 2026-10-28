"""Solomon 100-customer benchmark: HGS vs OR-Tools vs Nearest Neighbour.

Objective is the standard hierarchical one (vehicles first, then distance), approximated with a
large per-vehicle fixed cost. Every solution is re-checked by the solver-independent evaluator;
`*_Viol` counts constraint violations and must be 0.
"""
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.cost_engine.config import CostWeights
from src.optimization.baselines import solve_nn, solve_ortools
from src.optimization.hgs_solver import solve_hgs
from src.optimization.problem_builder import SOLOMON_COORD_SCALE, build_cvrptw_problem, parse_solomon_instance
from src.optimization.routing_metrics import evaluate_solution
from src.paths import BENCHMARK_DIR, FIGURES_DIR, RESULTS_DIR

BEST_KNOWN = {  # SINTEF: (distance, vehicles)
    "C101": (828.94, 10), "C201": (591.56, 3), "R101": (1650.80, 19),
    "R201": (1252.37, 4), "RC101": (1696.95, 14), "RC201": (1406.94, 4),
}
FIXED_COST = 1000.0
SEEDS = (1, 2, 3)
BUDGET_S = float(os.environ.get("BENCH_BUDGET_S", 20))


def run_benchmarks():
    weights = CostWeights(w_distance=1.0, w_time=0.0, w_fuel=0.0, w_delay=0.0)
    rows = []
    for inst, (best_d, best_v) in BEST_KNOWN.items():
        path = BENCHMARK_DIR / "solomon" / f"{inst}.txt"
        if not path.exists():
            print(f"Skipping {inst}: {path} not found")
            continue
        print(f"Processing {inst}...")
        orders, vehicles = parse_solomon_instance(str(path), num_customers=100)
        prob = build_cvrptw_problem(orders, vehicles, use_euclidean=True, coord_scale=SOLOMON_COORD_SCALE)

        hgs_runs = []
        for seed in SEEDS:
            r = solve_hgs(prob, weights, BUDGET_S, 5000, seed=seed, vehicle_fixed_cost=FIXED_COST)
            hgs_runs.append((r, evaluate_solution(r.routes, prob, weights, r.unassigned)))
        r_h, m_h = min(hgs_runs, key=lambda x: (-x[1]["orders_assigned"], x[1]["vehicles_used"], x[1]["total_distance"]))
        r_o = solve_ortools(prob, weights, BUDGET_S, vehicle_fixed_cost=FIXED_COST)
        m_o = evaluate_solution(r_o.routes, prob, weights, r_o.unassigned)
        r_n = solve_nn(prob, weights)
        m_n = evaluate_solution(r_n.routes, prob, weights, r_n.unassigned)

        gap = lambda d: (d - best_d) / best_d * 100.0
        rows.append({
            "Instance": inst,
            "HGS_Dist": m_h["total_distance"], "HGS_Veh": m_h["vehicles_used"], "HGS_Gap": gap(m_h["total_distance"]),
            "HGS_Time": r_h.runtime_s, "HGS_Dist_Mean": sum(m["total_distance"] for _, m in hgs_runs) / len(hgs_runs),
            "HGS_Unassigned": m_h["orders_unassigned"], "HGS_Viol": len(m_h["violations"]),
            "ORT_Dist": m_o["total_distance"], "ORT_Veh": m_o["vehicles_used"], "ORT_Gap": gap(m_o["total_distance"]),
            "ORT_Time": r_o.runtime_s, "ORT_Unassigned": m_o["orders_unassigned"], "ORT_Viol": len(m_o["violations"]),
            "NN_Dist": m_n["total_distance"], "NN_Veh": m_n["vehicles_used"], "NN_Gap": gap(m_n["total_distance"]),
            "NN_Unassigned": m_n["orders_unassigned"], "NN_Viol": len(m_n["violations"]),
            "Best_Known_Dist": best_d, "Best_Known_Veh": best_v,
        })
        print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in rows[-1].items()})

    df = pd.DataFrame(rows)
    os.makedirs(FIGURES_DIR, exist_ok=True)
    out = RESULTS_DIR / "benchmark_summary.csv"
    df.to_csv(out, index=False)
    print(f"Saved {out}")
    if not df.empty:
        x = range(len(df))
        plt.figure(figsize=(10, 6))
        plt.bar([i - 0.27 for i in x], df["HGS_Gap"], width=0.27, label="HGS")
        plt.bar([i for i in x], df["ORT_Gap"], width=0.27, label="OR-Tools")
        plt.bar([i + 0.27 for i in x], df["NN_Gap"], width=0.27, label="Nearest Neighbour")
        plt.xticks(list(x), df["Instance"])
        plt.ylabel("Distance gap to best-known (%)")
        plt.legend()
        plt.savefig(FIGURES_DIR / "benchmark_gap.png")
        plt.close()


if __name__ == "__main__":
    run_benchmarks()
