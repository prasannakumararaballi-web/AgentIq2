"""Dataset upload endpoints supporting multipart/form-data streaming with storage and parsing."""

import logging
import os
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentiq_core.db.session import get_db_session
from agentiq_core.models.audit_log import AuditLog
from agentiq_core.models.project import Project
from agentiq_core.models.upload import Upload
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.errors import ErrorResponse
from agentiq_core.schemas.upload import UploadResponse
from agentiq_core.storage import (
    DatasetParseError,
    DatasetParser,
    EmptyDatasetError,
    LocalStorageService,
    StorageQuotaExceededError,
)
from apps.api.config import settings
from apps.api.dependencies import RequireWorkspacePermission, WorkspaceContext

logger = logging.getLogger("agentiq.api.uploads")

router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED_EXTENSIONS = {".csv", ".tsv", ".parquet", ".xlsx", ".xlsm", ".json"}
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


def get_storage_service() -> LocalStorageService:
    """Dependency / provider for storage service."""
    return LocalStorageService(base_path=settings.local_storage_path)


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Dataset File",
    description="Upload raw dataset file via multipart/form-data with streaming validation, SHA-256 hashing, and metadata introspection.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid file type, empty file, or corrupt tabular format"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Project not found in active workspace"},
        status.HTTP_413_CONTENT_TOO_LARGE: {"model": ErrorResponse, "description": "File exceeds allowed size limit (100MB)"},
    },
)
async def upload_file(
    file: UploadFile = File(..., description="Raw dataset file (.csv, .tsv, .parquet, .xlsx)"),
    project_id: UUID = Form(..., description="Target project ID"),
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer"])),
    db: AsyncSession = Depends(get_db_session),
    storage: LocalStorageService = Depends(get_storage_service),
) -> UploadResponse:
    # 1. Verify project exists and belongs strictly to active tenant workspace (IDOR prevention)
    project_stmt = select(Project).where(
        Project.id == project_id,
        Project.workspace_id == context.workspace_id,
    )
    project = (await db.execute(project_stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found in active workspace.",
        )

    # 2. Filename & Extension Validation
    filename = file.filename or "unknown_upload.csv"
    _, ext = os.path.splitext(filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # 3. Build isolated storage key
    upload_id = uuid4()
    storage_key = storage.build_raw_storage_key(
        workspace_id=context.workspace_id,
        project_id=project_id,
        upload_id=upload_id,
        filename=filename,
    )

    # 4. Stream file chunks to persistent storage while computing SHA-256 and enforcing byte limits
    async def chunk_generator():
        while True:
            chunk = await file.read(64 * 1024)
            if not chunk:
                break
            yield chunk

    try:
        saved_key, sha256_hex, total_bytes = await storage.save_stream(
            key=storage_key,
            stream=chunk_generator(),
            max_size_bytes=MAX_FILE_SIZE_BYTES,
        )
    except StorageQuotaExceededError as quota_err:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds maximum allowable limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
        )
    except Exception as stream_err:
        logger.error(f"Upload streaming failed: {stream_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stream and persist upload: {stream_err}",
        )

    # 5. Check empty file (0 bytes)
    if total_bytes == 0:
        await storage.delete(storage_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty (0 bytes).",
        )

    # 6. Introspect dataset structure, encoding, headers, and row count
    local_path = storage.get_local_path(storage_key)
    try:
        if local_path and local_path.is_file():
            metadata = DatasetParser.introspect_dataset(local_path, filename)
        else:
            with storage.open_reader(storage_key) as reader:
                metadata = DatasetParser.introspect_dataset(reader, filename)
    except EmptyDatasetError as empty_err:
        await storage.delete(storage_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(empty_err),
        )
    except DatasetParseError as parse_err:
        await storage.delete(storage_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse tabular dataset: {parse_err}",
        )
    except Exception as exc:
        await storage.delete(storage_key)
        logger.exception("Unexpected error during tabular introspection")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse file as tabular dataset: {exc}",
        )

    # 7. Persist database record with atomic cleanup on failure
    try:
        upload = Upload(
            id=upload_id,
            project_id=project_id,
            workspace_id=context.workspace_id,
            filename=filename,
            file_size_bytes=total_bytes,
            mime_type=file.content_type or "application/octet-stream",
            storage_path=saved_key,
            file_hash=sha256_hex,
            row_count=metadata.row_count,
            column_count=metadata.column_count,
            metadata_={
                "columns": metadata.columns,
                "original_columns": metadata.original_columns,
                "sheet_names": metadata.sheet_names,
                "active_sheet": metadata.active_sheet,
                "detected_encoding": metadata.detected_encoding,
                "warnings": metadata.warnings,
            },
        )
        db.add(upload)

        # 8. Immutable audit log
        audit_entry = AuditLog(
            id=uuid4(),
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            action="upload.created",
            details={
                "upload_id": str(upload.id),
                "filename": filename,
                "file_size": total_bytes,
                "file_hash": sha256_hex,
                "row_count": metadata.row_count,
                "column_count": metadata.column_count,
            },
            timestamp=utc_now(),
        )
        db.add(audit_entry)

        await db.flush()
    except Exception as db_err:
        logger.error(f"Database persistence failed, cleaning up stored file '{storage_key}': {db_err}")
        await storage.delete(storage_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database transaction failed during upload registration.",
        ) from db_err

    return UploadResponse(
        id=upload.id,
        project_id=upload.project_id,
        filename=upload.filename,
        file_size_bytes=upload.file_size_bytes,
        mime_type=upload.mime_type,
        file_hash=upload.file_hash,
        row_count=upload.row_count,
        column_count=upload.column_count,
        columns=metadata.columns,
        sheet_names=metadata.sheet_names,
        detected_encoding=metadata.detected_encoding,
        warnings=metadata.warnings,
        storage_path=upload.storage_path,
        created_at=upload.created_at,
    )
