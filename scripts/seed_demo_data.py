"""Seed persistent local database with standard demonstration workspace, users, and projects."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import UUID

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "packages"))
sys.path.insert(0, str(BASE_DIR / "apps"))

from sqlalchemy import select
from agentiq_core.db.session import get_async_session_factory
from agentiq_core.models import (
    Project,
    User,
    Workspace,
    WorkspaceMember,
)

WORKSPACE_A_ID = UUID("00000000-0000-0000-0000-000000000001")
ADMIN_USER_ID = UUID("00000000-0000-0000-0000-000000000099")
REVIEWER_USER_ID = UUID("00000000-0000-0000-0000-000000000088")
VIEWER_USER_ID = UUID("00000000-0000-0000-0000-000000000077")
PROJECT_A_ID = UUID("11111111-1111-1111-1111-111111111111")


async def seed():
    factory = get_async_session_factory()
    async with factory() as session:
        # 1. Users
        users = [
            User(id=ADMIN_USER_ID, email="admin@example.com", full_name="Demo Administrator"),
            User(id=REVIEWER_USER_ID, email="reviewer@example.com", full_name="Demo Reviewer"),
            User(id=VIEWER_USER_ID, email="viewer@example.com", full_name="Demo Viewer"),
        ]
        for u in users:
            existing = (await session.execute(select(User).where(User.id == u.id))).scalar_one_or_none()
            if not existing:
                session.add(u)

        # 2. Workspace
        existing_ws = (await session.execute(select(Workspace).where(Workspace.id == WORKSPACE_A_ID))).scalar_one_or_none()
        if not existing_ws:
            ws = Workspace(
                id=WORKSPACE_A_ID,
                name="Demo Workspace",
                slug="demo-workspace",
            )
            session.add(ws)

        await session.flush()

        # 3. Memberships
        memberships = [
            WorkspaceMember(workspace_id=WORKSPACE_A_ID, user_id=ADMIN_USER_ID, role="admin"),
            WorkspaceMember(workspace_id=WORKSPACE_A_ID, user_id=REVIEWER_USER_ID, role="reviewer"),
            WorkspaceMember(workspace_id=WORKSPACE_A_ID, user_id=VIEWER_USER_ID, role="viewer"),
        ]
        for m in memberships:
            existing_m = (await session.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == m.workspace_id,
                    WorkspaceMember.user_id == m.user_id,
                )
            )).scalar_one_or_none()
            if not existing_m:
                session.add(m)

        # 4. Project
        existing_proj = (await session.execute(select(Project).where(Project.id == PROJECT_A_ID))).scalar_one_or_none()
        if not existing_proj:
            proj = Project(
                id=PROJECT_A_ID,
                workspace_id=WORKSPACE_A_ID,
                name="Customer Intelligence Project",
                description="Seeded project for 1,000-row stage demonstration dataset",
            )
            session.add(proj)

        await session.commit()
        print("Database successfully seeded with demo workspace, users, and project.")


if __name__ == "__main__":
    asyncio.run(seed())
