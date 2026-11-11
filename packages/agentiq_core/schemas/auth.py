"""Authentication and authorization schemas."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import EmailStr, Field
from agentiq_core.schemas.base import AgentIQBaseModel

WorkspaceRole = Literal["admin", "reviewer", "viewer"]


class WorkspaceMembership(AgentIQBaseModel):
    """Represents a user's membership and assigned role within a workspace."""

    workspace_id: UUID = Field(..., description="Unique workspace ID")
    workspace_name: str = Field(..., description="Human-readable name of the workspace")
    role: WorkspaceRole = Field(..., description="Role permissions: admin, reviewer, or viewer")


class UserResponse(AgentIQBaseModel):
    """Response schema for authenticated user identity and workspace memberships."""

    id: UUID = Field(..., description="Supabase Auth UUID of the user")
    email: EmailStr = Field(..., description="User's email address")
    full_name: Optional[str] = Field(default=None, description="User's display or full name")
    workspaces: list[WorkspaceMembership] = Field(
        default_factory=list, description="List of workspaces accessible to the user"
    )
    created_at: datetime = Field(..., description="Account creation timestamp in UTC")

