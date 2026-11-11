"""Health check endpoint."""

from fastapi import APIRouter, status
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns service availability, active version, and current server UTC timestamp.",
)
async def check_health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=utc_now(),
    )

