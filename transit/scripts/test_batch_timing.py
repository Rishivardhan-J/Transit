import time
import sys
from src.optimization.problem_builder import parse_solomon_instance, build_cvrptw_problem
from src.optimization.hgs_solver import solve_with_hgs
from src.cost_engine.config import CostWeights

def measure_batch_timing():
    print("Testing batch timing for a duplicated 200-order instance...")
    
    # Load 100 customers from C101
    orders, vehicles = parse_solomon_instance("transit/data/benchmark/solomon/C101.txt", num_customers=100)
    
    # Duplicate the orders to create a 200-order instance
    new_orders = []
    for i, order in enumerate(orders):
        dup = order.model_copy(deep=True)
        dup.order_id = f"{order.order_id}_dup"
        new_orders.append(dup)
        
    all_orders = orders + new_orders
    
    print(f"Total orders: {len(all_orders)}")
    prob = build_cvrptw_problem(all_orders, vehicles)
    weights = CostWeights.auto_normalize(1.0, 1.0, 0.0, 0.0)
    
    # Disclaimer: duplicated coordinates/demands are not a realistic routing problem!
    # Solution quality on this test is meaningless; only the timing number is valid.
    
    t0 = time.time()
    # Give it a 30 second budget to see if it finishes early or exactly hits the budget gracefully
    routes = solve_with_hgs(prob, weights, max_runtime_seconds=30.0)
    duration = time.time() - t0
    
    print(f"Batch solve completed in {duration:.2f} seconds.")
    if duration <= 35.0: # Giving 5s margin for overhead
        print("PASS: Batch solve is within target threshold.")
        sys.exit(0)
    else:
        print("FAIL: Batch solve took too long.")
        sys.exit(1)

if __name__ == "__main__":
    measure_batch_timing()
