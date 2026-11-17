"""Upload model tracking raw preserved dataset files."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import BigInteger, ForeignKey, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentiq_core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from agentiq_core.models.project import Project
    from agentiq_core.models.run import Run


class Upload(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Metadata record of an uploaded dataset preserved in raw storage."""

    __tablename__ = "uploads"

    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    file_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    row_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    column_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="uploads",
    )
    runs: Mapped[List["Run"]] = relationship(
        "Run",
        back_populates="upload",
        cascade="all, delete-orphan",
    )
