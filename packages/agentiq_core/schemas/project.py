"""Project schemas and models."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import Field
from agentiq_core.schemas.base import AgentIQBaseModel


class ProjectCreate(AgentIQBaseModel):
    """Payload to create a new project within a workspace."""

    name: str = Field(..., min_length=1, max_length=120, description="Display name of the project")
    description: Optional[str] = Field(
        default=None, max_length=1000, description="Optional project description"
    )
    workspace_id: UUID = Field(..., description="Target workspace ID owning this project")


class ProjectResponse(AgentIQBaseModel):
    """Response schema representing an AgentIQ project."""

    id: UUID = Field(..., description="Unique project ID")
    workspace_id: UUID = Field(..., description="ID of the owning workspace")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(default=None, description="Project description")
    created_at: datetime = Field(..., description="Creation timestamp in UTC")
    updated_at: datetime = Field(..., description="Last modification timestamp in UTC")


class ProjectListResponse(AgentIQBaseModel):
    """Paginated or listed collection of projects."""

    items: list[ProjectResponse] = Field(default_factory=list, description="List of projects")
    total: int = Field(..., description="Total number of projects matching query")
