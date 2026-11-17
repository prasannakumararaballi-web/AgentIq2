"""Comprehensive test suite for Phase 1: Storage, Hashing, Parser, and Upload API."""

import hashlib
import io
import os
import shutil
import tempfile
from pathlib import Path
from uuid import UUID, uuid4
import openpyxl
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from agentiq_core.storage import (
    DatasetMetadata,
    DatasetParseError,
    DatasetParser,
    EmptyDatasetError,
    LocalStorageService,
    StorageQuotaExceededError,
    deduplicate_headers,
)
from tests.conftest import (
    ADMIN_USER_ID,
    PROJECT_A_ID,
    PROJECT_B_ID,
    WORKSPACE_A_ID,
    WORKSPACE_B_ID,
)


# ==============================================================================
# 1. STORAGE SERVICE UNIT TESTS
# ==============================================================================

@pytest.fixture
def temp_storage():
    """Create isolated temporary directory for storage tests."""
    temp_dir = tempfile.mkdtemp(prefix="agentiq_test_storage_")
    service = LocalStorageService(base_path=temp_dir)
    yield service
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_storage_save_and_read_stream(temp_storage: LocalStorageService):
    key = "raw/ws-1/proj-1/test.csv"
    data = b"col1,col2\nval1,val2\nval3,val4\n"
    expected_hash = hashlib.sha256(data).hexdigest()

    async def stream_gen():
        yield data[:10]
        yield data[10:]

    saved_key, file_hash, size = await temp_storage.save_stream(key, stream_gen())

    assert saved_key == key
    assert file_hash == expected_hash
    assert size == len(data)
    assert await temp_storage.exists(key) is True

    # Read back and verify exact byte parity
    read_chunks = []
    async for chunk in temp_storage.read_stream(key):
        read_chunks.append(chunk)
    assert b"".join(read_chunks) == data

    # Verify synchronous reader
    with temp_storage.open_reader(key) as reader:
        assert reader.read() == data


@pytest.mark.asyncio
async def test_storage_enforces_size_limit_and_cleans_up(temp_storage: LocalStorageService):
    key = "raw/ws-1/proj-1/oversized.csv"
    limit = 50

    async def big_stream():
        yield b"A" * 30
        yield b"B" * 30  # Total 60 > 50

    with pytest.raises(StorageQuotaExceededError) as exc:
        await temp_storage.save_stream(key, big_stream(), max_size_bytes=limit)

    assert exc.value.max_bytes == limit
    assert exc.value.current_bytes == 60
    # Verify no file or partial file remained
    assert await temp_storage.exists(key) is False

    # Check parent directory has no .part file
    resolved_parent = temp_storage.base_dir / "raw" / "ws-1" / "proj-1"
    if resolved_parent.exists():
        part_files = list(resolved_parent.glob("*.part"))
        assert len(part_files) == 0


@pytest.mark.asyncio
async def test_storage_blocks_path_traversal(temp_storage: LocalStorageService):
    bad_key = "../../etc/passwd"
    with pytest.raises(ValueError, match="Path traversal attempt"):
        temp_storage._resolve_path(bad_key)


# ==============================================================================
# 2. DATASET PARSER UNIT TESTS
# ==============================================================================

def test_deduplicate_headers():
    raw = ["id", "email", "name", "email", "email", ""]
    clean, warnings = deduplicate_headers(raw)
    assert clean == ["id", "email", "name", "email_1", "email_2", "unnamed_5"]
    assert len(warnings) == 2
    assert "Duplicate header 'email'" in warnings[0]


def test_parser_csv_utf8_and_metadata():
    csv_bytes = b"id,name,score\n1,Alice,95.5\n2,Bob,88.0\n3,Charlie,72.3\n"
    stream = io.BytesIO(csv_bytes)
    meta = DatasetParser.parse_csv(stream)

    assert meta.row_count == 3
    assert meta.column_count == 3
    assert meta.columns == ["id", "name", "score"]
    assert meta.detected_encoding == "utf-8"
    assert len(meta.sample_preview) == 3


def test_parser_csv_utf8_bom():
    csv_bytes = b"\xef\xbb\xbfid,name\n1,Alice\n2,Bob\n"
    stream = io.BytesIO(csv_bytes)
    meta = DatasetParser.parse_csv(stream)

    assert meta.row_count == 2
    assert meta.columns == ["id", "name"]
    # Verify no hidden BOM character in first column name
    assert not meta.columns[0].startswith("\ufeff")
    assert "\ufeff" not in meta.columns[0]
    assert meta.columns[0] == "id"
    assert meta.original_columns[0] == "id"
    assert meta.detected_encoding == "utf-8-sig"


def test_parser_csv_latin1_fallback():
    # Character 'é' in Latin-1 is \xe9, invalid in strict UTF-8
    latin1_bytes = "id,name,city\n1,René,Montréal\n2,François,Québec\n".encode("latin-1")
    stream = io.BytesIO(latin1_bytes)
    meta = DatasetParser.parse_csv(stream)

    assert meta.row_count == 2
    assert meta.columns == ["id", "name", "city"]
    assert meta.detected_encoding in ("cp1252", "latin-1")
    assert meta.sample_preview[0]["name"] == "René"


def test_parser_empty_csv_raises_error():
    empty_stream = io.BytesIO(b"")
    with pytest.raises(EmptyDatasetError):
        DatasetParser.parse_csv(empty_stream)


def test_parser_excel_multisheet_read_only(tmp_path: Path):
    excel_path = tmp_path / "multisheet_test.xlsx"
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Customers"
    ws1.append(["customer_id", "email", "tier"])
    ws1.append(["c1", "c1@test.com", "gold"])
    ws1.append(["c2", "c2@test.com", "silver"])

    ws2 = wb.create_sheet(title="Orders")
    ws2.append(["order_id", "amount", "status"])
    ws2.append(["o1", 150.0, "paid"])
    ws2.append(["o2", 230.5, "shipped"])
    ws2.append(["o3", 50.0, "cancelled"])
    wb.save(excel_path)
    wb.close()

    # Parse first sheet (Customers)
    meta = DatasetParser.parse_excel(excel_path)
    assert meta.sheet_names == ["Customers", "Orders"]
    assert meta.active_sheet == "Customers"
    assert meta.row_count == 2
    assert meta.column_count == 3
    assert meta.columns == ["customer_id", "email", "tier"]

    # Parse second sheet (Orders)
    meta_orders = DatasetParser.parse_excel(excel_path, sheet_name="Orders")
    assert meta_orders.active_sheet == "Orders"
    assert meta_orders.row_count == 3
    assert meta_orders.columns == ["order_id", "amount", "status"]


# ==============================================================================
# 3. API UPLOAD ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_api_upload_csv_persists_file_and_hash(client: TestClient, auth_headers: dict[str, str]):
    csv_content = b"user_id,email,age\n1,alice@example.com,29\n2,bob@example.com,34\n"
    expected_hash = hashlib.sha256(csv_content).hexdigest()

    res = client.post(
        "/api/v1/uploads",
        headers={"Authorization": auth_headers["Authorization"], "X-Workspace-ID": auth_headers["X-Workspace-ID"]},
        data={"project_id": str(PROJECT_A_ID)},
        files={"file": ("users.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert res.status_code == 201
    data = res.json()
    assert data["filename"] == "users.csv"
    assert data["file_hash"] == expected_hash
    assert data["file_size_bytes"] == len(csv_content)
    assert data["row_count"] == 2
    assert data["column_count"] == 3
    assert data["columns"] == ["user_id", "email", "age"]
    assert data["detected_encoding"] == "utf-8"

    # Verify file actually exists on disk and its SHA-256 matches bit-for-bit
    storage_path = Path("./storage") / data["storage_path"]
    assert storage_path.is_file()
    assert hashlib.sha256(storage_path.read_bytes()).hexdigest() == expected_hash


def test_api_upload_empty_csv_returns_400_and_cleans_up(client: TestClient, auth_headers: dict[str, str]):
    res = client.post(
        "/api/v1/uploads",
        headers={"Authorization": auth_headers["Authorization"], "X-Workspace-ID": auth_headers["X-Workspace-ID"]},
        data={"project_id": str(PROJECT_A_ID)},
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )

    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "BAD_REQUEST"
    assert "empty" in data["error"]["message"].lower()


def test_api_upload_duplicate_headers_normalizes_with_warnings(client: TestClient, auth_headers: dict[str, str]):
    csv_content = b"tag,value,tag\nalpha,10,beta\n"
    res = client.post(
        "/api/v1/uploads",
        headers={"Authorization": auth_headers["Authorization"], "X-Workspace-ID": auth_headers["X-Workspace-ID"]},
        data={"project_id": str(PROJECT_A_ID)},
        files={"file": ("dup_headers.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert res.status_code == 201
    data = res.json()
    assert data["columns"] == ["tag", "value", "tag_1"]
    assert len(data["warnings"]) >= 1
    assert "Duplicate header 'tag'" in data["warnings"][0]


def test_api_upload_multisheet_excel(client: TestClient, auth_headers: dict[str, str], tmp_path: Path):
    excel_path = tmp_path / "test_api_sheets.xlsx"
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "SheetAlpha"
    ws1.append(["colA", "colB"])
    ws1.append([1, 2])
    ws2 = wb.create_sheet(title="SheetBeta")
    ws2.append(["x", "y", "z"])
    ws2.append([10, 20, 30])
    wb.save(excel_path)
    wb.close()

    with open(excel_path, "rb") as f:
        file_bytes = f.read()

    res = client.post(
        "/api/v1/uploads",
        headers={"Authorization": auth_headers["Authorization"], "X-Workspace-ID": auth_headers["X-Workspace-ID"]},
        data={"project_id": str(PROJECT_A_ID)},
        files={"file": ("sheets.xlsx", io.BytesIO(file_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert res.status_code == 201
    data = res.json()
    assert "SheetAlpha" in data["sheet_names"]
    assert "SheetBeta" in data["sheet_names"]
    assert data["row_count"] == 1
    assert data["column_count"] == 2


def test_api_upload_tenant_isolation_idor_prevention(client: TestClient, auth_headers: dict[str, str]):
    # User in Workspace A attempts to upload into PROJECT_B (belonging to Workspace B)
    csv_content = b"col1\nval1\n"
    res = client.post(
        "/api/v1/uploads",
        headers={"Authorization": auth_headers["Authorization"], "X-Workspace-ID": auth_headers["X-Workspace-ID"]},
        data={"project_id": str(PROJECT_B_ID)},
        files={"file": ("exploit.csv", io.BytesIO(csv_content), "text/csv")},
    )

    # Server scopes Project by context.workspace_id, returning 404
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "NOT_FOUND"
    assert "Project" in data["error"]["message"]


@pytest.mark.asyncio
async def test_storage_reusable_integrity_verification_and_cleaned_isolation(temp_storage: LocalStorageService):
    key = "raw/ws-1/proj-1/integrity_check.csv"
    data = b"colA,colB\n1,2\n3,4\n"
    expected_hash = hashlib.sha256(data).hexdigest()

    async def stream():
        yield data

    await temp_storage.save_stream(key, stream())

    # 1. Verification succeeds when hash matches
    assert await temp_storage.verify_integrity(key, expected_hash) is True

    # 2. Raises StorageIntegrityError when hash mismatch
    from agentiq_core.storage.base import StorageIntegrityError
    with pytest.raises(StorageIntegrityError):
        await temp_storage.verify_integrity(key, "wrong_hash_" + "0" * 53)

    # 3. Cleaned output storage key is strictly separated from raw inputs
    cleaned_key = temp_storage.build_cleaned_storage_key(
        workspace_id=UUID("00000000-0000-0000-0000-000000000001"),
        project_id=UUID("11111111-1111-1111-1111-111111111111"),
        run_id=UUID("22222222-2222-2222-2222-222222222222"),
        format="parquet",
    )
    assert cleaned_key.startswith("cleaned/")
    assert not cleaned_key.startswith("raw/")


def test_file_hash_unchanged_before_and_after_parsing(tmp_path: Path):
    """Verify that parsing the dataset leaves the source file's SHA-256 hash completely unchanged."""
    csv_file = tmp_path / "immutable_test.csv"
    content = b"user,score\nalice,100\nbob,90\ncharlie,85\n"
    csv_file.write_bytes(content)

    hash_before = hashlib.sha256(csv_file.read_bytes()).hexdigest()

    # Parse dataset with DatasetParser
    meta = DatasetParser.introspect_dataset(csv_file, "immutable_test.csv")
    assert meta.row_count == 3

    hash_after = hashlib.sha256(csv_file.read_bytes()).hexdigest()
    assert hash_before == hash_after, "Dataset parser mutated the raw source file!"


def test_api_upload_database_failure_cleans_up_stored_file(client: TestClient, auth_headers: dict[str, str], monkeypatch):
    """Verify that a database commit/flush failure after file write reliably deletes the stored file."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from agentiq_core.db.session import get_db_session

    csv_content = b"col1,col2\nval1,val2\n"

    # Monkeypatch session.flush to simulate a database failure during upload persistence
    original_get_db = client.app.dependency_overrides.get(get_db_session)

    async def failing_get_db():
        async for session in original_get_db():
            real_flush = session.flush
            flush_calls = 0

            async def selective_flush(*args, **kwargs):
                nonlocal flush_calls
                flush_calls += 1
                if flush_calls > 1:
                    raise RuntimeError("Simulated database failure during upload flush")
                return await real_flush(*args, **kwargs)

            session.flush = selective_flush
            yield session

    client.app.dependency_overrides[get_db_session] = failing_get_db

    try:
        res = client.post(
            "/api/v1/uploads",
            headers={"Authorization": auth_headers["Authorization"], "X-Workspace-ID": auth_headers["X-Workspace-ID"]},
            data={"project_id": str(PROJECT_A_ID)},
            files={"file": ("db_fail_test.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert res.status_code == 500
        assert "Database transaction failed" in res.json()["error"]["message"]

        # Verify no file named db_fail_test exists in storage/raw/
        raw_storage = Path("./storage/raw")
        if raw_storage.exists():
            matching_files = list(raw_storage.rglob("*db_fail_test.csv"))
            assert len(matching_files) == 0, f"Orphaned file remained after DB failure: {matching_files}"

    finally:
        client.app.dependency_overrides[get_db_session] = original_get_db


def test_api_upload_cross_workspace_tampering_header_returns_403(client: TestClient, auth_headers: dict[str, str]):
    """User in Workspace A attempts to pass Workspace B in X-Workspace-ID header."""
    csv_content = b"col1\nval1\n"
    res = client.post(
        "/api/v1/uploads",
        headers={"Authorization": auth_headers["Authorization"], "X-Workspace-ID": str(WORKSPACE_B_ID)},
        data={"project_id": str(PROJECT_A_ID)},
        files={"file": ("tamper.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert res.status_code == 403
    data = res.json()
    assert data["error"]["code"] == "FORBIDDEN"
    assert "does not have access to workspace" in data["error"]["message"]
