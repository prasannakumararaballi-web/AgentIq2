"""Workspace and WorkspaceMember models for tenant isolation and RBAC."""

from typing import TYPE_CHECKING, List
from uuid import UUID
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentiq_core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from agentiq_core.models.user import User
    from agentiq_core.models.project import Project


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tenant boundary for data quality isolation."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(140),
        unique=True,
        index=True,
        nullable=False,
    )

    # Relationships
    members: Mapped[List["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )


class WorkspaceMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Associates a user with a workspace and defines their RBAC permission level."""

    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
        Index("ix_workspace_members_workspace_user", "workspace_id", "user_id"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="viewer",
    )  # admin, reviewer, viewer

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="workspace_memberships",
    )

