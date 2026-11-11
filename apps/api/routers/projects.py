"""Workspace project management endpoints."""

from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Query, status
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.errors import ErrorResponse
from agentiq_core.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse
from apps.api.dependencies import (
    AuthenticatedUser,
    RequireWorkspacePermission,
    get_current_user,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get(
    "",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Projects",
    description="Retrieve all projects belonging to the active workspace.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
    },
)
async def list_projects(
    membership=Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProjectListResponse:
    # Phase 1 contract mock response
    demo_project = ProjectResponse(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        workspace_id=membership.workspace_id,
        name="Demo Cleaning Project",
        description="Default sample workspace project for contract verification",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    return ProjectListResponse(items=[demo_project], total=1)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="Create a new dataset cleaning project inside the authorized workspace.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid payload"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
    },
)
async def create_project(
    payload: ProjectCreate,
    membership=Depends(RequireWorkspacePermission(allowed_roles=["admin"])),
) -> ProjectResponse:
    return ProjectResponse(
        id=uuid4(),
        workspace_id=membership.workspace_id,
        name=payload.name,
        description=payload.description,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
