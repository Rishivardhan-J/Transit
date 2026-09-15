import pytest
from src.cost_engine.config import CostWeights, PRIORITY_MULTIPLIERS
from src.cost_engine.cost_function import compute_delay_penalty, compute_fuel_cost, compute_edge_cost
from src.cost_engine.distance_matrix import distance_matrix_service

def test_cost_weights_sum_to_one():
    # Valid weights
    cw = CostWeights(w_distance=0.2, w_time=0.3, w_fuel=0.4, w_delay=0.1)
    assert cw.w_distance == 0.2
    
    # Invalid weights
    with pytest.raises(ValueError):
        CostWeights(w_distance=0.5, w_time=0.5, w_fuel=0.5, w_delay=0.5)

def test_auto_normalize():
    cw = CostWeights.auto_normalize(1.0, 1.0, 1.0, 1.0)
    assert cw.w_distance == 0.25
    assert cw.w_time == 0.25
    assert cw.w_fuel == 0.25
    assert cw.w_delay == 0.25
    
    cw2 = CostWeights.auto_normalize(2.0, 0.0, 0.0, 0.0)
    assert cw2.w_distance == 1.0
    assert cw2.w_time == 0.0

def test_compute_delay_penalty():
    # On time
    assert compute_delay_penalty(10.0, 15.0, "high") == 0.0
    
    # Late by 5 mins, standard priority
    assert compute_delay_penalty(20.0, 15.0, "standard") == 5.0
    
    # Late by 5 mins, urgent priority
    assert compute_delay_penalty(20.0, 15.0, "urgent") == 5.0 * 5.0

def test_compute_fuel_cost():
    # 10km, 10km/L, $1.5/L -> 1L -> $1.5
    assert compute_fuel_cost(10.0, 10.0, 1.5) == 1.5

def test_compute_edge_cost():
    weights = CostWeights(w_distance=0.5, w_time=0.5, w_fuel=0.0, w_delay=0.0)
    # dist=10, time=20 -> 5 + 10 = 15
    cost = compute_edge_cost(
        distance_km=10.0,
        predicted_time_min=20.0,
        fuel_efficiency=10.0,
        priority="standard",
        arrival_time_min=10.0,
        time_window_end=15.0,
        weights=weights,
        is_infeasible=False
    )
    assert cost == 15.0

    # Infeasible applies constraint penalty
    cost_infeasible = compute_edge_cost(
        distance_km=10.0,
        predicted_time_min=20.0,
        fuel_efficiency=10.0,
        priority="standard",
        arrival_time_min=10.0,
        time_window_end=15.0,
        weights=weights,
        is_infeasible=True
    )
    assert cost_infeasible == 15.0 + 10000.0

def test_distance_matrix():
    coords = [(0.0, 0.0), (0.0, 1.0)]
    matrix = distance_matrix_service.build_matrix(coords)
    assert matrix.shape == (2, 2)
    assert matrix[0, 0] == 0.0
    assert matrix[1, 1] == 0.0
    assert matrix[0, 1] > 110.0 # 1 degree of long at equator is ~111km
    assert matrix[1, 0] == matrix[0, 1]
