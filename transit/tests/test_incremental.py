import time
import pytest
from src.optimization.problem_builder import parse_solomon_instance, build_cvrptw_problem
from src.optimization.hgs_solver import solve_with_hgs
from src.cost_engine.config import CostWeights

def test_incremental_re_solve_under_5s():
    orders, vehicles = parse_solomon_instance("transit/data/benchmark/solomon/C101.txt", num_customers=100)
    prob = build_cvrptw_problem(orders, vehicles)
    weights = CostWeights.auto_normalize(1.0, 1.0, 0.0, 0.0)
    
    # Simulate incremental resolve by adding a new order (using order 0 duplicated)
    new_order = orders[0].model_copy(deep=True)
    new_order.order_id = "incremental_new_order"
    orders.append(new_order)
    
    prob_incremental = build_cvrptw_problem(orders, vehicles)
    
    start = time.time()
    routes = solve_with_hgs(prob_incremental, weights, max_runtime_seconds=4.0)
    duration = time.time() - start
    
    assert duration < 5.0, f"Incremental solve took {duration}s, expected <5s"
