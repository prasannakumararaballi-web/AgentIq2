"""Finding schemas representing detected anomalies and recommended fixes."""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID
from pydantic import Field
from agentiq_core.schemas.base import AgentIQBaseModel

FindingSeverity = Literal["low", "medium", "high", "critical"]
FindingCategory = Literal[
    "missing_value",
    "outlier",
    "type_mismatch",
    "duplicate",
    "format_inconsistency",
    "business_rule_violation",
]
FindingActionType = Literal["drop_row", "impute", "replace", "transform", "ignore"]


class SuggestedAction(AgentIQBaseModel):
    """Machine or AI recommended remediation for a data quality issue."""

    action_type: FindingActionType = Field(
        ..., description="Recommended remediation: drop_row, impute, replace, transform, ignore"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Concrete parameters needed to execute the fix"
    )
    rationale: Optional[str] = Field(
        default=None, description="Explanation or AI generated reasoning for why this action is recommended"
    )


class FindingResponse(AgentIQBaseModel):
    """Detailed representation of an individual detected anomaly."""

    id: UUID = Field(..., description="Unique finding identifier")
    run_id: UUID = Field(..., description="Associated run ID")
    row_index: Optional[int] = Field(
        default=None, description="Zero-based row index in dataset, if row-specific"
    )
    column_name: Optional[str] = Field(
        default=None, description="Target column affected, if column-specific"
    )
    category: FindingCategory = Field(..., description="Categorization of the data quality anomaly")
    severity: FindingSeverity = Field(..., description="Impact level: low, medium, high, critical")
    description: str = Field(..., description="Human-readable summary of the detected problem")
    affected_value: Optional[str] = Field(
        default=None, description="Sample or string representation of the offending raw value"
    )
    suggested_action: Optional[SuggestedAction] = Field(
        default=None, description="Suggested resolution action"
    )
    is_resolved: bool = Field(
        default=False, description="Whether a decision has already been committed for this finding"
    )
    created_at: datetime = Field(..., description="Timestamp when finding was detected")


class FindingListResponse(AgentIQBaseModel):
    """Paginated collection of run findings."""

    items: list[FindingResponse] = Field(default_factory=list, description="List of findings")
    total: int = Field(..., description="Total count matching filter criteria")
    limit: int = Field(default=50, description="Page limit applied")
    offset: int = Field(default=0, description="Page offset applied")
