"""Health check endpoint with database probe."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agentiq_core.db.session import get_db_session
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns service availability, active version, current server UTC timestamp, and database connectivity.",
)
async def check_health(
    db: AsyncSession = Depends(get_db_session),
) -> HealthResponse:
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
        is_healthy = True
    except Exception:
        db_status = "unreachable"
        is_healthy = False

    return HealthResponse(
        status="healthy" if is_healthy else "degraded",
        version="0.1.0",
        timestamp=utc_now(),
        database=db_status,
    )
