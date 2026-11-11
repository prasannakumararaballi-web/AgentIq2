"""Dataset upload endpoints supporting multipart/form-data."""

import os
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.errors import ErrorResponse
from agentiq_core.schemas.upload import UploadResponse
from apps.api.dependencies import RequireWorkspacePermission

router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED_EXTENSIONS = {".csv", ".parquet", ".xlsx", ".json"}
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Dataset File",
    description="Upload raw dataset file via multipart/form-data with file validation and original preservation.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid file type or format"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_413_CONTENT_TOO_LARGE: {"model": ErrorResponse, "description": "File exceeds allowed size limit"},
    },
)
async def upload_file(
    file: UploadFile = File(..., description="Raw dataset file (.csv, .parquet, .xlsx, .json)"),
    project_id: UUID = Form(..., description="Target project ID"),
    membership=Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer"])),
) -> UploadResponse:
    # 1. Filename & Extension Validation
    filename = file.filename or "unknown_upload"
    _, ext = os.path.splitext(filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # 2. File size check
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File size exceeds maximum allowable limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
        )

    # 3. Preserve original file
    upload_id = uuid4()
    storage_path = f"storage/raw/{project_id}/{upload_id}_{filename}"

    return UploadResponse(
        id=upload_id,
        project_id=project_id,
        filename=filename,
        file_size_bytes=file_size,
        mime_type=file.content_type or "application/octet-stream",
        row_count=None,
        column_count=None,
        storage_path=storage_path,
        created_at=utc_now(),
    )
