"""Remediation decision reversal endpoints with tenant isolation."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentiq_core.db.session import get_db_session
from agentiq_core.models.audit_log import AuditLog
from agentiq_core.models.decision import Decision
from agentiq_core.models.finding import Finding
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.decision import DecisionUndoResponse
from agentiq_core.schemas.errors import ErrorResponse
from apps.api.dependencies import RequireWorkspacePermission, WorkspaceContext

router = APIRouter(prefix="/decisions", tags=["Decisions"])


@router.post(
    "/{decision_id}/undo",
    response_model=DecisionUndoResponse,
    status_code=status.HTTP_200_OK,
    summary="Undo Remediation Decision",
    description="Revert a previously committed cleaning decision back to pending review.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Decision already undone"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Decision not found in active workspace"},
    },
)
async def undo_decision(
    decision_id: UUID,
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer"])),
    db: AsyncSession = Depends(get_db_session),
) -> DecisionUndoResponse:
    # 1. Verify decision belongs strictly to active tenant workspace (IDOR prevention)
    stmt = select(Decision).where(
        Decision.id == decision_id,
        Decision.workspace_id == context.workspace_id,
    )
    decision = (await db.execute(stmt)).scalar_one_or_none()
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision '{decision_id}' not found in active workspace.",
        )

    if decision.status == "undone":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Decision '{decision_id}' is already undone.",
        )

    # 2. Mark undone
    now = utc_now()
    decision.status = "undone"
    decision.undone_at = now

    # 3. Re-open finding
    finding_stmt = select(Finding).where(Finding.id == decision.finding_id)
    finding = (await db.execute(finding_stmt)).scalar_one_or_none()
    if finding:
        finding.is_resolved = False

    # 4. Immutable audit log
    audit_entry = AuditLog(
        id=UUID(int=decision.id.int ^ 1),
        workspace_id=context.workspace_id,
        run_id=decision.run_id,
        user_id=context.user_id,
        action="decision.undone",
        details={"decision_id": str(decision.id), "finding_id": str(decision.finding_id)},
        timestamp=now,
    )
    db.add(audit_entry)

    await db.flush()

    return DecisionUndoResponse(
        decision_id=decision.id,
        status="undone",
        undone_at=now,
        message=f"Decision {decision_id} was successfully reverted.",
    )
