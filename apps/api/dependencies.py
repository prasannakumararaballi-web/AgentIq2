"""Security and workspace authorization dependencies."""

from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from agentiq_core.schemas.auth import UserResponse, WorkspaceMembership, WorkspaceRole
from agentiq_core.schemas.errors import ErrorResponse

# HTTP Bearer scheme for OpenAPI documentation
security_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(UserResponse):
    """Internal user model carrying resolved workspace permissions."""

    pass


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> AuthenticatedUser:
    """Verify Supabase JWT token and extract user identity.

    In Phase 1, validates Bearer token structure and provides an authoritative
    mock user identity until Supabase connection is established in Phase 2.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    # Reject empty or obvious malformed tokens
    if len(token.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Autoritative mock user identity for Phase 1 contract validation
    default_workspace_id = UUID("00000000-0000-0000-0000-000000000001")
    return AuthenticatedUser(
        id=UUID("00000000-0000-0000-0000-000000000099"),
        email="developer@example.com",
        full_name="AgentIQ Developer",
        workspaces=[
            WorkspaceMembership(
                workspace_id=default_workspace_id,
                workspace_name="Engineering Workspace",
                role="admin",
            )
        ],
        created_at="2026-01-01T00:00:00Z",
    )


class RequireWorkspacePermission:
    """Verifies user has access to target workspace with required minimum role.

    Enforces server-side authorization: never trust user-supplied roles or workspace IDs.
    """

    def __init__(self, allowed_roles: List[WorkspaceRole]):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        workspace_id: UUID = Header(
            ...,
            alias="X-Workspace-ID",
            description="Authoritative active workspace ID header",
        ),
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> WorkspaceMembership:
        # Find membership in user's verified token memberships
        membership = next(
            (m for m in current_user.workspaces if m.workspace_id == workspace_id),
            None,
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have access to workspace '{workspace_id}'.",
            )

        role_hierarchy = {"admin": 3, "reviewer": 2, "viewer": 1}
        user_rank = role_hierarchy.get(membership.role, 0)
        required_ranks = [role_hierarchy.get(r, 0) for r in self.allowed_roles]

        if not any(user_rank >= r for r in required_ranks):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {self.allowed_roles}.",
            )

        return membership
