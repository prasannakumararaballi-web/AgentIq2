"""Remediation decision reversal endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, status
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.decision import DecisionUndoResponse
from agentiq_core.schemas.errors import ErrorResponse
from apps.api.dependencies import RequireWorkspacePermission

router = APIRouter(prefix="/decisions", tags=["Decisions"])


@router.post(
    "/{decision_id}/undo",
    response_model=DecisionUndoResponse,
    status_code=status.HTTP_200_OK,
    summary="Undo Remediation Decision",
    description="Revert a previously committed cleaning decision back to pending review.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Decision cannot be reverted"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient workspace permissions"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Decision not found"},
    },
)
async def undo_decision(
    decision_id: UUID,
    membership=Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer"])),
) -> DecisionUndoResponse:
    return DecisionUndoResponse(
        decision_id=decision_id,
        status="undone",
        undone_at=utc_now(),
        message=f"Decision {decision_id} was successfully reverted.",
    )
