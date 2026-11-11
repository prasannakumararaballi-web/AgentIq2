"""Execution run and summary schemas."""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID
from pydantic import Field
from agentiq_core.schemas.base import AgentIQBaseModel

RunStatus = Literal["queued", "processing", "completed", "failed", "cancelled"]
RunStage = Literal["reading", "detecting", "grouping", "explaining", "summarizing"]


class RunConfig(AgentIQBaseModel):
    """Optional execution configuration overrides for a cleaning run."""

    enable_ai_explanations: bool = Field(
        default=True, description="Whether to invoke AI provider for natural language explanations"
    )
    sample_size: Optional[int] = Field(
        default=None, description="Optional limit on row count for profiling sampling"
    )
    anomaly_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence threshold for anomaly detection"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary engine tuning parameters"
    )


class RunCreate(AgentIQBaseModel):
    """Payload to trigger an analysis and cleaning pipeline run."""

    project_id: UUID = Field(..., description="Target project ID")
    upload_id: UUID = Field(..., description="ID of the uploaded dataset file to process")
    config: Optional[RunConfig] = Field(default=None, description="Optional run configuration")


class RunProgress(AgentIQBaseModel):
    """Real-time progress telemetry designed for two-second polling intervals."""

    current_stage: Optional[RunStage] = Field(
        default=None, description="Active processing stage: reading, detecting, grouping, explaining, summarizing"
    )
    stage_percent: int = Field(default=0, ge=0, le=100, description="Completion percentage of the active stage (0-100)")
    total_percent: int = Field(default=0, ge=0, le=100, description="Overall run completion percentage (0-100)")
    message: Optional[str] = Field(default=None, description="Human-readable status or telemetry log snippet")


class RunResponse(AgentIQBaseModel):
    """Response schema for run lifecycle and status tracking."""

    id: UUID = Field(..., description="Unique run identifier")
    project_id: UUID = Field(..., description="Associated project ID")
    upload_id: UUID = Field(..., description="Target upload dataset ID")
    status: RunStatus = Field(..., description="Current status: queued, processing, completed, failed, cancelled")
    stage: Optional[RunStage] = Field(default=None, description="Current stage if processing")
    progress: RunProgress = Field(default_factory=RunProgress, description="Progress percentage and telemetry")
    started_at: Optional[datetime] = Field(default=None, description="UTC timestamp when processing began")
    completed_at: Optional[datetime] = Field(default=None, description="UTC timestamp when run ended")
    error_message: Optional[str] = Field(default=None, description="Failure reason if status is failed")
    created_at: datetime = Field(..., description="Run dispatch timestamp in UTC")


class RunSummaryResponse(AgentIQBaseModel):
    """High-level statistical and metric summary produced once a run completes."""

    run_id: UUID = Field(..., description="Associated run ID")
    total_rows: int = Field(..., ge=0, description="Total rows in the source dataset")
    total_columns: int = Field(..., ge=0, description="Total columns profiled")
    dirty_rows: int = Field(..., ge=0, description="Number of rows with at least one detected anomaly")
    clean_rows: int = Field(..., ge=0, description="Number of pristine rows")
    total_findings: int = Field(..., ge=0, description="Total number of distinct anomalies detected")
    findings_by_severity: dict[str, int] = Field(
        default_factory=dict, description="Counts broken down by severity: low, medium, high, critical"
    )
    findings_by_category: dict[str, int] = Field(
        default_factory=dict, description="Counts broken down by category"
    )
    estimated_quality_score: float = Field(
        ..., ge=0.0, le=100.0, description="Calculated data quality score (0.0 - 100.0)"
    )
