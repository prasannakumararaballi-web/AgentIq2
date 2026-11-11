"""Finding remediation decision endpoints."""

from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, status
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.decision import FindingDecisionCreate, FindingDecisionResponse
from agentiq_core.schemas.errors import ErrorResponse
from apps.api.dependencies import (
    AuthenticatedUser,
    RequireWorkspacePermission,
    get_current_user,
)

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
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Finding not found"},
    },
)
async def submit_finding_decision(
    finding_id: UUID,
    payload: FindingDecisionCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    membership=Depends(RequireWorkspacePermission(allowed_roles=["admin", "reviewer"])),
) -> FindingDecisionResponse:
    decision_id = uuid4()
    return FindingDecisionResponse(
        id=decision_id,
        finding_id=finding_id,
        run_id=UUID("44444444-4444-4444-4444-444444444444"),
        user_id=current_user.id,
        action_type=payload.action_type,
        parameters=payload.custom_parameters,
        status="applied",
        decided_at=utc_now(),
    )

