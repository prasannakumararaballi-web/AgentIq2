"""Base schema definitions and configuration."""

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class AgentIQBaseModel(BaseModel):
    """Base model for all AgentIQ schemas enforcing consistent serialization."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

