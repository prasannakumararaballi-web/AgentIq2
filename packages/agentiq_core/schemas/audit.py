"""Audit trail schemas for tracking user actions and run events."""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import Field
from agentiq_core.schemas.base import AgentIQBaseModel


class AuditEventResponse(AgentIQBaseModel):
    """Single immutable audit log entry."""

    id: UUID = Field(..., description="Unique audit entry ID")
    run_id: UUID = Field(..., description="Associated run ID")
    user_id: UUID = Field(..., description="User ID responsible for the event")
    action: str = Field(..., description="Action tag (e.g. run.started, finding.decided, decision.undone)")
    details: dict[str, Any] = Field(default_factory=dict, description="Detailed metadata or diff snapshot")
    timestamp: datetime = Field(..., description="UTC timestamp of the event")


class RunAuditResponse(AgentIQBaseModel):
    """Chronological collection of audit events for a run."""

    run_id: UUID = Field(..., description="Target run ID")
    events: list[AuditEventResponse] = Field(default_factory=list, description="Chronological audit records")
    total: int = Field(..., description="Total audit events recorded")
