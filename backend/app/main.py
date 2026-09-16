"""
Enterprise AI Analytics Copilot - Main Application Entry Point

This is the FastAPI application factory. It:
1. Creates the FastAPI app instance
2. Configures CORS middleware and structured logging
3. Registers all API routers
4. Adds a /health endpoint for container orchestrators
5. Sets up startup/shutdown events for database and cache connections
"""

import logging
from pathlib import Path
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — Register all models with Base.metadata
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.metrics import PrometheusMiddleware, metrics_endpoint
from app.core.middleware import (
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)


# ─── Structured Logging Setup ──────────────────────────────────
def setup_logging():
    """
    Configure structured logging.

    In production (DEBUG=False): JSON-formatted logs for log aggregation
    (CloudWatch, Datadog, ELK stack, etc.)
    In development (DEBUG=True): Human-readable format for terminal output.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    if settings.DEBUG:
        # Development: readable format
        fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
        logging.basicConfig(level=log_level, format=fmt, stream=sys.stdout)
    else:
        # Production: JSON-ish structured format (compatible with log aggregators)
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
        logging.basicConfig(level=log_level, format=fmt, stream=sys.stdout)

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if not settings.DEBUG else log_level)


setup_logging()
logger = logging.getLogger("app")


# ─── Lifespan Events ──────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events.

    On startup:
      - In development/debug mode: initializes database tables via create_all.
      - In production: verifies DB connectivity safely without blocking or racing migrations.
    On shutdown:
      - Close database connections gracefully.
    """
    logger.info("Starting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)

    # Startup database connectivity verification
    try:
        if settings.APP_ENV == "development" or settings.DEBUG:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema verified (development mode create_all)")
        else:
            from sqlalchemy import text
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
    except Exception as e:
        logger.warning(
            "Database connectivity check deferred or unavailable during startup: %s. "
            "Application started in resilient mode (API requests will connect on demand).",
            e,
        )

    logger.info("Application ready")
    yield

    # Shutdown
    logger.info("Shutting down...")
    await engine.dispose()


# ─── App Factory ──────────────────────────────────────────────
def create_app() -> FastAPI:
    """Application factory pattern - creates and configures the FastAPI app."""

    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered analytics platform for business intelligence",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS Middleware
    origins = settings.cors_origins_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True if origins != ["*"] else False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security middleware stack (order matters: outermost runs first)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(RateLimitMiddleware, window_seconds=60)
    app.add_middleware(PrometheusMiddleware)

    # Request logging middleware (logs method, path, status, duration)
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        # Skip noisy health check logs
        if request.url.path != "/health":
            logger.info(
                "%s %s → %d (%dms)",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
        return response

    # ─── Health Check (no auth required) ─────────────────────
    @app.get("/health", tags=["System"])
    async def health_check():
        """
        Health check endpoint for container orchestrators (Docker, K8s).

        Returns basic service status. Used by:
        - Docker HEALTHCHECK
        - Load balancer health probes
        - Monitoring systems (Datadog, Prometheus)
        """
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": "1.0.0",
            "environment": settings.APP_ENV,
        }

    # Register API routes
    app.include_router(api_router, prefix="/api/v1")

    # Prometheus metrics endpoint (no auth, scraped by Prometheus)
    app.add_route("/metrics", metrics_endpoint, methods=["GET"])

    # ─── Serve React Frontend Web UI (SPA) ────────────────────
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    static_dir = Path("/app/static")
    if not static_dir.exists():
        static_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

    if static_dir.exists() and (static_dir / "index.html").exists():
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/", tags=["UI"], include_in_schema=False)
        async def serve_index():
            return FileResponse(static_dir / "index.html")

        @app.get("/{full_path:path}", tags=["UI"], include_in_schema=False)
        async def serve_spa(full_path: str):
            if full_path.startswith(("api", "docs", "redoc", "openapi.json", "health", "metrics")):
                raise HTTPException(status_code=404, detail="Not Found")
            file_path = static_dir / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(static_dir / "index.html")
    else:
        @app.get("/", tags=["System"])
        async def root():
            """Root landing endpoint providing API status and navigation links."""
            return {
                "service": settings.APP_NAME,
                "version": "1.0.0",
                "environment": settings.APP_ENV,
                "status": "online",
                "docs": "/docs",
                "health": "/health",
                "api": "/api/v1",
            }

    return app


# Create the app instance
app = create_app()
