import io

from backend.models_db.user import Role, User
from backend.security.auth import get_password_hash, verify_password


def test_password_check_is_real():
    h = get_password_hash("correct horse")
    assert verify_password("correct horse", h)
    assert not verify_password("admin", h)          # the old hard-coded bypass is gone
    assert not verify_password("x", "not-a-hash")


def test_register_always_creates_a_manager(client, db_session):
    r = client.post("/auth/register", json={"email": "sneaky@test.com", "password": "pw12345", "role": "admin"})
    assert r.status_code == 200
    assert db_session.query(User).filter_by(email="sneaky@test.com").one().role == Role.manager
    login = client.post("/auth/login", data={"username": "sneaky@test.com", "password": "pw12345"})
    assert login.status_code == 200 and "access_token" in login.json()
    assert client.post("/auth/login", data={"username": "sneaky@test.com", "password": "admin"}).status_code == 401


def test_rbac_matrix(client, override_user, mock_manager_user, mock_researcher_user, mock_admin_user, plan_data):
    researcher_only = [("get", "/eda/summary"), ("get", "/models/performance"), ("get", "/models/"),
                       ("post", "/benchmarks/compare-live")]
    override_user(mock_manager_user)
    for method, path in researcher_only:
        assert getattr(client, method)(path, **({"json": {}} if method == "post" else {})).status_code == 403, path
    assert client.get("/users").status_code == 403
    override_user(mock_researcher_user)
    assert client.get("/eda/summary").status_code == 200
    assert client.get("/models/performance").status_code == 200
    assert client.get("/users").status_code == 403
    override_user(mock_admin_user)
    assert client.get("/users").status_code == 200
    assert client.get("/eda/summary").status_code == 200


def test_admin_can_change_roles_but_not_demote_self(client, override_user, mock_admin_user, mock_manager_user):
    override_user(mock_admin_user)
    r = client.patch(f"/users/{mock_manager_user.id}/role", json={"role": "researcher"})
    assert r.status_code == 200 and r.json()["role"] == "researcher"
    client.patch(f"/users/{mock_manager_user.id}/role", json={"role": "manager"})
    assert client.patch(f"/users/{mock_admin_user.id}/role", json={"role": "manager"}).status_code == 400


def test_compare_live_runs_all_three_solvers(client, override_user, mock_researcher_user, plan_data):
    override_user(mock_researcher_user)
    r = client.post("/benchmarks/compare-live", json={"max_runtime_s": 3})
    assert r.status_code == 200, r.text
    rows = {s["solver"]: s for s in r.json()["solvers"]}
    assert set(rows) == {"nn", "ortools", "hgs"} and all(s["feasible"] for s in rows.values())


def test_eda_summary_is_real_data(client, override_user, mock_researcher_user):
    override_user(mock_researcher_user)
    body = client.get("/eda/summary", params={"dataset": "food"}).json()
    s = body["summary"]
    if s is None:
        return  # processed data not present in this environment
    assert s["rows"] > 0 and s["distributions"] and s["correlation"]
    assert sum(b["count"] for b in s["distributions"][s["target"]]) > 0


def test_upload_reports_bad_rows_with_row_numbers(client, override_user, mock_manager_user):
    override_user(mock_manager_user)
    csv = (
        "order_id,pickup_lat,pickup_lng,delivery_lat,delivery_lng,demand_weight,priority,time_window_start,time_window_end,service_time_minutes,created_at,status\n"
        "U-1,34.0,-118.2,34.01,-118.21,5,standard,2025-01-06T09:00:00,2025-01-06T12:00:00,5,2025-01-06T08:00:00,pending\n"
        "U-2,34.0,-118.2,134.01,-118.21,5,standard,2025-01-06T09:00:00,2025-01-06T12:00:00,5,2025-01-06T08:00:00,pending\n"
        "U-3,34.0,-118.2,34.02,-118.22,-4,standard,2025-01-06T13:00:00,2025-01-06T12:00:00,5,2025-01-06T08:00:00,pending\n"
    )
    r = client.post("/orders/upload", files={"file": ("orders.csv", io.BytesIO(csv.encode()), "text/csv")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 3 and body["valid"] == 1 and body["error_count"] >= 2
    assert {e["row_index"] for e in body["errors"]} == {1, 2}
    assert any(e["field"] == "delivery_lat" for e in body["errors"])
    committed = client.post("/orders/upload", params={"commit": True}, files={"file": ("orders.csv", io.BytesIO(csv.encode()), "text/csv")})
    assert committed.json()["created"] == 1
    assert client.post("/orders/upload", files={"file": ("x.csv", io.BytesIO(b""), "text/csv")}).status_code == 400


def test_websocket_rejects_missing_or_bad_token(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect
    for url in ("/ws/jobs/abc", "/ws/jobs/abc?token=garbage", "/ws/routes/abc?token=garbage"):
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(url):
                pass
        assert exc.value.code == 4401
