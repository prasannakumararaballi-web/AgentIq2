"""Tenant-scoped secure download streaming endpoints."""

import io
import logging
from pathlib import Path
import re
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentiq_core.db.session import get_db_session
from agentiq_core.models.audit_log import AuditLog
from agentiq_core.models.workspace import WorkspaceMember
from agentiq_core.schemas.errors import ErrorResponse
from agentiq_core.storage.local import LocalStorageService
from apps.api.security.jwt_validator import AuthenticationError, get_jwt_validator

logger = logging.getLogger("agentiq.downloads")
router = APIRouter(prefix="/downloads", tags=["Downloads"])

SAFE_FILENAME_REGEX = re.compile(r"^([0-9a-fA-F-]{36})\.(csv|excel|xlsx|parquet)$")


@router.get(
    "/{filename}",
    status_code=status.HTTP_200_OK,
    summary="Download Cleaned Dataset Export",
    description="Stream a generated cleaned dataset export with strict tenant authorization and traversal protection.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid download filename format"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid authentication"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "User does not have access to this workspace"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Export not found in active workspace"},
    },
)
async def download_export_file(
    filename: str,
    token: Optional[str] = Query(None, description="Optional JWT query param for direct browser download links"),
    workspace_id_param: Optional[str] = Query(None, alias="workspace_id", description="Optional workspace ID query param"),
    authorization: Optional[str] = Header(None, description="Bearer JWT header"),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID", description="Workspace ID header"),
    db: AsyncSession = Depends(get_db_session),
):
    # 1. Path traversal & filename safety check
    match = SAFE_FILENAME_REGEX.match(filename)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename format. Expected '<uuid>.<format>'.",
        )

    export_id_str = match.group(1)
    file_format = match.group(2).lower()
    if file_format == "excel":
        file_format = "xlsx"

    # 2. Extract JWT token and Workspace ID from headers or query parameters
    jwt_token = None
    if authorization and authorization.startswith("Bearer "):
        jwt_token = authorization.split(" ", 1)[1].strip()
    elif token:
        jwt_token = token.strip()

    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    active_ws_str = x_workspace_id or workspace_id_param
    if not active_ws_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing target workspace identifier (header 'X-Workspace-ID' or query param 'workspace_id').",
        )

    try:
        target_ws_id = UUID(str(active_ws_str))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workspace ID format: '{active_ws_str}'.",
        )

    # 3. Cryptographically verify JWT token
    validator = get_jwt_validator()
    try:
        claims = await validator.verify_token(jwt_token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = UUID(str(claims["sub"]))

    # 4. Verify tenant membership & RBAC
    membership_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == target_ws_id,
        WorkspaceMember.user_id == user_id,
    )
    membership = (await db.execute(membership_stmt)).scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User does not have access to workspace '{target_ws_id}'.",
        )

    # 5. Verify export belongs strictly to this workspace (IDOR prevention)
    audit_stmt = select(AuditLog).where(
        AuditLog.workspace_id == target_ws_id,
        AuditLog.action == "export.created",
    )
    audit_logs = (await db.execute(audit_stmt)).scalars().all()
    matching_log = None
    for log in audit_logs:
        if log.details and log.details.get("export_id") == export_id_str:
            matching_log = log
            break

    if not matching_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export '{filename}' not found in active workspace.",
        )

    storage_key = matching_log.details.get("storage_key")
    if not storage_key:
        storage_key = f"exports/{target_ws_id}/{matching_log.run_id}/{export_id_str}.{file_format}"

    # 6. Read file from storage
    storage = LocalStorageService()
    try:
        resolved_path = storage._resolve_path(storage_key)
        if not resolved_path.is_file():
            # Check alternative extensions (e.g. .excel vs .xlsx)
            alt_key = f"exports/{target_ws_id}/{matching_log.run_id}/{export_id_str}.xlsx"
            resolved_path = storage._resolve_path(alt_key)
            if not resolved_path.is_file():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Exported file artifact is missing or has expired from storage.",
                )

        file_bytes = resolved_path.read_bytes()
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        logger.error(f"Error accessing export file '{storage_key}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read export artifact from storage.",
        )

    # 7. Determine content type and download disposition
    if file_format == "csv":
        media_type = "text/csv; charset=utf-8"
        download_name = f"cleaned_dataset_{export_id_str[:8]}.csv"
    elif file_format in ("xlsx", "excel"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        download_name = f"cleaned_dataset_{export_id_str[:8]}.xlsx"
    elif file_format == "parquet":
        media_type = "application/octet-stream"
        download_name = f"cleaned_dataset_{export_id_str[:8]}.parquet"
    else:
        media_type = "application/octet-stream"
        download_name = f"cleaned_dataset_{export_id_str[:8]}.{file_format}"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"',
            "Content-Length": str(len(file_bytes)),
        },
    )
