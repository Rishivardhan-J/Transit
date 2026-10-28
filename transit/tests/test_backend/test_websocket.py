import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

@pytest.fixture
def mock_redis():
    with patch("backend.websocket.connection_manager.manager.redis") as mock_redis_client:
        mock_pubsub = AsyncMock()
        mock_redis_client.pubsub = MagicMock(return_value=mock_pubsub)
        
        # Setup mock pubsub to yield a message then block
        mock_pubsub.get_message.side_effect = [
            {"type": "message", "data": json.dumps({"status": "completed"})},
            None
        ]
        yield mock_pubsub

@pytest.mark.asyncio
async def test_websocket_job_status(client, mock_redis, mock_manager_user):
    # The TestClient allows context manager usage for websockets
    from backend.security.auth import create_access_token
    from backend.models_db.base import SessionLocal  # noqa: F401
    token = create_access_token({"sub": "manager@test.com"})
    with client.websocket_connect(f"/ws/jobs/test-job-123?token={token}") as websocket:
        data = websocket.receive_json()
        assert data["status"] == "completed"
