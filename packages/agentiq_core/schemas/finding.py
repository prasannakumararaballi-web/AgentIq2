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
    # Card-level aggregation & risk tier extensions (Phase 2)
    issue_title: Optional[str] = Field(
        default=None, description="Human-readable title for card-level grouped anomaly"
    )
    affected_row_count: int = Field(
        default=1, description="Total count of rows affected across dataset"
    )
    affected_row_indices: list[int] = Field(
        default_factory=list, description="Bounded sample list of affected row indices (max 50)"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Evidence-based detection confidence"
    )
    risk_tier: int = Field(
        default=1, ge=0, le=3, description="Conservative remediation risk tier (0=safe, 1=low, 2=medium, 3=high)"
    )
    impact_estimate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Estimated proportion of dataset affected"
    )
    sample_before: list[dict[str, Any]] = Field(
        default_factory=list, description="Sample preview of values before remediation"
    )
    sample_after: list[dict[str, Any]] = Field(
        default_factory=list, description="Sample preview of values after remediation"
    )
    detection_rule: Optional[str] = Field(
        default=None, description="Identifier of the rule or heuristic that detected this issue"
    )
    created_at: datetime = Field(..., description="Timestamp when finding was detected")


class FindingListResponse(AgentIQBaseModel):
    """Paginated collection of run findings."""

    items: list[FindingResponse] = Field(default_factory=list, description="List of findings")
    total: int = Field(..., description="Total count matching filter criteria")
    limit: int = Field(default=50, description="Page limit applied")
    offset: int = Field(default=0, description="Page offset applied")

