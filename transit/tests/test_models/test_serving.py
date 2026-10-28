"""Serving tests against the trained bundles (skipped when no model has been trained yet)."""
from datetime import datetime, timedelta

import numpy as np
import pytest

from src.cost_engine.travel_time import MLTravelTime
from src.data_processing.schemas import Order, Vehicle, VehicleType
from src.models.model_registry import load_bundle
from src.models.predict import predict_delivery_time


def _require(kind):
    try:
        return load_bundle(kind)
    except FileNotFoundError:
        pytest.skip(f"no trained '{kind}' bundle")


def _order(i=0):
    t = datetime(2025, 1, 6, 9, 0)
    return Order(order_id=f"o{i}", pickup_lat=34.05, pickup_lng=-118.25, delivery_lat=34.09, delivery_lng=-118.2,
                 demand_weight=3.0, time_window_start=t, time_window_end=t + timedelta(hours=2),
                 service_time_minutes=5, created_at=t - timedelta(hours=1))


def test_order_prediction_is_ordered_and_explained():
    _require("order")
    veh = Vehicle(vehicle_id="v", capacity=50, vehicle_type=VehicleType.CAR, fuel_efficiency=10,
                  available_from=datetime(2025, 1, 6, 8), available_until=datetime(2025, 1, 6, 18))
    p = predict_delivery_time(_order(), veh, None)
    assert 0 <= p.predicted_time_p10 <= p.predicted_time_p50 <= p.predicted_time_p90
    assert p.shap_top_features and {"feature", "value", "impact_minutes", "text"} <= set(p.shap_top_features[0])
    assert p.model_version.startswith("order_")


def test_ml_travel_time_matrix_shape_and_risk_ordering():
    _require("leg")
    rng = np.random.RandomState(0)
    coords = [(34.05, -118.25)] + [(34.05 + rng.uniform(-.05, .05), -118.25 + rng.uniform(-.05, .05)) for _ in range(25)]
    q = MLTravelTime("DLA3").quantile_matrices(coords)
    for m in q.values():
        assert m.shape == (26, 26) and np.allclose(np.diag(m), 0) and (m >= 0).all()
    assert (q["p10"] <= q["p50"] + 1e-9).all() and (q["p50"] <= q["p90"] + 1e-9).all()
    p50 = MLTravelTime("DLA3", 0.0).matrix(coords, None)
    p90 = MLTravelTime("DLA3", 1.0).matrix(coords, None)
    assert (p90 >= p50 - 1e-9).all()


def test_leg_model_beats_naive_baseline_and_is_calibrated():
    b = _require("leg")
    m = b.metadata
    assert m["metrics"]["test_mae_lift_vs_best_naive"] > 0.2
    assert abs(m["metrics"]["test_coverage80_cqr"] - 0.8) < 0.05
    assert not m["leakage_audit"]["forbidden_features_present"]
    assert m["time_ranges"]["train"][1] < m["time_ranges"]["test"][0]
