"""Dataset comparison schemas comparing raw vs cleaned state."""

from typing import Any
from uuid import UUID
from pydantic import Field
from agentiq_core.schemas.base import AgentIQBaseModel


class ColumnDiff(AgentIQBaseModel):
    """Statistical difference per column between raw and cleaned versions."""

    column_name: str = Field(..., description="Name of the evaluated column")
    original_nulls: int = Field(..., ge=0, description="Null count in the raw dataset")
    cleaned_nulls: int = Field(..., ge=0, description="Null count in the remediated dataset")
    changes_count: int = Field(..., ge=0, description="Total values mutated or cleaned in this column")


class RunCompareResponse(AgentIQBaseModel):
    """Side-by-side comparison payload comparing raw vs cleaned data."""

    run_id: UUID = Field(..., description="Associated run ID")
    original_rows_count: int = Field(..., ge=0, description="Row count in raw file")
    cleaned_rows_count: int = Field(..., ge=0, description="Row count in cleaned state")
    columns_diff: list[ColumnDiff] = Field(
        default_factory=list, description="Per-column diff statistics"
    )
    preview_original: list[dict[str, Any]] = Field(
        default_factory=list, description="Top N sample rows from original raw data"
    )
    preview_cleaned: list[dict[str, Any]] = Field(
        default_factory=list, description="Top N sample rows from cleaned data"
    )
