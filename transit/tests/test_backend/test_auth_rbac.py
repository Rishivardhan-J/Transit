def test_benchmark_researcher_success(client, override_user, mock_researcher_user):
    override_user(mock_researcher_user)
    response = client.get("/benchmarks/solver-comparison")
    # Even if data file isn't there, we should get 200 with error JSON, not 403
    assert response.status_code == 200

def test_benchmark_manager_forbidden(client, override_user, mock_manager_user):
    override_user(mock_manager_user)
    response = client.get("/benchmarks/solver-comparison")
    assert response.status_code == 403

def test_models_researcher_success(client, override_user, mock_researcher_user):
    override_user(mock_researcher_user)
    response = client.get("/models/performance")
    assert response.status_code == 200

def test_models_manager_forbidden(client, override_user, mock_manager_user):
    override_user(mock_manager_user)
    response = client.get("/models/performance")
    assert response.status_code == 403
