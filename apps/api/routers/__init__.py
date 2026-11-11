"""Export all API routers."""

from apps.api.routers.auth import router as auth_router
from apps.api.routers.decisions import router as decisions_router
from apps.api.routers.findings import router as findings_router
from apps.api.routers.health import router as health_router
from apps.api.routers.projects import router as projects_router
from apps.api.routers.runs import router as runs_router
from apps.api.routers.uploads import router as uploads_router

__all__ = [
    "health_router",
    "auth_router",
    "projects_router",
    "uploads_router",
    "runs_router",
    "findings_router",
    "decisions_router",
]
