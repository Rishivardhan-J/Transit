import pytest

def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "process_cpu_seconds_total" in response.text

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
