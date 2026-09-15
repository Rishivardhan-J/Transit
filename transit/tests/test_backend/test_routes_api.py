def test_optimize_route_async(client, override_user, mock_manager_user):
    override_user(mock_manager_user)
    payload = {
        "order_ids": ["ord-1"],
        "vehicle_ids": ["veh-1"],
        "solver_type": "hgs",
        "weight_config": {"preset": "balanced"}
    }
    response = client.post("/routes/optimize", json=payload)
    assert response.status_code == 202
    assert "job_id" in response.json()
    assert response.json()["status"] == "pending"

def test_disrupt_route_async(client, override_user, mock_manager_user):
    override_user(mock_manager_user)
    response = client.post("/routes/disrupt?optimizer_run_id=test-1", json={"type": "cancellation", "order_id": "ord-1"})
    assert response.status_code == 202
    assert "job_id" in response.json()
