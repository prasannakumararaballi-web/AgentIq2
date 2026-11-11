"""Run lifecycle, profiling, telemetry, findings, comparison, audit, and export endpoints."""

from datetime import timedelta
from typing import Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from agentiq_core.schemas.audit import AuditEventResponse, RunAuditResponse
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.compare import ColumnDiff, RunCompareResponse
from agentiq_core.schemas.errors import ErrorResponse
from agentiq_core.schemas.export import RunExportCreate, RunExportResponse
from agentiq_core.schemas.finding import (
    FindingCategory,
    FindingListResponse,
    FindingResponse,
    FindingSeverity,
    SuggestedAction,
)
from agentiq_core.schemas.run import (
    RunCreate,
    RunProgress,
    RunResponse,
    RunStatus,
    RunSummaryResponse,
)
from apps.api.dependencies import RequireWorkspacePermission

router = APIRouter(prefix="/runs", tags=["Runs"])


@router.post(
    "",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Execution Run",
    description="Enqueue an asynchronous data profiling and AI-assisted anomaly detection run.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid run payload"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
    },
)
async def create_run(
    payload: RunCreate,
    membership=Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer"])),
) -> RunResponse:
    run_id = uuid4()
    return RunResponse(
        id=run_id,
        project_id=payload.project_id,
        upload_id=payload.upload_id,
        status="queued",
        stage=None,
        progress=RunProgress(
            current_stage=None,
            stage_percent=0,
            total_percent=0,
            message="Run enqueued for asynchronous worker processing",
        ),
        started_at=None,
        completed_at=None,
        error_message=None,
        created_at=utc_now(),
    )


@router.get(
    "/{run_id}",
    response_model=RunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Run Status & Progress",
    description="Poll current execution status and stage progress (recommended poll interval: 2 seconds).",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Run not found"},
    },
)
async def get_run(
    run_id: UUID,
    membership=Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
) -> RunResponse:
    # Phase 1 mock contract implementation
    return RunResponse(
        id=run_id,
        project_id=UUID("11111111-1111-1111-1111-111111111111"),
        upload_id=UUID("22222222-2222-2222-2222-222222222222"),
        status="completed",
        stage="summarizing",
        progress=RunProgress(
            current_stage="summarizing",
            stage_percent=100,
            total_percent=100,
            message="Profiling and AI explanation completed successfully",
        ),
        started_at=utc_now(),
        completed_at=utc_now(),
        error_message=None,
        created_at=utc_now(),
    )


@router.get(
    "/{run_id}/summary",
    response_model=RunSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Run Summary",
    description="Retrieve high-level statistical overview and anomaly counts for a completed run.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Run not found"},
    },
)
async def get_run_summary(
    run_id: UUID,
    membership=Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
) -> RunSummaryResponse:
    return RunSummaryResponse(
        run_id=run_id,
        total_rows=10000,
        total_columns=12,
        dirty_rows=145,
        clean_rows=9855,
        total_findings=160,
        findings_by_severity={"critical": 10, "high": 35, "medium": 75, "low": 40},
        findings_by_category={
            "missing_value": 80,
            "outlier": 35,
            "type_mismatch": 25,
            "duplicate": 20,
        },
        estimated_quality_score=94.2,
    )


@router.get(
    "/{run_id}/findings",
    response_model=FindingListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Run Findings",
    description="Fetch paginated list of anomalies, quality violations, and AI-suggested remediations.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Run not found"},
    },
)
async def get_run_findings(
    run_id: UUID,
    category: Optional[FindingCategory] = Query(default=None, description="Filter by category"),
    severity: Optional[FindingSeverity] = Query(default=None, description="Filter by severity"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    membership=Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
) -> FindingListResponse:
    demo_finding = FindingResponse(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        run_id=run_id,
        row_index=42,
        column_name="email",
        category="format_inconsistency",
        severity="high",
        description="Value does not match RFC standard email formatting pattern.",
        affected_value="user@@domain..com",
        suggested_action=SuggestedAction(
            action_type="replace",
            parameters={"regex_replace": "@+", "replacement": "@"},
            rationale="AI detected redundant consecutive '@' symbols likely originating from form copy-paste error.",
        ),
        is_resolved=False,
        created_at=utc_now(),
    )
    return FindingListResponse(items=[demo_finding], total=1, limit=limit, offset=offset)


@router.get(
    "/{run_id}/compare",
    response_model=RunCompareResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare Raw vs Cleaned Dataset",
    description="Retrieve per-column mutation statistics and sample row previews comparing raw vs cleaned state.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Run not found"},
    },
)
async def get_run_comparison(
    run_id: UUID,
    membership=Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
) -> RunCompareResponse:
    return RunCompareResponse(
        run_id=run_id,
        original_rows_count=10000,
        cleaned_rows_count=9980,
        columns_diff=[
            ColumnDiff(
                column_name="email",
                original_nulls=45,
                cleaned_nulls=0,
                changes_count=120,
            ),
            ColumnDiff(
                column_name="age",
                original_nulls=10,
                cleaned_nulls=0,
                changes_count=10,
            ),
        ],
        preview_original=[{"id": 1, "email": "invalid@@domain.com", "age": None}],
        preview_cleaned=[{"id": 1, "email": "invalid@domain.com", "age": 28}],
    )


@router.get(
    "/{run_id}/audit",
    response_model=RunAuditResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Run Audit Trail",
    description="Retrieve immutable chronological audit records of all decisions and status transitions.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Run not found"},
    },
)
async def get_run_audit(
    run_id: UUID,
    membership=Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
) -> RunAuditResponse:
    demo_event = AuditEventResponse(
        id=uuid4(),
        run_id=run_id,
        user_id=UUID("00000000-0000-0000-0000-000000000099"),
        action="run.completed",
        details={"total_findings": 160, "duration_seconds": 14.2},
        timestamp=utc_now(),
    )
    return RunAuditResponse(run_id=run_id, events=[demo_event], total=1)


@router.post(
    "/{run_id}/exports",
    response_model=RunExportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Cleaned Dataset Export",
    description="Generate a downloadable cleaned dataset in CSV, Parquet, or Excel format.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid export parameters"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Run not found"},
    },
)
async def create_run_export(
    run_id: UUID,
    payload: RunExportCreate,
    membership=Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer"])),
) -> RunExportResponse:
    export_id = uuid4()
    return RunExportResponse(
        id=export_id,
        run_id=run_id,
        format=payload.format,
        file_size_bytes=1048576,
        download_url=f"/api/v1/downloads/{export_id}.{payload.format}",
        expires_at=utc_now() + timedelta(hours=24),
        created_at=utc_now(),
    )

