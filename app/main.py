from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import time
import os

from app.config import settings
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.api import deps
from app.services.cache import cache_service

# Import Routers
from app.api.v1 import auth, zones, meters, predict, alerts, analytics

# Create database tables at startup if SQLite (or postgres fallback) is active
# Note: In production Docker environment, migrations are handled by Alembic.
# For quick local run/sandbox, auto-creating tables is extremely robust.
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")
except Exception as e:
    print(f"Warning: Database auto-initialization skipped or failed: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Powered Smart Grid Load Forecasting Platform. Ingests smart meter readings, runs autoregressive forecasters, detects overloads, and triggers alerts.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response

# Include API Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(zones.router, prefix="/api/v1/zones", tags=["Zones"])
app.include_router(meters.router, prefix="/api/v1/meters", tags=["Meters & Readings"])
app.include_router(predict.router, prefix="/api/v1/predict", tags=["Forecasting"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])

@app.get("/", tags=["General"])
def read_root():
    return {
        "message": "Welcome to the Smart Grid Load Forecasting API",
        "docs_url": "/docs",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health", tags=["General"])
def health_check(db: Session = Depends(deps.get_db)):
    """
    Detailed health check of API dependencies.
    Verifies connection to PostgreSQL and Redis.
    """
    db_status = "unhealthy"
    try:
        db.execute(Base.metadata.tables["user"].select().limit(1))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy ({e})"

    redis_status = "healthy" if cache_service.enabled else "unhealthy (offline)"

    status_code = status.HTTP_200_OK
    if "unhealthy" in db_status:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "redis": redis_status,
        "environment": "testing" if os.getenv("TESTING") else "production"
    }
