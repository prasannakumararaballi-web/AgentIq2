"""Project model scoped within a workspace."""

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentiq_core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from agentiq_core.models.workspace import Workspace
    from agentiq_core.models.upload import Upload
    from agentiq_core.models.run import Run


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Logical dataset project scoped to a specific tenant workspace."""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_project_name_workspace"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="projects",
    )
    uploads: Mapped[List["Upload"]] = relationship(
        "Upload",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    runs: Mapped[List["Run"]] = relationship(
        "Run",
        back_populates="project",
        cascade="all, delete-orphan",
    )

