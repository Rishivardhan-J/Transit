from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from backend.config import settings
from backend.observability.sentry_init import init_sentry
from backend.api import auth, orders, vehicles, routes, predictions, benchmarks, models_meta
from backend.websocket import routes_ws

# Initialize Sentry
init_sentry()

app = FastAPI(title="Transit API", version="1.0.0")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include Routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(vehicles.router, prefix="/vehicles", tags=["Vehicles"])
app.include_router(routes.router, prefix="/routes", tags=["Routes"])
app.include_router(predictions.router, prefix="/predictions", tags=["Predictions"])
app.include_router(benchmarks.router, prefix="/benchmarks", tags=["Benchmarks"])
app.include_router(models_meta.router, prefix="/models", tags=["Models Metadata"])
app.include_router(routes_ws.router, prefix="/ws", tags=["WebSockets"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
