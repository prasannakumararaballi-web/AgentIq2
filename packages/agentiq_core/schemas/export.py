"""Data export schemas for cleaned datasets."""

from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import Field
from agentiq_core.schemas.base import AgentIQBaseModel

ExportFormat = Literal["csv", "parquet", "excel"]


class RunExportCreate(AgentIQBaseModel):
    """Configuration payload to generate a downloadable export."""

    format: ExportFormat = Field(default="csv", description="Target file format: csv, parquet, excel")
    include_cleaned_only: bool = Field(
        default=True, description="When true, exports only rows that passed or were remediated"
    )


class RunExportResponse(AgentIQBaseModel):
    """Response containing signed/temporary download link for the exported dataset."""

    id: UUID = Field(..., description="Unique export identifier")
    run_id: UUID = Field(..., description="Associated run ID")
    format: ExportFormat = Field(..., description="Generated file format")
    file_size_bytes: int = Field(..., ge=0, description="Size of generated export file in bytes")
    download_url: str = Field(..., description="Temporary or signed URL for dataset download")
    expires_at: datetime = Field(..., description="Expiration timestamp for the download URL in UTC")
    created_at: datetime = Field(..., description="Export generation timestamp in UTC")

