"""Finding model representing detected dataset anomalies."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentiq_core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from agentiq_core.models.run import Run
    from agentiq_core.models.decision import Decision


class Finding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Data quality violation or anomaly discovered during a profiling run."""

    __tablename__ = "findings"

    run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_index: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    column_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    affected_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    suggested_action: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    is_resolved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    # Card-level aggregation & risk tier extensions (Phase 2)
    issue_title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    affected_row_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )
    affected_row_indices: Mapped[Optional[List[int]]] = mapped_column(
        JSON,
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        server_default="1.0",
        nullable=False,
    )
    risk_tier: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
        index=True,
    )
    impact_estimate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0.0",
        nullable=False,
    )
    sample_before: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    sample_after: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    detection_rule: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # Relationships
    run: Mapped["Run"] = relationship(
        "Run",
        back_populates="findings",
    )
    decisions: Mapped[List["Decision"]] = relationship(
        "Decision",
        back_populates="finding",
        cascade="all, delete-orphan",
    )

