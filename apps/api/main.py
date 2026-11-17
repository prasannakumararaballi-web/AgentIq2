"""Main FastAPI application entry point."""

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


def create_app() -> FastAPI:
    """Initialize and configure the FastAPI application."""
    app = FastAPI(
        title="AgentIQ v2 API",
        description="Data-quality and AI-assisted data-cleaning platform API.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
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

