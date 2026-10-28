import os
import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set environment variables for tests BEFORE importing app
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["TESTING"] = "True"

from backend.main import app  # noqa: E402
from backend.models_db.base import Base  # noqa: E402
from backend.api.deps import get_db, get_current_user  # noqa: E402
from backend.models_db.user import User, Role  # noqa: E402
from backend.jobs.celery_app import celery_app  # noqa: E402

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Run Celery tasks inline and never touch the network: job progress is best-effort pub/sub.
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True


@pytest.fixture(autouse=True)
def _no_redis(monkeypatch):
    monkeypatch.setattr("backend.jobs.optimization_tasks.publish", lambda *a, **k: None)


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)


def _make_user(db, email, role):
    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(id=str(uuid.uuid4()), email=email, hashed_password="hashed", role=role)
        db.add(user)
        db.commit()
    return user


@pytest.fixture(scope="module")
def mock_manager_user(db_session):
    return _make_user(db_session, "manager@test.com", Role.manager)


@pytest.fixture(scope="module")
def mock_researcher_user(db_session):
    return _make_user(db_session, "researcher@test.com", Role.researcher)


@pytest.fixture(scope="module")
def mock_admin_user(db_session):
    return _make_user(db_session, "admin@test.com", Role.admin)


@pytest.fixture
def override_user(client):
    def _override(user: User):
        app.dependency_overrides[get_current_user] = lambda: user
    return _override


BASE_TIME = datetime(2025, 1, 6, 8, 0, tzinfo=timezone.utc)
DEPOT = (34.0407, -118.2468)


def make_order_payload(i, rng, window_start_min=0, width=300):
    start = BASE_TIME + timedelta(minutes=window_start_min)
    return {
        "order_id": f"T-{i:03d}",
        "pickup_lat": DEPOT[0], "pickup_lng": DEPOT[1],
        "delivery_lat": DEPOT[0] + float(rng.uniform(-0.05, 0.05)), "delivery_lng": DEPOT[1] + float(rng.uniform(-0.05, 0.05)),
        "demand_weight": float(rng.randint(2, 12)), "priority": "standard",
        "time_window_start": start.isoformat(), "time_window_end": (start + timedelta(minutes=width)).isoformat(),
        "service_time_minutes": 6.0, "created_at": (BASE_TIME - timedelta(hours=1)).isoformat(), "status": "pending",
    }


@pytest.fixture(scope="module")
def plan_data(db_session):
    """12 LA orders and 3 vans, committed to the test DB."""
    from backend.models_db.converters import to_db_order, to_db_vehicle
    from src.data_processing.schemas import Order, Vehicle, VehicleType

    rng = np.random.RandomState(7)
    orders = [Order(**make_order_payload(i, rng, window_start_min=int(rng.randint(0, 60)))) for i in range(12)]
    vehicles = [Vehicle(vehicle_id=f"TV-{k}", capacity=45.0, vehicle_type=VehicleType.VAN, fuel_efficiency=11.0,
                        available_from=BASE_TIME, available_until=BASE_TIME + timedelta(hours=9),
                        current_lat=DEPOT[0], current_lng=DEPOT[1]) for k in range(3)]
    for o in orders:
        db_session.add(to_db_order(o))
    for v in vehicles:
        db_session.add(to_db_vehicle(v))
    db_session.commit()
    return {"orders": orders, "vehicles": vehicles}
