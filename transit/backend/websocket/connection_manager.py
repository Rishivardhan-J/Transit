import asyncio
import json

import redis.asyncio as redis
from fastapi import WebSocket
from backend.config import settings

class ConnectionManager:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)
        
    async def subscribe_to_job(self, job_id: str, websocket: WebSocket):
        pubsub = self.redis.pubsub()
        await asyncio.wait_for(pubsub.subscribe(f"job_updates:{job_id}"), timeout=2.0)
        
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    await websocket.send_json(data)
                    if data.get("status") in ["completed", "failed"]:
                        break
        finally:
            await pubsub.unsubscribe(f"job_updates:{job_id}")
            
    async def subscribe_to_route(self, optimizer_run_id: str, websocket: WebSocket):
        pubsub = self.redis.pubsub()
        await asyncio.wait_for(pubsub.subscribe(f"route_updates:{optimizer_run_id}"), timeout=2.0)
        
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    await websocket.send_json(data)
        finally:
            await pubsub.unsubscribe(f"route_updates:{optimizer_run_id}")

manager = ConnectionManager()
