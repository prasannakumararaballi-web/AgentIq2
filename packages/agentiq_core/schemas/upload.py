"""Dataset file upload schemas."""

from datetime import datetime
from typing import List, Optional
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
    file_hash: Optional[str] = Field(default=None, description="SHA-256 cryptographic digest of the raw uploaded file")
    row_count: Optional[int] = Field(default=None, description="Introspected total row count")
    column_count: Optional[int] = Field(default=None, description="Introspected total column count")
    columns: Optional[List[str]] = Field(default=None, description="Introspected column headers (deduplicated)")
    sheet_names: Optional[List[str]] = Field(default=None, description="Discovered sheet names for Excel workbooks")
    detected_encoding: Optional[str] = Field(default=None, description="Detected text character encoding")
    warnings: List[str] = Field(default_factory=list, description="Parser warnings (e.g. duplicate headers renamed)")
    storage_path: str = Field(..., description="Internal preserved storage key for raw data")
    created_at: datetime = Field(..., description="Upload timestamp in UTC")
