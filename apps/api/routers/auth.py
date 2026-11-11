"""Authentication and user identity endpoints."""

from fastapi import APIRouter, Depends, status
from agentiq_core.schemas.auth import UserResponse
from agentiq_core.schemas.errors import ErrorResponse
from apps.api.dependencies import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns authenticated user details and all authorized workspace memberships.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid Bearer token"},
    },
)
async def get_me(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> UserResponse:
    return current_user

