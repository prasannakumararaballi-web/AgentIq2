"""Main FastAPI application entry point."""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Automatically inject project root, packages, and apps into sys.path
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
for _p in [str(_BASE_DIR), str(_BASE_DIR / "packages"), str(_BASE_DIR / "apps")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.api.config import settings
from apps.api.middleware.error_handler import register_error_handlers
from apps.api.routers import (
    auth_router,
    decisions_router,
    downloads_router,
    findings_router,
    health_router,
    projects_router,
    runs_router,
    uploads_router,
    workspaces_router,
)

logger = logging.getLogger("agentiq.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event to guarantee DB tables and demo seed exist on boot."""
    # Ensure local storage folders exist
    Path("storage").mkdir(parents=True, exist_ok=True)
    Path("storage/raw").mkdir(parents=True, exist_ok=True)
    Path("storage/exports").mkdir(parents=True, exist_ok=True)

    try:
        from agentiq_core.models import Base
        from agentiq_core.db.session import get_async_engine
        engine = get_async_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema verified.")

        # Seed demo workspace and user
        from scripts.seed_demo_data import seed
        await seed()
        logger.info("Demo data seed verified.")
    except Exception as exc:
        logger.warning(f"Startup initialization notice: {exc}")

    yield


def create_app() -> FastAPI:
    """Initialize and configure the FastAPI application."""
    app = FastAPI(
        title="AgentIQ v2 API",
        description="Data-quality and AI-assisted data-cleaning platform API.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        servers=[
            {"url": "http://localhost:8000", "description": "Local Development Server"},
        ],
    )

    # 1. CORS Configuration for Next.js frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register Global Standardized Error Handlers
    register_error_handlers(app)

    # 3. Mount Routers
    # Health endpoint is mounted at the root level: GET /health
    app.include_router(health_router)

    # Versioned API routes mounted under prefix: /api/v1
    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(projects_router, prefix=settings.api_v1_prefix)
    app.include_router(uploads_router, prefix=settings.api_v1_prefix)
    app.include_router(runs_router, prefix=settings.api_v1_prefix)
    app.include_router(findings_router, prefix=settings.api_v1_prefix)
    app.include_router(decisions_router, prefix=settings.api_v1_prefix)
    app.include_router(workspaces_router, prefix=settings.api_v1_prefix)
    app.include_router(downloads_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.api.main:app", host=settings.api_host, port=settings.api_port, reload=True)

