"""Health check schema."""

from datetime import datetime
from pydantic import Field
from agentiq_core.schemas.base import AgentIQBaseModel


class HealthResponse(AgentIQBaseModel):
    """Health status response payload."""

    status: str = Field(default="healthy", description="Application health status")
    version: str = Field(..., description="Application semantic version")
    timestamp: datetime = Field(..., description="Current UTC timestamp of the server")
    database: str | None = Field(default=None, description="Database connection health status")

