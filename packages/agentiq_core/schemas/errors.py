"""Standard error response schemas conforming to AgentIQ conventions."""

from typing import Any, Optional
from pydantic import Field
from agentiq_core.schemas.base import AgentIQBaseModel


class ErrorDetail(AgentIQBaseModel):
    """Inner error payload with code, explanation, and optional context details."""

    code: str = Field(..., description="Unique machine-readable error identifier")
    message: str = Field(..., description="Human-readable explanation of the error")
    details: Optional[Any] = Field(
        default=None,
        description="Optional structured context, field validation errors, or debugging metadata",
    )


class ErrorResponse(AgentIQBaseModel):
    """Standard envelope for all HTTP 4xx and 5xx API error responses."""

    error: ErrorDetail

