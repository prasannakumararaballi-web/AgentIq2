"""Workspace project management endpoints with tenant isolation."""

from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentiq_core.db.session import get_db_session
from agentiq_core.models.audit_log import AuditLog
from agentiq_core.models.project import Project
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.errors import ErrorResponse
from agentiq_core.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse
from apps.api.dependencies import RequireWorkspacePermission, WorkspaceContext

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
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProjectListResponse:
    # 1. Total count scoped strictly to tenant workspace
    count_stmt = select(func.count()).select_from(Project).where(Project.workspace_id == context.workspace_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    # 2. Paginated projects query
    query = (
        select(Project)
        .where(Project.workspace_id == context.workspace_id)
        .order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    projects = result.scalars().all()

    items = [
        ProjectResponse(
            id=p.id,
            workspace_id=p.workspace_id,
            name=p.name,
            description=p.description,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in projects
    ]

    return ProjectListResponse(items=items, total=total)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="Create a new dataset cleaning project inside the authorized workspace.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid payload or duplicate name"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
    },
)
async def create_project(
    payload: ProjectCreate,
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin"])),
    db: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    # Check duplicate name within workspace
    check_stmt = select(Project).where(
        Project.workspace_id == context.workspace_id,
        Project.name == payload.name,
    )
    existing = (await db.execute(check_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with name '{payload.name}' already exists in this workspace.",
        )

    project = Project(
        id=uuid4(),
        workspace_id=context.workspace_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(project)

    # Immutable audit log
    audit_entry = AuditLog(
        id=uuid4(),
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        action="project.created",
        details={"project_id": str(project.id), "name": project.name},
        timestamp=utc_now(),
    )
    db.add(audit_entry)

    await db.flush()

    return ProjectResponse(
        id=project.id,
        workspace_id=project.workspace_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
