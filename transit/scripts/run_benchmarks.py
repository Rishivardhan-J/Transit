import pandas as pd
from pathlib import Path
from src.optimization.problem_builder import parse_solomon_instance, build_cvrptw_problem
from src.optimization.hgs_solver import solve_with_hgs
from src.cost_engine.config import CostWeights

def run_benchmarks():
    benchmark_dir = Path("transit/data/benchmark/solomon")
    instances = ["C101.txt", "R101.txt", "RC101.txt"]
    weights = CostWeights.auto_normalize(1.0, 1.0, 0.0, 0.0)
    
    results = []
    
    for inst in instances:
        path = benchmark_dir / inst
        if not path.exists():
            continue
            
        orders, vehicles = parse_solomon_instance(str(path), num_customers=25)
        prob = build_cvrptw_problem(orders, vehicles, use_euclidean=True)
        
        routes = solve_with_hgs(
            problem=prob,
            weights=weights,
            max_runtime_seconds=5.0,
            max_iterations_no_improvement=1000
        )
        
        results.append({
            "Instance": inst,
            "Customers": 25,
            "Vehicles Used": len(routes),
            "Total Cost": sum(r.total_cost for r in routes)
        })
        
    df = pd.DataFrame(results)
    out_path = "transit/results/benchmark_summary.csv"
    df.to_csv(out_path, index=False)
    print(f"Benchmark summary saved to {out_path}")
    print(df.to_string())

if __name__ == "__main__":
    run_benchmarks()
