import time

from backend.models_db.order import DBOrder
from backend.models_db.vehicle import DBVehicle
from src.data_processing.schemas import OrderStatus

from tests.test_backend.conftest import BASE_TIME, make_order_payload


def _optimize(client, **kw):
    body = {"solver_type": "hgs", "weight_config": {"preset": "balanced"}, "max_runtime_s": 5, **kw}
    r = client.post("/routes/optimize", json=body)
    assert r.status_code == 202, r.text
    return r.json()["job_id"]


def test_optimize_then_read_plan(client, override_user, mock_manager_user, plan_data):
    override_user(mock_manager_user)
    job = _optimize(client)
    assert client.get(f"/jobs/{job}").json()["status"] == "completed"

    routes = client.get("/routes").json()                       # latest run only
    assert routes and {r["optimizer_run_id"] for r in routes} == {job}

    runs = client.get("/optimizer-runs").json()
    assert runs[0]["id"] == job and runs[0]["metrics"]["feasible"]

    plan = client.get(f"/optimizer-runs/{job}").json()
    assert plan["depot"] and plan["routes"]
    stop = plan["routes"][0]["stops"][0]
    assert stop["p10"] <= stop["p50"] <= stop["p90"]
    assert stop["status"] in {"on_time", "at_risk", "late"}


def test_explain_uses_persisted_stop_prediction(client, override_user, mock_manager_user, plan_data):
    override_user(mock_manager_user)
    plan = client.get("/optimizer-runs", params={"limit": 1}).json()[0]
    oid = client.get(f"/optimizer-runs/{plan['id']}").json()["routes"][0]["stops"][0]["order_id"]
    r = client.get(f"/predictions/{oid}/explain")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["optimizer_run_id"] == plan["id"]
    assert body["leg_minutes"]["p10"] <= body["leg_minutes"]["p50"] <= body["leg_minutes"]["p90"]
    assert body["arrival"]["p10"] <= body["arrival"]["p50"] <= body["arrival"]["p90"]
    assert all({"feature", "value", "text"} <= set(s) for s in body["shap_values"])


def test_whatif_is_fast_reports_deltas_and_does_not_persist(client, override_user, mock_manager_user, plan_data):
    override_user(mock_manager_user)
    before = client.get("/optimizer-runs").json()
    t0 = time.time()
    r = client.post("/routes/whatif", json={"w_distance": 1, "w_time": 0, "w_fuel": 0, "w_delay": 0, "max_runtime_s": 4})
    elapsed = time.time() - t0
    assert r.status_code == 200, r.text
    assert elapsed < 10, f"what-if took {elapsed:.1f}s (target < 10s)"
    body = r.json()
    assert body["committed"] is False and body["metrics"]["feasible"]
    assert abs(sum(body["weights"][k] for k in ("w_distance", "w_time", "w_fuel", "w_delay")) - 1.0) < 1e-6
    assert body["delta_vs_current"] is not None and "total_cost" in body["delta_vs_current"]
    assert len(client.get("/optimizer-runs").json()) == len(before)   # nothing saved

    r2 = client.post("/routes/whatif", json={"w_distance": 0, "w_time": 1, "w_fuel": 0, "w_delay": 0, "max_runtime_s": 4})
    assert r2.status_code == 200 and r2.json()["metrics"]["feasible"]
    assert client.post("/routes/whatif", json={"w_distance": 0, "w_time": 0, "w_fuel": 0, "w_delay": 0}).status_code == 422


def test_new_order_disruption_creates_child_run_quickly(client, override_user, mock_manager_user, plan_data, db_session):
    import numpy as np
    override_user(mock_manager_user)
    parent = client.get("/optimizer-runs", params={"limit": 1}).json()[0]["id"]
    order = make_order_payload(99, np.random.RandomState(3), window_start_min=30)
    t0 = time.time()
    r = client.post("/routes/disrupt", json={"event": {"type": "new_order", "order": order}})
    elapsed = time.time() - t0
    assert r.status_code == 202, r.text
    assert elapsed < 5, f"re-solve took {elapsed:.1f}s (target < 5s)"
    child = r.json()["job_id"]
    assert r.json()["parent_run_id"] == parent
    plan = client.get(f"/optimizer-runs/{child}").json()
    assert plan["parent_run_id"] == parent and plan["event"]["type"] == "new_order"
    placed = {s["order_id"] for rt in plan["routes"] for s in rt["stops"]} | {u["order_id"] for u in plan["unassigned"]}
    assert "T-099" in placed
    assert plan["metrics"]["violations"] == []


def test_cancel_and_vehicle_down(client, override_user, mock_manager_user, plan_data, db_session):
    override_user(mock_manager_user)
    latest = client.get("/optimizer-runs", params={"limit": 1}).json()[0]["id"]
    plan = client.get(f"/optimizer-runs/{latest}").json()
    victim = plan["routes"][0]["stops"][0]["order_id"]
    r = client.post("/routes/disrupt", json={"event": {"type": "cancel_order", "order_id": victim}})
    assert r.status_code == 202, r.text
    db_session.expire_all()
    assert db_session.get(DBOrder, victim).status == OrderStatus.CANCELLED
    child = client.get(f"/optimizer-runs/{r.json()['job_id']}").json()
    assert victim not in {s["order_id"] for rt in child["routes"] for s in rt["stops"]}

    down = child["routes"][0]["vehicle_id"]
    r = client.post("/routes/disrupt", json={"event": {"type": "vehicle_down", "vehicle_id": down}})
    assert r.status_code == 202, r.text
    db_session.expire_all()
    assert db_session.get(DBVehicle, down).is_active is False
    after = client.get(f"/optimizer-runs/{r.json()['job_id']}").json()
    assert down not in {rt["vehicle_id"] for rt in after["routes"]}
    assert after["metrics"]["violations"] == []


def test_invalid_disruption_rejected(client, override_user, mock_manager_user, plan_data):
    override_user(mock_manager_user)
    assert client.post("/routes/disrupt", json={"event": {"type": "meteor"}}).status_code == 422
    assert client.post("/routes/disrupt", json={"event": {"type": "traffic_change", "time_multiplier": 0}}).status_code == 422


def test_traffic_change_slows_the_plan(client, override_user, mock_manager_user, plan_data):
    override_user(mock_manager_user)
    r = client.post("/routes/disrupt", json={"event": {"type": "traffic_change", "time_multiplier": 1.4}})
    assert r.status_code == 202, r.text
    plan = client.get(f"/optimizer-runs/{r.json()['job_id']}").json()
    assert plan["event"]["type"] == "traffic_change" and plan["metrics"]["violations"] == []


def test_replay_is_reproducible_and_flagged_simulated(client, override_user, mock_manager_user, plan_data):
    override_user(mock_manager_user)
    run = client.get("/optimizer-runs", params={"limit": 1}).json()[0]["id"]
    a = client.get(f"/replay/{run}").json()
    b = client.get(f"/replay/{run}").json()
    assert a["simulated"] is True and a == b
    assert a["summary"]["stops"] == sum(len(r["stops"]) for r in a["routes"]) > 0
