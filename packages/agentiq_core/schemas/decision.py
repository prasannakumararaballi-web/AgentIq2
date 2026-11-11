"""User decision schemas for approving, modifying, or reverting remediation actions."""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID
from pydantic import Field
from agentiq_core.schemas.base import AgentIQBaseModel
from agentiq_core.schemas.finding import FindingActionType

DecisionStatus = Literal["applied", "undone"]


class FindingDecisionCreate(AgentIQBaseModel):
    """User submission to resolve a specific finding."""

    action_type: FindingActionType = Field(
        ..., description="Resolution strategy chosen: drop_row, impute, replace, transform, ignore"
    )
    custom_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the remediation action (e.g., replacement value, strategy)",
    )
    notes: Optional[str] = Field(
        default=None, max_length=500, description="Optional reviewer commentary or reason"
    )


class FindingDecisionResponse(AgentIQBaseModel):
    """Result of an applied remediation decision."""

    id: UUID = Field(..., description="Unique decision record identifier")
    finding_id: UUID = Field(..., description="Target finding ID")
    run_id: UUID = Field(..., description="Associated run ID")
    user_id: UUID = Field(..., description="ID of the user who made the decision")
    action_type: FindingActionType = Field(..., description="Action taken")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Resolved execution parameters"
    )
    status: DecisionStatus = Field(default="applied", description="Status: applied or undone")
    decided_at: datetime = Field(..., description="UTC timestamp of the decision")


class DecisionUndoResponse(AgentIQBaseModel):
    """Result of reverting a previously committed decision."""

    decision_id: UUID = Field(..., description="Reverted decision ID")
    status: DecisionStatus = Field(default="undone", description="Updated status: undone")
    undone_at: datetime = Field(..., description="UTC timestamp when the undo was recorded")
    message: str = Field(..., description="Status summary confirming reversal")
