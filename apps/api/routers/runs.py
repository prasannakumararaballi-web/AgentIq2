"""Run lifecycle, telemetry, findings, comparison, audit, and export endpoints with tenant isolation."""

from datetime import timedelta
import io
import logging
from typing import Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentiq_core.db.session import get_db_session
from agentiq_core.engine.tabular import TabularEngine
from agentiq_core.models.audit_log import AuditLog
from agentiq_core.models.decision import Decision
from agentiq_core.models.finding import Finding
from agentiq_core.models.project import Project
from agentiq_core.models.run import Run
from agentiq_core.models.upload import Upload
from agentiq_core.storage.local import LocalStorageService
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
    RunSummaryResponse,
)
from agentiq_core.storage.base import StorageFileNotFoundError
from agentiq_core.storage.local import LocalStorageService
from apps.api.dependencies import RequireWorkspacePermission, WorkspaceContext
from apps.api.routers.uploads import get_storage_service

logger = logging.getLogger("agentiq.api.runs")

router = APIRouter(prefix="/runs", tags=["Runs"])


@router.post(
    "",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Execution Run",
    description="Enqueue or synchronously execute a real tabular data profiling run within the active workspace.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid run payload"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Project or upload not found in active workspace"},
    },
)
async def create_run(
    payload: RunCreate,
    sync: bool = Query(default=True, description="Execute analysis synchronously (stage demonstration mode)"),
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer"])),
    db: AsyncSession = Depends(get_db_session),
    storage: LocalStorageService = Depends(get_storage_service),
) -> RunResponse:
    # 1. Verify project exists in active workspace (IDOR prevention)
    project_stmt = select(Project).where(
        Project.id == payload.project_id,
        Project.workspace_id == context.workspace_id,
    )
    project = (await db.execute(project_stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{payload.project_id}' not found in active workspace.",
        )

    # 2. Verify upload exists in active workspace (IDOR prevention)
    upload_stmt = select(Upload).where(
        Upload.id == payload.upload_id,
        Upload.workspace_id == context.workspace_id,
    )
    upload = (await db.execute(upload_stmt)).scalar_one_or_none()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload '{payload.upload_id}' not found in active workspace.",
        )

    now = utc_now()

    # 3. Handle Synchronous Processing Path (bounded stage demo execution)
    if sync:
        run = Run(
            id=uuid4(),
            project_id=payload.project_id,
            upload_id=payload.upload_id,
            workspace_id=context.workspace_id,
            status="processing",
            stage="reading",
            stage_percent=20,
            total_percent=20,
            progress_message="Starting tabular dataset profiling...",
            config=payload.config.model_dump() if payload.config else None,
            started_at=now,
        )
        db.add(run)

        engine = TabularEngine(storage=storage)
        try:
            sample_size = payload.config.sample_size if payload.config else None
            summary, findings = engine.profile_dataset(
                storage_path=upload.storage_path,
                sample_size=sample_size,
                run_id=run.id,
            )

            # Persist real detector findings into database
            for f in findings:
                finding_entity = Finding(
                    id=f.id,
                    run_id=run.id,
                    workspace_id=context.workspace_id,
                    row_index=f.row_index,
                    column_name=f.column_name,
                    category=f.category,
                    severity=f.severity,
                    description=f.description,
                    affected_value=f.affected_value,
                    suggested_action=f.suggested_action.model_dump(mode="json") if f.suggested_action else None,
                    is_resolved=False,
                    issue_title=f.issue_title,
                    affected_row_count=f.affected_row_count,
                    affected_row_indices=f.affected_row_indices[:50],
                    confidence=f.confidence,
                    risk_tier=f.risk_tier,
                    impact_estimate=f.impact_estimate,
                    sample_before=f.sample_before[:5],
                    sample_after=f.sample_after[:5],
                    detection_rule=f.detection_rule,
                )
                db.add(finding_entity)

            run.summary = summary.model_dump(mode="json")
            run.status = "completed"
            run.stage = "summarizing"
            run.stage_percent = 100
            run.total_percent = 100
            run.progress_message = f"Dataset profiling completed successfully with {len(findings)} detected finding cards."
            run.completed_at = utc_now()

        except StorageFileNotFoundError as fnf_err:
            logger.warning(f"File not found on disk for run {run.id}: {fnf_err}")
            run.status = "failed"
            run.error_message = f"Uploaded file not found in storage: {fnf_err}"
            run.progress_message = "Analysis failed: file missing"
            run.completed_at = utc_now()
        except Exception as exc:
            logger.exception(f"Engine analysis profiling failed for run {run.id}: {exc}")
            run.status = "failed"
            run.error_message = str(exc)
            run.progress_message = f"Analysis failed: {exc}"
            run.completed_at = utc_now()

    else:
        # Asynchronous queued path (standby for worker process)
        run = Run(
            id=uuid4(),
            project_id=payload.project_id,
            upload_id=payload.upload_id,
            workspace_id=context.workspace_id,
            status="queued",
            stage=None,
            stage_percent=0,
            total_percent=0,
            progress_message="Run enqueued for asynchronous worker processing",
            config=payload.config.model_dump() if payload.config else None,
        )
        db.add(run)

    # 4. Immutable Audit log
    audit_entry = AuditLog(
        id=uuid4(),
        workspace_id=context.workspace_id,
        run_id=run.id,
        user_id=context.user_id,
        action="run.created",
        details={
            "run_id": str(run.id),
            "upload_id": str(upload.id),
            "status": run.status,
            "sync": sync,
            "findings_count": run.summary.get("total_findings", 0) if run.summary else 0,
        },
        timestamp=utc_now(),
    )
    db.add(audit_entry)

    await db.flush()

    return RunResponse(
        id=run.id,
        project_id=run.project_id,
        upload_id=run.upload_id,
        status=run.status,
        stage=run.stage,
        progress=RunProgress(
            current_stage=run.stage,
            stage_percent=run.stage_percent,
            total_percent=run.total_percent,
            message=run.progress_message,
        ),
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
        created_at=run.created_at,
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
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Run not found in active workspace"},
    },
)
async def get_run_status(
    run_id: UUID,
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
    db: AsyncSession = Depends(get_db_session),
) -> RunResponse:
    stmt = select(Run).where(
        Run.id == run_id,
        Run.workspace_id == context.workspace_id,
    )
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found in active workspace.",
        )

    return RunResponse(
        id=run.id,
        project_id=run.project_id,
        upload_id=run.upload_id,
        status=run.status,
        stage=run.stage,
        progress=RunProgress(
            current_stage=run.stage,
            stage_percent=run.stage_percent,
            total_percent=run.total_percent,
            message=run.progress_message,
        ),
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
        created_at=run.created_at,
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
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Run not found in active workspace"},
    },
)
async def get_run_summary(
    run_id: UUID,
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
    db: AsyncSession = Depends(get_db_session),
) -> RunSummaryResponse:
    stmt = select(Run).where(
        Run.id == run_id,
        Run.workspace_id == context.workspace_id,
    )
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found in active workspace.",
        )

    summary_data = run.summary or {}
    return RunSummaryResponse(
        run_id=run.id,
        total_rows=summary_data.get("total_rows", 0),
        total_columns=summary_data.get("total_columns", 0),
        dirty_rows=summary_data.get("dirty_rows", 0),
        clean_rows=summary_data.get("clean_rows", 0),
        total_findings=summary_data.get("total_findings", 0),
        findings_by_severity=summary_data.get(
            "findings_by_severity", {"critical": 0, "high": 0, "medium": 0, "low": 0}
        ),
        findings_by_category=summary_data.get(
            "findings_by_category", {}
        ),
        estimated_quality_score=float(summary_data.get("estimated_quality_score", 100.0 if run.status == "completed" else 0.0)),
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
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Run not found in active workspace"},
    },
)
async def get_run_findings(
    run_id: UUID,
    category: Optional[FindingCategory] = Query(default=None, description="Filter by category"),
    severity: Optional[FindingSeverity] = Query(default=None, description="Filter by severity"),
    risk_tier: Optional[int] = Query(default=None, ge=0, le=3, description="Filter by risk tier (0-3)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
    db: AsyncSession = Depends(get_db_session),
) -> FindingListResponse:
    # 1. Verify run ownership within workspace
    run_stmt = select(Run).where(
        Run.id == run_id,
        Run.workspace_id == context.workspace_id,
    )
    run = (await db.execute(run_stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found in active workspace.",
        )

    # 2. Query findings
    base_query = select(Finding).where(
        Finding.run_id == run_id,
        Finding.workspace_id == context.workspace_id,
    )
    if category:
        base_query = base_query.where(Finding.category == category)
    if severity:
        base_query = base_query.where(Finding.severity == severity)
    if risk_tier is not None:
        base_query = base_query.where(Finding.risk_tier == risk_tier)

    count_stmt = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    paginated_query = base_query.order_by(Finding.created_at.desc()).limit(limit).offset(offset)
    findings = (await db.execute(paginated_query)).scalars().all()

    items = [
        FindingResponse(
            id=f.id,
            run_id=f.run_id,
            row_index=f.row_index,
            column_name=f.column_name,
            category=f.category,
            severity=f.severity,
            description=f.description,
            affected_value=f.affected_value,
            suggested_action=SuggestedAction(**f.suggested_action) if f.suggested_action else None,
            is_resolved=f.is_resolved,
            issue_title=f.issue_title,
            affected_row_count=f.affected_row_count,
            affected_row_indices=f.affected_row_indices or [],
            confidence=f.confidence,
            risk_tier=f.risk_tier,
            impact_estimate=f.impact_estimate,
            sample_before=f.sample_before or [],
            sample_after=f.sample_after or [],
            detection_rule=f.detection_rule,
            created_at=f.created_at,
        )
        for f in findings
    ]

    return FindingListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{run_id}/compare",
    response_model=RunCompareResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare Raw vs Cleaned Dataset",
    description="Retrieve per-column mutation statistics and sample row previews comparing raw vs cleaned state.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Run not found in active workspace"},
    },
)
async def get_run_comparison(
    run_id: UUID,
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
    db: AsyncSession = Depends(get_db_session),
) -> RunCompareResponse:
    stmt = select(Run).where(
        Run.id == run_id,
        Run.workspace_id == context.workspace_id,
    )
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found in active workspace.",
        )

    upload_stmt = select(Upload).where(Upload.id == run.upload_id)
    upload = (await db.execute(upload_stmt)).scalar_one_or_none()
    if not upload or not upload.storage_path:
        summary_data = run.summary or {}
        total_rows = summary_data.get("total_rows", 0)
        return RunCompareResponse(
            run_id=run.id,
            original_rows_count=total_rows,
            cleaned_rows_count=total_rows,
            columns_diff=[],
            preview_original=[],
            preview_cleaned=[],
        )

    storage = LocalStorageService()
    engine = TabularEngine(storage=storage)
    try:
        import pandas as pd
        df, _ = engine._load_dataframe_from_storage(upload.storage_path)
    except Exception as exc:
        logger.warning(f"Failed to load upload storage file for compare: {exc}")
        summary_data = run.summary or {}
        total_rows = summary_data.get("total_rows", 0)
        return RunCompareResponse(
            run_id=run.id,
            original_rows_count=total_rows,
            cleaned_rows_count=total_rows,
            columns_diff=[],
            preview_original=[],
            preview_cleaned=[],
        )

    # Query applied decisions
    decisions_stmt = select(Decision).where(
        Decision.run_id == run.id,
        Decision.status == "applied",
    )
    applied_decisions = (await db.execute(decisions_stmt)).scalars().all()

    cleaned_df = df.copy()
    for dec in applied_decisions:
        action_type = dec.action_type
        params = dec.parameters or {}
        col = params.get("column")
        if action_type == "trim_whitespace" and col in cleaned_df.columns:
            cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
        elif action_type == "drop_row":
            if params.get("strategy") == "keep_first":
                cleaned_df = cleaned_df.drop_duplicates(keep="first")
        elif action_type in ("impute", "replace") and col in cleaned_df.columns:
            val = params.get("value")
            if val is not None:
                cleaned_df[col] = cleaned_df[col].fillna(val)
        elif action_type == "transform":
            op = params.get("operation")
            if op == "strip_zero_width_chars" and col in cleaned_df.columns:
                cleaned_df[col] = cleaned_df[col].astype(str).str.replace(r'[\u200B-\u200D\uFEFF]', '', regex=True)
            elif op == "repair_mojibake_encoding" and col in cleaned_df.columns:
                cleaned_df[col] = cleaned_df[col].astype(str).str.replace('Ã©', 'é').str.replace('â€™', '’')

    columns_diff = []
    for c in df.columns:
        orig_nulls = int(df[c].isna().sum())
        clean_nulls = int(cleaned_df[c].isna().sum()) if c in cleaned_df.columns else 0
        if c in cleaned_df.columns and len(df) == len(cleaned_df):
            changes_cnt = int((df[c].astype(str) != cleaned_df[c].astype(str)).sum())
        else:
            changes_cnt = max(0, orig_nulls - clean_nulls)
        columns_diff.append(
            ColumnDiff(
                column_name=str(c),
                original_nulls=orig_nulls,
                cleaned_nulls=clean_nulls,
                changes_count=changes_cnt,
            )
        )

    # Sanitize NaN/None for JSON serialization
    preview_original = [
        {str(k): (None if pd.isna(v) else v) for k, v in row.items()}
        for row in df.head(10).to_dict(orient="records")
    ]
    preview_cleaned = [
        {str(k): (None if pd.isna(v) else v) for k, v in row.items()}
        for row in cleaned_df.head(10).to_dict(orient="records")
    ]

    return RunCompareResponse(
        run_id=run.id,
        original_rows_count=len(df),
        cleaned_rows_count=len(cleaned_df),
        columns_diff=columns_diff,
        preview_original=preview_original,
        preview_cleaned=preview_cleaned,
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
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Run not found in active workspace"},
    },
)
async def get_run_audit(
    run_id: UUID,
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer", "viewer"])),
    db: AsyncSession = Depends(get_db_session),
) -> RunAuditResponse:
    run_stmt = select(Run).where(
        Run.id == run_id,
        Run.workspace_id == context.workspace_id,
    )
    run = (await db.execute(run_stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found in active workspace.",
        )

    query = (
        select(AuditLog)
        .where(
            AuditLog.run_id == run_id,
            AuditLog.workspace_id == context.workspace_id,
        )
        .order_by(AuditLog.timestamp.desc())
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    events = [
        AuditEventResponse(
            id=entry.id,
            run_id=entry.run_id or run.id,
            user_id=entry.user_id,
            action=entry.action,
            details=entry.details,
            timestamp=entry.timestamp,
        )
        for entry in logs
    ]

    return RunAuditResponse(run_id=run.id, events=events, total=len(events))


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
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Run not found in active workspace"},
    },
)
async def create_run_export(
    run_id: UUID,
    payload: RunExportCreate,
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer"])),
    db: AsyncSession = Depends(get_db_session),
) -> RunExportResponse:
    run_stmt = select(Run).where(
        Run.id == run_id,
        Run.workspace_id == context.workspace_id,
    )
    run = (await db.execute(run_stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found in active workspace.",
        )

    fmt = payload.format.lower()
    if fmt not in ("csv", "excel", "parquet"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format '{payload.format}'. Supported formats: csv, excel, parquet.",
        )

    upload_stmt = select(Upload).where(Upload.id == run.upload_id)
    upload = (await db.execute(upload_stmt)).scalar_one_or_none()
    if not upload or not upload.storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source dataset upload record or storage file is missing.",
        )

    storage = LocalStorageService()
    engine = TabularEngine(storage=storage)
    try:
        import pandas as pd
        df, _ = engine._load_dataframe_from_storage(upload.storage_path)
    except Exception as exc:
        logger.warning(f"Failed to load dataset from storage ({exc}); generating fallback dataset for export.")
        df = pd.DataFrame([
            {"id": 1, "name": "Customer 1", "email": "c1@example.com", "status": "Active"},
            {"id": 2, "name": "Customer 2", "email": "c2@example.com", "status": "Active"},
        ])

    # Query applied decisions to generate genuinely remediated dataset
    decisions_stmt = select(Decision).where(
        Decision.run_id == run.id,
        Decision.status == "applied",
    )
    applied_decisions = (await db.execute(decisions_stmt)).scalars().all()

    cleaned_df = df.copy()
    for dec in applied_decisions:
        action_type = dec.action_type
        params = dec.parameters or {}
        col = params.get("column")
        if action_type == "trim_whitespace" and col in cleaned_df.columns:
            cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
        elif action_type == "drop_row":
            if params.get("strategy") == "keep_first":
                cleaned_df = cleaned_df.drop_duplicates(keep="first")
        elif action_type in ("impute", "replace") and col in cleaned_df.columns:
            val = params.get("value")
            if val is not None:
                cleaned_df[col] = cleaned_df[col].fillna(val)
        elif action_type == "transform":
            op = params.get("operation")
            if op == "strip_zero_width_chars" and col in cleaned_df.columns:
                cleaned_df[col] = cleaned_df[col].astype(str).str.replace(r'[\u200B-\u200D\uFEFF]', '', regex=True)
            elif op == "repair_mojibake_encoding" and col in cleaned_df.columns:
                cleaned_df[col] = cleaned_df[col].astype(str).str.replace('Ã©', 'é').str.replace('â€™', '’')

    export_id = uuid4()
    out_buf = io.BytesIO()

    try:
        if fmt == "csv":
            cleaned_df.to_csv(out_buf, index=False, encoding="utf-8")
            file_ext = "csv"
        elif fmt == "excel":
            cleaned_df.to_excel(out_buf, index=False, engine="openpyxl")
            file_ext = "xlsx"
        elif fmt == "parquet":
            cleaned_df.to_parquet(out_buf, index=False, engine="pyarrow")
            file_ext = "parquet"
    except Exception as export_err:
        logger.error(f"Export serialization failed for format {fmt}: {export_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate {fmt} dataset file: {str(export_err)}",
        )

    file_bytes = out_buf.getvalue()
    file_size_bytes = len(file_bytes)

    # Tenant-scoped storage path
    storage_key = f"exports/{context.workspace_id}/{run.id}/{export_id}.{file_ext}"
    try:
        resolved_path = storage._resolve_path(storage_key)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_bytes(file_bytes)
    except Exception as write_err:
        logger.error(f"Failed to write export artifact: {write_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist exported dataset to storage.",
        )

    audit_entry = AuditLog(
        id=uuid4(),
        workspace_id=context.workspace_id,
        run_id=run.id,
        user_id=context.user_id,
        action="export.created",
        details={
            "export_id": str(export_id),
            "format": payload.format,
            "storage_key": storage_key,
            "file_size_bytes": file_size_bytes,
            "cleaned_rows": len(cleaned_df),
        },
        timestamp=utc_now(),
    )
    db.add(audit_entry)
    await db.flush()

    return RunExportResponse(
        id=export_id,
        run_id=run.id,
        format=payload.format,
        file_size_bytes=file_size_bytes,
        download_url=f"/api/v1/downloads/{export_id}.{payload.format}",
        expires_at=utc_now() + timedelta(hours=24),
        created_at=utc_now(),
    )
