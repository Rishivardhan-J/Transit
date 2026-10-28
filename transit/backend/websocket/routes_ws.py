from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from backend.config import settings
from backend.models_db.base import SessionLocal
from backend.models_db.user import User
from backend.websocket.connection_manager import manager

router = APIRouter()
POLICY_VIOLATION = 4401


def _authenticate(token: str) -> bool:
    try:
        email = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]).get("sub")
    except JWTError:
        return False
    if not email:
        return False
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).first() is not None
    finally:
        db.close()


async def _accept_if_authenticated(websocket: WebSocket, token: str) -> bool:
    if not token or not _authenticate(token):
        await websocket.close(code=POLICY_VIOLATION)
        return False
    await websocket.accept()
    return True


@router.websocket("/jobs/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: str, token: str = Query("")):
    if not await _accept_if_authenticated(websocket, token):
        return
    try:
        await manager.subscribe_to_job(job_id, websocket)
    except WebSocketDisconnect:
        pass


@router.websocket("/routes/{optimizer_run_id}")
async def websocket_route_updates(websocket: WebSocket, optimizer_run_id: str, token: str = Query("")):
    if not await _accept_if_authenticated(websocket, token):
        return
    try:
        await manager.subscribe_to_route(optimizer_run_id, websocket)
    except WebSocketDisconnect:
        pass
