import pytest

def test_metrics_endpoint(client):
    # Hit an endpoint to generate a metric
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "request_count" in response.text
    assert "request_latency_seconds" in response.text

def test_predictions_endpoint(client, override_user, mock_researcher_user):
    override_user(mock_researcher_user)
    payload = {
        "order": {
            "order_id": "ord-pred-1",
            "pickup_lat": 40.7128,
            "pickup_lng": -74.0060,
            "delivery_lat": 40.7300,
            "delivery_lng": -73.9900,
            "demand_weight": 10.5,
            "priority": "standard",
            "time_window_start": "2024-01-01T10:00:00Z",
            "time_window_end": "2050-01-01T12:00:00Z",
            "service_time_minutes": 5,
            "created_at": "2020-01-01T10:00:00Z",
            "status": "pending"
        },
        "vehicle": {
            "vehicle_id": "veh-pred-1",
            "capacity": 50.0,
            "vehicle_type": "truck",
            "fuel_efficiency": 10.0,
            "available_from": "2024-01-01T08:00:00Z",
            "available_until": "2024-01-01T20:00:00Z"
        }
    }
    response = client.post("/predictions/eta", json=payload)
    assert response.status_code == 200
    assert "predicted_time_p50" in response.json()

def test_explain_real_model_predictions(client, override_user, mock_manager_user, db_session, monkeypatch):
    from datetime import datetime, timezone
    from backend.models_db.order import DBOrder
    from backend.models_db.vehicle import DBVehicle
    from backend.models_db.route import DBRoute
    from backend.models_db.optimizer_run import DBOptimizerRun
    from src.data_processing.schemas import Priority, OrderStatus, VehicleType
    
    # 1. Ensure TESTING is completely unset
    monkeypatch.delenv("TESTING", raising=False)
    override_user(mock_manager_user)
    
    opt_run = DBOptimizerRun(
        id="opt-real-1",
        solver_type="hgs",
        weight_config={"distance": 1.0},
        status="completed"
    )
    db_session.add(opt_run)
    
    veh = DBVehicle(
        vehicle_id="veh-real-1",
        capacity=100.0,
        vehicle_type=VehicleType.TRUCK,
        fuel_efficiency=10.0,
        available_from=datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc),
        available_until=datetime(2024, 1, 1, 20, 0, tzinfo=timezone.utc),
        current_lat=40.71,
        current_lng=-74.00
    )
    db_session.add(veh)
    
    ord1 = DBOrder(
        order_id="ORD-TEST-1",
        pickup_lat=40.7128,
        pickup_lng=-74.0060,
        delivery_lat=40.7300,
        delivery_lng=-73.9900,
        demand_weight=10.0,
        priority=Priority.STANDARD,
        time_window_start=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        time_window_end=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        service_time_minutes=5.0,
        created_at=datetime(2020, 1, 1, 10, 0, tzinfo=timezone.utc),
        status=OrderStatus.ASSIGNED
    )
    ord2 = DBOrder(
        order_id="ORD-TEST-2",
        pickup_lat=40.7800,
        pickup_lng=-73.9600,
        delivery_lat=40.8500,
        delivery_lng=-73.9200,
        demand_weight=35.0,
        priority=Priority.URGENT,
        time_window_start=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        time_window_end=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        service_time_minutes=15.0,
        created_at=datetime(2020, 1, 1, 10, 0, tzinfo=timezone.utc),
        status=OrderStatus.ASSIGNED
    )
    db_session.add(ord1)
    db_session.add(ord2)
    
    route = DBRoute(
        route_id="RT-TEST-1",
        vehicle_id="veh-real-1",
        ordered_stops=["ORD-TEST-1", "ORD-TEST-2"],
        predicted_arrival_times=["2024-01-01T10:30:00Z", "2024-01-01T11:15:00Z"],
        total_distance_km=25.0,
        total_predicted_time_min=60.0,
        total_cost=45.0,
        optimizer_run_id="opt-real-1"
    )
    db_session.add(route)
    db_session.commit()
    
    resp1 = client.get("/predictions/ORD-TEST-1/explain")
    resp2 = client.get("/predictions/ORD-TEST-2/explain")
    
    assert resp1.status_code == 200, f"resp1 failed: {resp1.text}"
    assert resp2.status_code == 200, f"resp2 failed: {resp2.text}"
    
    data1 = resp1.json()
    data2 = resp2.json()
    
    # Must contain model_version
    assert "model_version" in data1 and data1["model_version"].startswith("lightgbm_")
    assert "model_version" in data2 and data2["model_version"].startswith("lightgbm_")
    
    # Must fail if response matches old stub values
    stub_shap = [{"feature": "distance", "value": 0.5}, {"feature": "priority", "value": 0.2}]
    assert data1["shap_values"] != stub_shap, "Failed: returned stub SHAP values"
    assert data2["shap_values"] != stub_shap, "Failed: returned stub SHAP values"
    
    # Values must differ per order
    assert data1["predicted_eta_mins"] != data2["predicted_eta_mins"] or data1["shap_values"] != data2["shap_values"], \
        "Failed: predictions and SHAP values must not be identical across different orders"
