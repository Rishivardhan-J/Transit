import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from src.optimization.problem_builder import parse_solomon_instance, build_cvrptw_problem
from src.optimization.hgs_solver import solve_with_hgs
from src.optimization.baselines import solve_with_ortools, solve_with_nn
from src.cost_engine.config import CostWeights
from src.optimization.routing_metrics import compute_routing_metrics
import time

def run_benchmarks():
    benchmark_dir = Path("transit/data/benchmark/solomon")
    
    instances = ["C101.txt", "C201.txt", "R101.txt", "R201.txt", "RC101.txt", "RC201.txt"]
    weights = CostWeights.auto_normalize(1.0, 1.0, 0.0, 0.0)
    
    sintef_best_dist = {
        "C101.txt": 828.94,
        "C201.txt": 591.56,
        "R101.txt": 1650.80,
        "R201.txt": 1252.37,
        "RC101.txt": 1696.95,
        "RC201.txt": 1406.94
    }
    
    sintef_best_veh = {
        "C101.txt": 10,
        "C201.txt": 3,
        "R101.txt": 19,
        "R201.txt": 4,
        "RC101.txt": 14,
        "RC201.txt": 4
    }
    
    results = []
    
    print("Starting benchmarks...")
    for inst in instances:
        path = benchmark_dir / inst
        if not path.exists():
            print(f"Skipping {inst}, not found.")
            continue
            
        print(f"Processing {inst}...")
        try:
            orders, vehicles = parse_solomon_instance(str(path), num_customers=100)
            prob = build_cvrptw_problem(orders, vehicles, use_euclidean=True)
            
            # HGS
            t0 = time.time()
            routes_hgs = solve_with_hgs(prob, weights, max_runtime_seconds=30.0, max_iterations_no_improvement=5000)
            t_hgs = time.time() - t0
            metrics_hgs = compute_routing_metrics(routes_hgs)
            
            # OR-Tools
            t0 = time.time()
            routes_ortools = solve_with_ortools(prob, weights, max_runtime_seconds=30.0)
            t_ort = time.time() - t0
            metrics_ort = compute_routing_metrics(routes_ortools)
            
            # NN
            t0 = time.time()
            routes_nn = solve_with_nn(prob, weights)
            t_nn = time.time() - t0
            metrics_nn = compute_routing_metrics(routes_nn)
            
            metrics_hgs["total_distance_km"] *= 10
            metrics_ort["total_distance_km"] *= 10
            metrics_nn["total_distance_km"] *= 10
            
            best_d = sintef_best_dist[inst]
            gap_hgs = ((metrics_hgs["total_distance_km"] - best_d) / best_d) * 100.0 if metrics_hgs["total_distance_km"] > 0 else 0
            gap_ort = ((metrics_ort["total_distance_km"] - best_d) / best_d) * 100.0 if metrics_ort["total_distance_km"] > 0 else 0
            
            results.append({
                "Instance": inst,
                "HGS_Dist": metrics_hgs["total_distance_km"],
                "HGS_Veh": len(routes_hgs),
                "HGS_Gap": gap_hgs,
                "HGS_Time": t_hgs,
                "ORT_Dist": metrics_ort["total_distance_km"],
                "ORT_Veh": len(routes_ortools),
                "ORT_Gap": gap_ort,
                "ORT_Time": t_ort,
                "NN_Dist": metrics_nn["total_distance_km"],
                "NN_Veh": len(routes_nn),
                "Best_Known_Dist": best_d,
                "Best_Known_Veh": sintef_best_veh[inst]
            })
        except Exception as e:
            print(f"Failed to process {inst}: {e}")
            
    df = pd.DataFrame(results)
    os.makedirs("transit/results/figures", exist_ok=True)
    out_path = "transit/results/benchmark_summary.csv"
    df.to_csv(out_path, index=False)
    print(f"Benchmark summary saved to {out_path}")
    print(df.to_string())
    
    if not df.empty:
        # Plot Benchmark Gap
        plt.figure(figsize=(10, 6))
        x = range(len(df))
        plt.bar([i - 0.2 for i in x], df["HGS_Gap"], width=0.4, label='HGS Gap (%)')
        plt.bar([i + 0.2 for i in x], df["ORT_Gap"], width=0.4, label='OR-Tools Gap (%)')
        plt.xticks(x, df["Instance"])
        plt.ylabel("Gap to SINTEF Best Known (%)")
        plt.title("Routing Solver Performance vs Best Known Solutions")
        plt.legend()
        plt.savefig("transit/results/figures/benchmark_gap.png")
        plt.close()

if __name__ == "__main__":
    run_benchmarks()
