import pytest
from datetime import datetime, timezone
import json

def test_create_order_valid(client, override_user, mock_manager_user):
    override_user(mock_manager_user)
    payload = {
        "order_id": "ord-1",
        "pickup_lat": 40.7128,
        "pickup_lng": -74.0060,
        "delivery_lat": 40.7300,
        "delivery_lng": -73.9900,
        "demand_weight": 10.5,
        "priority": "standard",
        "time_window_start": datetime.now(timezone.utc).isoformat(),
        "time_window_end": "2050-01-01T12:00:00Z",
        "service_time_minutes": 5,
        "created_at": "2020-01-01T10:00:00Z",
        "status": "pending"
    }
    response = client.post("/orders", json=payload)
    assert response.status_code == 201
    assert response.json()["order_id"] == "ord-1"

def test_create_order_invalid_coordinates(client, override_user, mock_manager_user):
    override_user(mock_manager_user)
    payload = {
        "order_id": "ord-bad",
        "pickup_lat": 95.0, # invalid lat
        "pickup_lng": -74.0060,
        "delivery_lat": 40.7300,
        "delivery_lng": -73.9900,
        "demand_weight": 10.5,
        "priority": "standard",
        "time_window_start": datetime.now(timezone.utc).isoformat(),
        "time_window_end": "2050-01-01T12:00:00Z",
        "service_time_minutes": 5,
        "created_at": "2020-01-01T10:00:00Z",
        "status": "pending"
    }
    response = client.post("/orders", json=payload)
    assert response.status_code == 422
    assert "ge" in response.text or "less than or equal to" in response.text

def test_delete_order(client, override_user, mock_manager_user):
    override_user(mock_manager_user)
    response = client.delete("/orders/ord-1")
    assert response.status_code == 204

def test_export_orders_anonymization(client, override_user, mock_manager_user, db_session):
    override_user(mock_manager_user)
    payload = {
        "order_id": "ord-export-1",
        "pickup_lat": 40.7128,
        "pickup_lng": -74.0060,
        "delivery_lat": 40.7300,
        "delivery_lng": -73.9900,
        "demand_weight": 10.5,
        "priority": "standard",
        "time_window_start": datetime.now(timezone.utc).isoformat(),
        "time_window_end": "2050-01-01T12:00:00Z",
        "service_time_minutes": 5,
        "created_at": "2020-01-01T10:00:00Z",
        "status": "pending"
    }
    client.post("/orders", json=payload)
    
    response = client.get("/orders/export")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) > 0
    
    # Anonymized coordinates are rounded to 3 decimal places by processor
    for order in orders:
        if order["order_id"] == "ord-export-1":
            assert order["pickup_lat"] == 40.713
            assert order["pickup_lng"] == -74.006
            assert order["delivery_lat"] == 40.730
            assert order["delivery_lng"] == -73.990
