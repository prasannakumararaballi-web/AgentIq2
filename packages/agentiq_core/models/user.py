"""User model mapping to Supabase Auth identity."""

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID
from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentiq_core.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from agentiq_core.models.workspace import WorkspaceMember


class User(Base, TimestampMixin):
    """Application user record synchronizing identity from Supabase Auth.

    Does not store credentials; uses Supabase Auth as the authoritative IdP.
    """

    __tablename__ = "users"

    # Matches Supabase Auth user UUID (sub)
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )

    # Relationships
    workspace_memberships: Mapped[List["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

