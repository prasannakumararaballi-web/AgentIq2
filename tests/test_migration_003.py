"""Automated verification of Alembic Migration 003 upgrade, preservation, and rollback cycle."""

import os
import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config


def test_migration_003_upgrade_preserve_downgrade_cycle():
    """Verify Migration 003:
    1. Upgrade from 002 to 003.
    2. Preserve existing findings records intact with defaults.
    3. Verify new columns (issue_title, affected_row_count, risk_tier, etc.).
    4. Downgrade back to 002.
    5. Upgrade again successfully.
    """
    temp_dir = tempfile.mkdtemp(prefix="agentiq_test_migration_003_")
    db_path = Path(temp_dir) / "migration_test_003.db"
    db_url = f"sqlite:///{db_path.as_posix()}"

    alembic_ini_path = Path(__file__).resolve().parent.parent / "alembic.ini"
    cfg = Config(str(alembic_ini_path))
    cfg.set_main_option("sqlalchemy.url", db_url)
    os.environ["DIRECT_DATABASE_URL"] = db_url

    try:
        # Step 1: Upgrade to 002
        command.upgrade(cfg, "002_add_upload_hash_and_metadata")

        # Step 2: Seed data under 002 schema (before finding card fields existed)
        ws_id = str(uuid4())
        user_id = str(uuid4())
        proj_id = str(uuid4())
        upload_id = str(uuid4())
        run_id = str(uuid4())
        finding_id = str(uuid4())

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO workspaces (id, name, slug, created_at, updated_at) VALUES (?, ?, ?, datetime('now'), datetime('now'))",
            (ws_id, "WS 003", "ws-003"),
        )
        cursor.execute(
            "INSERT INTO users (id, email, created_at, updated_at) VALUES (?, ?, datetime('now'), datetime('now'))",
            (user_id, "user003@example.com"),
        )
        cursor.execute(
            "INSERT INTO projects (id, workspace_id, name, created_at, updated_at) VALUES (?, ?, ?, datetime('now'), datetime('now'))",
            (proj_id, ws_id, "Proj 003"),
        )
        cursor.execute(
            """INSERT INTO uploads (id, project_id, workspace_id, filename, file_size_bytes, mime_type, storage_path, file_hash, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (upload_id, proj_id, ws_id, "data.csv", 1024, "text/csv", "path/to/data.csv", "abc123hash"),
        )
        cursor.execute(
            """INSERT INTO runs (id, project_id, upload_id, workspace_id, status, stage_percent, total_percent, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'completed', 100, 100, datetime('now'), datetime('now'))""",
            (run_id, proj_id, upload_id, ws_id),
        )
        cursor.execute(
            """INSERT INTO findings (id, run_id, workspace_id, category, severity, description, is_resolved, created_at, updated_at)
               VALUES (?, ?, ?, 'missing_value', 'medium', 'Legacy finding before 003', 0, datetime('now'), datetime('now'))""",
            (finding_id, run_id, ws_id),
        )
        conn.commit()
        conn.close()

        # Step 3: Upgrade to 003_add_finding_card_fields
        command.upgrade(cfg, "003_add_finding_card_fields")

        # Step 4: Verify columns exist and legacy row has sensible defaults
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, description, affected_row_count, confidence, risk_tier, issue_title FROM findings WHERE id = '{finding_id}'")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == finding_id
        assert row[1] == "Legacy finding before 003"
        assert row[2] == 1  # Default affected_row_count
        assert row[3] == 1.0  # Default confidence
        assert row[4] == 1  # Default risk_tier
        assert row[5] is None  # Nullable issue_title

        # Step 5: Downgrade back to 002
        conn.close()
        command.downgrade(cfg, "002_add_upload_hash_and_metadata")

        # Verify columns removed and finding remains
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, description FROM findings WHERE id = '{finding_id}'")
        row_after_downgrade = cursor.fetchone()
        assert row_after_downgrade is not None
        assert row_after_downgrade[0] == finding_id

        # Verify card columns no longer exist
        cursor.execute("PRAGMA table_info(findings)")
        columns = [col[1] for col in cursor.fetchall()]
        assert "affected_row_count" not in columns
        assert "risk_tier" not in columns
        assert "issue_title" not in columns
        conn.close()

        # Step 6: Re-upgrade to 003 successfully
        command.upgrade(cfg, "003_add_finding_card_fields")

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
