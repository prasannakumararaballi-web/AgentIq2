"""Automated verification of Alembic Migration 002 backward compatibility and rollback."""

import os
import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config


def test_migration_002_upgrade_preserve_downgrade_cycle():
    """Verify Migration 002:

    1. Upgrade from 001 to 002.
    2. Preserve existing upload records intact.
    3. Verify new columns (file_hash, metadata).
    4. Downgrade to 001.
    5. Upgrade again successfully.
    """
    temp_dir = tempfile.mkdtemp(prefix="agentiq_test_migration_")
    db_path = Path(temp_dir) / "migration_test.db"
    db_url = f"sqlite:///{db_path.as_posix()}"

    alembic_ini_path = Path(__file__).resolve().parent.parent / "alembic.ini"
    cfg = Config(str(alembic_ini_path))
    cfg.set_main_option("sqlalchemy.url", db_url)

    # Use environment override recognized by env.py
    os.environ["DIRECT_DATABASE_URL"] = db_url

    try:
        # Step 1: Upgrade to 001_initial_schema
        command.upgrade(cfg, "001_initial_schema")

        # Step 2: Seed data under 001 schema (before file_hash and metadata existed)
        ws_id = str(uuid4())
        user_id = str(uuid4())
        proj_id = str(uuid4())
        upload_id = str(uuid4())

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO workspaces (id, name, slug, created_at, updated_at) VALUES (?, ?, ?, datetime('now'), datetime('now'))",
            (ws_id, "Migration Workspace", "mig-ws"),
        )
        cursor.execute(
            "INSERT INTO users (id, email, created_at, updated_at) VALUES (?, ?, datetime('now'), datetime('now'))",
            (user_id, "mig_user@example.com"),
        )
        cursor.execute(
            "INSERT INTO projects (id, workspace_id, name, created_at, updated_at) VALUES (?, ?, ?, datetime('now'), datetime('now'))",
            (proj_id, ws_id, "Migration Project"),
        )
        cursor.execute(
            """INSERT INTO uploads (id, project_id, workspace_id, filename, file_size_bytes, mime_type, storage_path, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (upload_id, proj_id, ws_id, "legacy_file.csv", 4096, "text/csv", "storage/raw/legacy_file.csv"),
        )
        conn.commit()

        # Step 3: Upgrade to 002_add_upload_hash_and_metadata
        command.upgrade(cfg, "002_add_upload_hash_and_metadata")

        # Step 4: Verify existing record was preserved intact and new columns exist with NULL values
        cursor.execute("SELECT id, filename, file_size_bytes, storage_path, file_hash, metadata FROM uploads WHERE id = ?", (upload_id,))
        row = cursor.fetchone()
        assert row is not None, "Pre-existing upload record was dropped or lost during migration!"
        assert row[0] == upload_id
        assert row[1] == "legacy_file.csv"
        assert row[2] == 4096
        assert row[3] == "storage/raw/legacy_file.csv"
        assert row[4] is None, "Expected file_hash to be NULL for backward-compatibility"
        assert row[5] is None, "Expected metadata to be NULL for backward-compatibility"

        # Step 5: Test updating row with new columns
        test_hash = "a" * 64
        test_meta = '{"columns": ["colA", "colB"]}'
        cursor.execute("UPDATE uploads SET file_hash = ?, metadata = ? WHERE id = ?", (test_hash, test_meta, upload_id))
        conn.commit()

        cursor.execute("SELECT file_hash, metadata FROM uploads WHERE id = ?", (upload_id,))
        updated_row = cursor.fetchone()
        assert updated_row[0] == test_hash
        assert updated_row[1] == test_meta

        # Step 6: Downgrade back to 001_initial_schema
        conn.close()
        command.downgrade(cfg, "001_initial_schema")

        # Verify columns removed and row preserved
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, storage_path FROM uploads WHERE id = ?", (upload_id,))
        downgraded_row = cursor.fetchone()
        assert downgraded_row is not None
        assert downgraded_row[0] == upload_id
        assert downgraded_row[1] == "legacy_file.csv"

        # Verify file_hash column no longer exists
        with pytest.raises(sqlite3.OperationalError):
            cursor.execute("SELECT file_hash FROM uploads")

        conn.close()

        # Step 7: Re-upgrade to 002_add_upload_hash_and_metadata successfully
        command.upgrade(cfg, "002_add_upload_hash_and_metadata")

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, file_hash, metadata FROM uploads WHERE id = ?", (upload_id,))
        reupgraded_row = cursor.fetchone()
        assert reupgraded_row is not None
        assert reupgraded_row[0] == upload_id
        conn.close()

    finally:
        os.environ.pop("DIRECT_DATABASE_URL", None)
        try:
            db_path.unlink(missing_ok=True)
            Path(temp_dir).rmdir()
        except Exception:
            pass
