def test_benchmark_results_visible_to_every_role(client, override_user, mock_researcher_user, mock_manager_user):
    # The Baseline-vs-HGS comparison screen is part of the manager dashboard (PRD 11.3 #6)
    for user in (mock_researcher_user, mock_manager_user):
        override_user(user)
        response = client.get("/benchmarks/solver-comparison")
        assert response.status_code == 200
        assert {"HGS_Dist", "ORT_Dist", "NN_Dist"} <= set(response.json()[0])

def test_models_researcher_success(client, override_user, mock_researcher_user):
    override_user(mock_researcher_user)
    response = client.get("/models/performance")
    assert response.status_code == 200

def test_models_manager_forbidden(client, override_user, mock_manager_user):
    override_user(mock_manager_user)
    response = client.get("/models/performance")
    assert response.status_code == 403
