from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.websocket.connection_manager import manager

router = APIRouter()

@router.websocket("/jobs/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: str):
    await websocket.accept()
    try:
        await manager.subscribe_to_job(job_id, websocket)
    except WebSocketDisconnect:
        pass

@router.websocket("/routes/{optimizer_run_id}")
async def websocket_route_updates(websocket: WebSocket, optimizer_run_id: str):
    await websocket.accept()
    try:
        await manager.subscribe_to_route(optimizer_run_id, websocket)
    except WebSocketDisconnect:
        pass
