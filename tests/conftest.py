"""Pytest test configuration and database fixtures for AgentIQ v2."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncGenerator, Generator
from uuid import UUID
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from agentiq_core.db.session import get_db_session
from agentiq_core.models import (
    AuditLog,
    Base,
    Decision,
    Finding,
    Project,
    Run,
    Upload,
    User,
    Workspace,
    WorkspaceMember,
)
from apps.api.main import app
from apps.api.security.jwt_validator import SupabaseJWTValidator, set_jwt_validator

TEST_JWT_SECRET = "test-secret-key-for-agentiq-pytest-environment-at-least-32-chars"

# Well-known seeded test identifiers
WORKSPACE_A_ID = UUID("00000000-0000-0000-0000-000000000001")
WORKSPACE_B_ID = UUID("00000000-0000-0000-0000-000000000002")

ADMIN_USER_ID = UUID("00000000-0000-0000-0000-000000000099")
REVIEWER_USER_ID = UUID("00000000-0000-0000-0000-000000000088")
VIEWER_USER_ID = UUID("00000000-0000-0000-0000-000000000077")
OUTSIDER_USER_ID = UUID("00000000-0000-0000-0000-000000000066")

PROJECT_A_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_B_ID = UUID("99999999-9999-9999-9999-999999999999")

UPLOAD_A_ID = UUID("22222222-2222-2222-2222-222222222222")
RUN_A_ID = UUID("44444444-4444-4444-4444-444444444444")
FINDING_A_ID = UUID("33333333-3333-3333-3333-333333333333")
DECISION_A_ID = UUID("55555555-5555-5555-5555-555555555555")


def make_jwt(
    user_id: UUID,
    email: str = "test@example.com",
    role: str = "authenticated",
    exp_seconds: int = 3600,
    secret: str = TEST_JWT_SECRET,
    issuer: str | None = None,
    audience: str | None = "authenticated",
) -> str:
    """Generate cryptographically signed test JWT."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "aud": audience,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=exp_seconds)).timestamp()),
    }
    if issuer:
        payload["iss"] = issuer
    return jwt.encode(payload, secret, algorithm="HS256")


# Shared in-memory test database engine
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    echo=False,
)
TestSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_security():
    """Configure real cryptographic JWT validator with known test secret."""
    validator = SupabaseJWTValidator(
        jwt_secret=TEST_JWT_SECRET,
        audience="authenticated",
    )
    set_jwt_validator(validator)


@pytest.fixture(autouse=True)
def seed_database() -> Generator[None, None, None]:
    """Create all schema tables and seed tenant workspaces before each test."""
    async def _setup() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with TestSessionFactory() as session:
            # 1. Users
            admin_u = User(id=ADMIN_USER_ID, email="admin@example.com", full_name="Admin User")
            reviewer_u = User(id=REVIEWER_USER_ID, email="reviewer@example.com", full_name="Reviewer User")
            viewer_u = User(id=VIEWER_USER_ID, email="viewer@example.com", full_name="Viewer User")
            outsider_u = User(id=OUTSIDER_USER_ID, email="outsider@example.com", full_name="Outsider User")
            session.add_all([admin_u, reviewer_u, viewer_u, outsider_u])

            # 2. Workspaces
            ws_a = Workspace(id=WORKSPACE_A_ID, name="Workspace A", slug="workspace-a")
            ws_b = Workspace(id=WORKSPACE_B_ID, name="Workspace B", slug="workspace-b")
            session.add_all([ws_a, ws_b])

            # 3. Workspace Memberships
            m1 = WorkspaceMember(workspace_id=WORKSPACE_A_ID, user_id=ADMIN_USER_ID, role="admin")
            m2 = WorkspaceMember(workspace_id=WORKSPACE_A_ID, user_id=REVIEWER_USER_ID, role="reviewer")
            m3 = WorkspaceMember(workspace_id=WORKSPACE_A_ID, user_id=VIEWER_USER_ID, role="viewer")
            m4 = WorkspaceMember(workspace_id=WORKSPACE_B_ID, user_id=OUTSIDER_USER_ID, role="admin")
            session.add_all([m1, m2, m3, m4])

            # 4. Projects (Workspace A and Workspace B)
            proj_a = Project(
                id=PROJECT_A_ID,
                workspace_id=WORKSPACE_A_ID,
                name="Project A",
                description="Workspace A dataset project",
            )
            proj_b = Project(
                id=PROJECT_B_ID,
                workspace_id=WORKSPACE_B_ID,
                name="Project B (Secret)",
                description="Workspace B confidential project",
            )
            session.add_all([proj_a, proj_b])

            # 5. Uploads
            upload_a = Upload(
                id=UPLOAD_A_ID,
                project_id=PROJECT_A_ID,
                workspace_id=WORKSPACE_A_ID,
                filename="customers.csv",
                file_size_bytes=1024,
                mime_type="text/csv",
                storage_path="storage/raw/customers.csv",
            )
            session.add(upload_a)

            # 6. Runs
            run_a = Run(
                id=RUN_A_ID,
                project_id=PROJECT_A_ID,
                upload_id=UPLOAD_A_ID,
                workspace_id=WORKSPACE_A_ID,
                status="completed",
                stage="summarizing",
                summary={"total_rows": 100, "total_columns": 5, "total_findings": 2, "estimated_quality_score": 98.0},
            )
            session.add(run_a)

            # 7. Findings
            finding_a = Finding(
                id=FINDING_A_ID,
                run_id=RUN_A_ID,
                workspace_id=WORKSPACE_A_ID,
                category="missing_value",
                severity="medium",
                description="Missing email in row 5",
                column_name="email",
                row_index=5,
                is_resolved=False,
            )
            session.add(finding_a)

            # 8. Decisions
            decision_a = Decision(
                id=DECISION_A_ID,
                finding_id=FINDING_A_ID,
                run_id=RUN_A_ID,
                workspace_id=WORKSPACE_A_ID,
                user_id=ADMIN_USER_ID,
                action_type="impute",
                parameters={"value": "default@example.com"},
                status="applied",
            )
            session.add(decision_a)

            # 9. Audit Log
            audit_a = AuditLog(
                id=UUID("77777777-7777-7777-7777-777777777777"),
                workspace_id=WORKSPACE_A_ID,
                run_id=RUN_A_ID,
                user_id=ADMIN_USER_ID,
                action="run.created",
                details={"status": "completed"},
            )
            session.add(audit_a)

            await session.commit()

    async def _teardown() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(_setup())
    yield
    asyncio.run(_teardown())


@pytest.fixture
def db_session_override() -> Generator[None, None, None]:
    """Dependency override connecting FastAPI endpoints to the seeded in-memory test database."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionFactory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db
    yield
    app.dependency_overrides.pop(get_db_session, None)


@pytest.fixture
def client(db_session_override) -> Generator[TestClient, None, None]:
    """FastAPI TestClient wired with in-memory database and security overrides."""
    yield TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Valid authentication and workspace headers for Admin User in Workspace A."""
    token = make_jwt(ADMIN_USER_ID, email="admin@example.com")
    return {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(WORKSPACE_A_ID),
    }


@pytest.fixture
def reviewer_headers() -> dict[str, str]:
    """Valid headers for Reviewer User in Workspace A."""
    token = make_jwt(REVIEWER_USER_ID, email="reviewer@example.com")
    return {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(WORKSPACE_A_ID),
    }


@pytest.fixture
def viewer_headers() -> dict[str, str]:
    """Valid headers for Viewer User in Workspace A."""
    token = make_jwt(VIEWER_USER_ID, email="viewer@example.com")
    return {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(WORKSPACE_A_ID),
    }


@pytest.fixture
def outsider_headers() -> dict[str, str]:
    """Valid headers for Outsider User belonging only to Workspace B."""
    token = make_jwt(OUTSIDER_USER_ID, email="outsider@example.com")
    return {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(WORKSPACE_B_ID),
    }