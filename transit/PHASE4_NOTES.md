# Phase 4 Implementation Notes

- **WebSocket Dependency on Redis**: We've implemented real-time WebSocket delivery by piping the `job_updates:{job_id}` and `route_updates:{optimizer_run_id}` pub/sub channels from Redis into the FastAPI Websocket manager. This unifies real-time messaging around the Celery broker (Redis). However, this means WebSocket delivery depends strictly on Redis staying up. If Redis restarts mid-job, in-flight job updates may not reach the socket. Clients must implement a resilient reconnect loop, or safely fallback to polling the REST status endpoint (`GET /jobs/{job_id}`) upon disconnect.
- **RBAC Strict Gating**: Security logic gates the researcher-oriented benchmarking and metrics endpoints by verifying that the provided OAuth2 token carries the `researcher` role.
- **Port Conflict**: To avoid local conflicts with existing postgres instances (5432), Postgres runs on 5433 via `docker-compose`. Testing relies on SQLite `test.db`.
