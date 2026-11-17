"""Security, database session, and workspace-based RBAC dependencies."""

from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agentiq_core.db.session import get_db_session
from agentiq_core.models.user import User
from agentiq_core.models.workspace import Workspace, WorkspaceMember
from agentiq_core.schemas.auth import UserResponse, WorkspaceMembership, WorkspaceRole
from apps.api.security.jwt_validator import AuthenticationError, get_jwt_validator

# HTTP Bearer scheme for OpenAPI documentation
security_scheme = HTTPBearer(auto_error=False)


@dataclass
class WorkspaceContext:
    """Authoritative tenant context established for a request."""

    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    workspace: Workspace
    member: WorkspaceMember


class AuthenticatedUser(UserResponse):
    """Internal user model carrying resolved workspace permissions."""

    pass


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser:
    """Cryptographically verify Supabase JWT token and resolve/provision user identity in database."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    validator = get_jwt_validator()

    try:
        claims = await validator.verify_token(token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = UUID(str(claims["sub"]))
    email = claims.get("email") or f"{user_id}@supabase.auth"
    metadata = claims.get("user_metadata") or {}
    full_name = metadata.get("full_name") or metadata.get("name")

    # Resolve or synchronize user in local database
    stmt = (
        select(User)
        .options(
            selectinload(User.workspace_memberships).selectinload(WorkspaceMember.workspace)
        )
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=user_id,
            email=email,
            full_name=full_name,
        )
        db.add(user)
        await db.flush()

        # Provision personal default workspace for newly registered Supabase user
        from uuid import uuid4
        personal_ws = Workspace(
            id=uuid4(),
            name=f"{full_name or email.split('@')[0]}'s Workspace",
            slug=f"ws-{user_id.hex[:8]}",
        )
        db.add(personal_ws)
        await db.flush()

        member = WorkspaceMember(
            workspace_id=personal_ws.id,
            user_id=user.id,
            role="admin",
        )
        db.add(member)
        await db.flush()

        memberships_data = [
            WorkspaceMembership(
                workspace_id=personal_ws.id,
                workspace_name=personal_ws.name,
                role="admin",
            )
        ]
    else:
        # Update profile if changed
        if user.email != email or user.full_name != full_name:
            user.email = email
            user.full_name = full_name
            await db.flush()

        memberships_data = [
            WorkspaceMembership(
                workspace_id=wm.workspace_id,
                workspace_name=wm.workspace.name if wm.workspace else "Workspace",
                role=wm.role,
            )
            for wm in user.workspace_memberships
        ]

    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        workspaces=memberships_data,
        created_at=user.created_at,
    )


class RequireWorkspacePermission:
    """Verifies user has access to target workspace with required minimum role.

    Enforces strict server-side authorization: never trust user-supplied roles or workspace IDs.
    """

    def __init__(self, allowed_roles: List[WorkspaceRole]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        x_workspace_id: UUID = Header(
            ...,
            alias="X-Workspace-ID",
            description="Authoritative active workspace ID header",
        ),
        current_user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session),
    ) -> WorkspaceContext:
        # Query membership directly from database ensuring fresh authorization state
        stmt = (
            select(WorkspaceMember)
            .options(selectinload(WorkspaceMember.workspace))
            .where(
                WorkspaceMember.workspace_id == x_workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
        )
        result = await db.execute(stmt)
        membership = result.scalar_one_or_none()

        if not membership or not membership.workspace:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have access to workspace '{x_workspace_id}'.",
            )

        role_hierarchy = {"admin": 3, "reviewer": 2, "viewer": 1}
        user_rank = role_hierarchy.get(membership.role, 0)
        required_ranks = [role_hierarchy.get(r, 0) for r in self.allowed_roles]

        if not any(user_rank >= r for r in required_ranks):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {self.allowed_roles}.",
            )

        return WorkspaceContext(
            workspace_id=x_workspace_id,
            user_id=current_user.id,
            role=membership.role,
            workspace=membership.workspace,
            member=membership,
        )
