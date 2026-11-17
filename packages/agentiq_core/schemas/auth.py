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


class WorkspaceMemberCreate(AgentIQBaseModel):
    """Payload for adding or inviting a user to a workspace."""

    user_id: UUID = Field(..., description="Supabase user ID to associate with workspace")
    role: WorkspaceRole = Field(default="viewer", description="Role to assign: admin, reviewer, or viewer")


class WorkspaceMemberResponse(AgentIQBaseModel):
    """Response representing a workspace membership record."""

    id: UUID = Field(..., description="Membership record unique ID")
    workspace_id: UUID = Field(..., description="Target workspace ID")
    user_id: UUID = Field(..., description="Member user ID")
    role: WorkspaceRole = Field(..., description="Assigned role: admin, reviewer, or viewer")
    user_email: Optional[str] = Field(default=None, description="Email address of the member user")
    created_at: datetime = Field(..., description="Membership assignment timestamp in UTC")


class WorkspaceMemberListResponse(AgentIQBaseModel):
    """Collection of members in a workspace."""

    items: list[WorkspaceMemberResponse] = Field(default_factory=list, description="List of members")
    total: int = Field(..., description="Total members in workspace")


class UserResponse(AgentIQBaseModel):
    """Response schema for authenticated user identity and workspace memberships."""

    id: UUID = Field(..., description="Supabase Auth UUID of the user")
    email: EmailStr = Field(..., description="User's email address")
    full_name: Optional[str] = Field(default=None, description="User's display or full name")
    workspaces: list[WorkspaceMembership] = Field(
        default_factory=list, description="List of workspaces accessible to the user"
    )
    created_at: datetime = Field(..., description="Account creation timestamp in UTC")

