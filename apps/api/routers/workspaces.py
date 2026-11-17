"""Workspace membership and administrative management endpoints."""

from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agentiq_core.db.session import get_db_session
from agentiq_core.models.audit_log import AuditLog
from agentiq_core.models.user import User
from agentiq_core.models.workspace import WorkspaceMember
from agentiq_core.schemas.auth import (
    WorkspaceMemberCreate,
    WorkspaceMemberListResponse,
    WorkspaceMemberResponse,
)
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.errors import ErrorResponse
from apps.api.dependencies import RequireWorkspacePermission, WorkspaceContext

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Workspace Members",
    description="Retrieve all members and their roles within the target workspace.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
    },
)
async def list_workspace_members(
    workspace_id: UUID,
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
    db: AsyncSession = Depends(get_db_session),
) -> WorkspaceMemberListResponse:
    if workspace_id != context.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Header workspace mismatch with target resource.",
        )

    stmt = (
        select(WorkspaceMember)
        .options(selectinload(WorkspaceMember.user))
        .where(WorkspaceMember.workspace_id == context.workspace_id)
        .order_by(WorkspaceMember.created_at.asc())
    )
    members = (await db.execute(stmt)).scalars().all()

    items = [
        WorkspaceMemberResponse(
            id=m.id,
            workspace_id=m.workspace_id,
            user_id=m.user_id,
            role=m.role,
            user_email=m.user.email if m.user else None,
            created_at=m.created_at,
        )
        for m in members
    ]
    return WorkspaceMemberListResponse(items=items, total=len(items))


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Workspace Member",
    description="Assign a user to a workspace with a specified RBAC role (Admin only).",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "User already member"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions (Requires Admin)"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def add_workspace_member(
    workspace_id: UUID,
    payload: WorkspaceMemberCreate,
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin"])),
    db: AsyncSession = Depends(get_db_session),
) -> WorkspaceMemberResponse:
    if workspace_id != context.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Header workspace mismatch with target resource.",
        )

    # 1. Ensure user exists
    user_stmt = select(User).where(User.id == payload.user_id)
    target_user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not target_user:
        # Create user record stub if exists in Supabase
        target_user = User(
            id=payload.user_id,
            email=f"{payload.user_id}@supabase.auth",
        )
        db.add(target_user)
        await db.flush()

    # 2. Check if already member
    check_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == context.workspace_id,
        WorkspaceMember.user_id == payload.user_id,
    )
    existing = (await db.execute(check_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{payload.user_id}' is already a member of this workspace.",
        )

    # 3. Add membership
    member = WorkspaceMember(
        id=uuid4(),
        workspace_id=context.workspace_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    db.add(member)

    # 4. Audit log
    audit_entry = AuditLog(
        id=uuid4(),
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        action="workspace.member_added",
        details={"user_id": str(payload.user_id), "role": payload.role},
        timestamp=utc_now(),
    )
    db.add(audit_entry)

    await db.flush()

    return WorkspaceMemberResponse(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        role=member.role,
        user_email=target_user.email,
        created_at=member.created_at,
    )

