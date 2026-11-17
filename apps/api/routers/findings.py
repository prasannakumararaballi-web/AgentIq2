"""Finding remediation decision endpoints with tenant isolation."""

from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentiq_core.db.session import get_db_session
from agentiq_core.models.audit_log import AuditLog
from agentiq_core.models.decision import Decision
from agentiq_core.models.finding import Finding
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.decision import FindingDecisionCreate, FindingDecisionResponse
from agentiq_core.schemas.errors import ErrorResponse
from apps.api.dependencies import RequireWorkspacePermission, WorkspaceContext

router = APIRouter(prefix="/findings", tags=["Findings"])


@router.post(
    "/{finding_id}/decisions",
    response_model=FindingDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Remediation Decision",
    description="Commit a human reviewer decision (accept suggestion, specify custom rule, or ignore) for an anomaly finding.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid decision payload"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Finding not found in active workspace"},
    },
)
async def submit_finding_decision(
    finding_id: UUID,
    payload: FindingDecisionCreate,
    context: WorkspaceContext = Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer"])),
    db: AsyncSession = Depends(get_db_session),
) -> FindingDecisionResponse:
    # 1. Verify finding belongs strictly to active tenant workspace (IDOR prevention)
    stmt = select(Finding).where(
        Finding.id == finding_id,
        Finding.workspace_id == context.workspace_id,
    )
    finding = (await db.execute(stmt)).scalar_one_or_none()
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found in active workspace.",
        )

    # 2. Record decision
    decision = Decision(
        id=uuid4(),
        finding_id=finding.id,
        run_id=finding.run_id,
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        action_type=payload.action_type,
        parameters=payload.custom_parameters,
        notes=payload.notes,
        status="applied",
        decided_at=utc_now(),
    )
    db.add(decision)

    # 3. Mark finding resolved
    finding.is_resolved = True

    # 4. Immutable audit trail
    audit_entry = AuditLog(
        id=uuid4(),
        workspace_id=context.workspace_id,
        run_id=finding.run_id,
        user_id=context.user_id,
        action="finding.decided",
        details={
            "finding_id": str(finding.id),
            "decision_id": str(decision.id),
            "action_type": payload.action_type,
        },
        timestamp=utc_now(),
    )
    db.add(audit_entry)

    await db.flush()

    return FindingDecisionResponse(
        id=decision.id,
        finding_id=decision.finding_id,
        run_id=decision.run_id,
        user_id=decision.user_id,
        action_type=decision.action_type,
        parameters=decision.parameters,
        status=decision.status,
        decided_at=decision.decided_at,
    )
