"""Run model representing dataset profiling and anomaly detection runs."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentiq_core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from agentiq_core.models.project import Project
    from agentiq_core.models.upload import Upload
    from agentiq_core.models.finding import Finding
    from agentiq_core.models.decision import Decision
    from agentiq_core.models.audit_log import AuditLog


class Run(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Execution lifecycle record for data profiling and cleaning."""

    __tablename__ = "runs"

    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    upload_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="queued",
        nullable=False,
        index=True,
    )  # queued, processing, completed, failed, cancelled
    stage: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # reading, detecting, grouping, explaining, summarizing
    stage_percent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_percent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    progress_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="runs",
    )
    upload: Mapped["Upload"] = relationship(
        "Upload",
        back_populates="runs",
    )
    findings: Mapped[List["Finding"]] = relationship(
        "Finding",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    decisions: Mapped[List["Decision"]] = relationship(
        "Decision",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="run",
        cascade="all, delete-orphan",
    )

