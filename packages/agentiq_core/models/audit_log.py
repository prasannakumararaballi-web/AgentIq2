"""AuditLog model for immutable activity tracking."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID
from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentiq_core.models.base import Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from agentiq_core.models.run import Run
    from agentiq_core.models.user import User


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """Immutable audit trail record for compliance and activity transparency."""

    __tablename__ = "audit_logs"

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[Optional[UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )

    # Relationships
    run: Mapped[Optional["Run"]] = relationship(
        "Run",
        back_populates="audit_logs",
    )
    user: Mapped["User"] = relationship(
        "User",
    )

