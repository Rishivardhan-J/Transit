import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Set environment variables for tests BEFORE importing app
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["TESTING"] = "True"

from backend.main import app
from backend.models_db.base import Base
from backend.api.deps import get_db, get_current_user
from backend.models_db.user import User, Role
import uuid

# Use an in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
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

@pytest.fixture(scope="module")
def mock_manager_user(db_session):
    user = db_session.query(User).filter_by(email="manager@test.com").first()
    if not user:
        user = User(id=str(uuid.uuid4()), email="manager@test.com", hashed_password="hashed", role=Role.manager)
        db_session.add(user)
        db_session.commit()
    return user

@pytest.fixture(scope="module")
def mock_researcher_user(db_session):
    user = db_session.query(User).filter_by(email="researcher@test.com").first()
    if not user:
        user = User(id=str(uuid.uuid4()), email="researcher@test.com", hashed_password="hashed", role=Role.researcher)
        db_session.add(user)
        db_session.commit()
    return user

@pytest.fixture
def override_user(client):
    def _override(user: User):
        app.dependency_overrides[get_current_user] = lambda: user
    return _override
