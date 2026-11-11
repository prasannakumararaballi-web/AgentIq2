"""Dataset file upload schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import Field
from agentiq_core.schemas.base import AgentIQBaseModel


class UploadResponse(AgentIQBaseModel):
    """Response schema following successful file upload."""

    id: UUID = Field(..., description="Unique upload identifier")
    project_id: UUID = Field(..., description="Associated project ID")
    filename: str = Field(..., description="Original filename of the uploaded file")
    file_size_bytes: int = Field(..., description="Size of uploaded file in bytes")
    mime_type: str = Field(..., description="Detected MIME type (e.g. text/csv, application/vnd.apache.parquet)")
    row_count: Optional[int] = Field(default=None, description="Pre-computed row count if available during upload")
    column_count: Optional[int] = Field(default=None, description="Pre-computed column count if available")
    storage_path: str = Field(..., description="Internal preserved storage path for raw data")
    created_at: datetime = Field(..., description="Upload timestamp in UTC")
