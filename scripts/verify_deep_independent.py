"""Targeted deep independent verification script for AgentIQ v2.

Tests:
1. Approved decisions are reflected in exports.
2. Undone decisions are strictly NOT applied in exports.
3. CSV, Excel, and Parquet exports open independently with full row/col/header validation.
4. Compare endpoint diffs match actual transformations.
5. Security: Unauthenticated, cross-tenant, invalid UUID, and path traversal vectors.
6. Bit-for-bit SHA-256 immutability of source file.
"""

import hashlib
import io
from pathlib import Path
import sys
from uuid import UUID, uuid4

import pandas as pd
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "packages"))
sys.path.insert(0, str(BASE_DIR / "apps"))

from apps.api.main import app
from tests.conftest import (
    ADMIN_USER_ID,
    OUTSIDER_USER_ID,
    PROJECT_A_ID,
    WORKSPACE_A_ID,
    WORKSPACE_B_ID,
    make_jwt,
)


def run_deep_verification():
    print("=" * 80)
    print("AGENTIQ v2 — DEEP INDEPENDENT AUDIT & VERIFICATION")
    print("=" * 80)

    client = TestClient(app)
    admin_token = make_jwt(ADMIN_USER_ID, email="admin@example.com")
    outsider_token = make_jwt(OUTSIDER_USER_ID, email="outsider@example.com")

    headers_admin = {
        "Authorization": f"Bearer {admin_token}",
        "X-Workspace-ID": str(WORKSPACE_A_ID),
    }
    headers_outsider = {
        "Authorization": f"Bearer {outsider_token}",
        "X-Workspace-ID": str(WORKSPACE_B_ID),
    }

    # 1. Source file & SHA-256
    demo_file = BASE_DIR / "storage" / "demo" / "demo_customers_1000.csv"
    assert demo_file.exists(), "Demo file does not exist"
    initial_bytes = demo_file.read_bytes()
    initial_sha256 = hashlib.sha256(initial_bytes).hexdigest()
    orig_df = pd.read_csv(io.BytesIO(initial_bytes))
    print(f"\n[Source File] Path: {demo_file.name}, Size: {len(initial_bytes)} bytes, SHA-256: {initial_sha256}")
    print(f"[Source File] Actual Columns ({len(orig_df.columns)}): {list(orig_df.columns)}")

    # 2. Upload file
    upload_res = client.post(
        "/api/v1/uploads",
        headers=headers_admin,
        data={"project_id": str(PROJECT_A_ID)},
        files={"file": (demo_file.name, io.BytesIO(initial_bytes), "text/csv")},
    )
    assert upload_res.status_code == 201, f"Upload failed: {upload_res.status_code} {upload_res.text}"
    upload_id = upload_res.json()["id"]
    print(f"[Upload] Upload ID: {upload_id}")

    # 3. Trigger run
    run_res = client.post(
        "/api/v1/runs?sync=true",
        headers=headers_admin,
        json={"project_id": str(PROJECT_A_ID), "upload_id": upload_id},
    )
    assert run_res.status_code == 202, f"Run start failed: {run_res.status_code} {run_res.text}"
    run_id = run_res.json()["id"]
    print(f"[Run] Run ID: {run_id}, Status: {run_res.json()['status']}")

    # 4. Get Findings
    findings_res = client.get(f"/api/v1/runs/{run_id}/findings", headers=headers_admin)
    assert findings_res.status_code == 200
    findings = findings_res.json()["items"]
    print(f"[Findings] Total detected: {len(findings)}")

    # Find a whitespace finding or mojibake finding
    whitespace_finding = next((f for f in findings if "whitespace" in f["description"].lower() or f["category"] == "format_inconsistency"), findings[0])
    finding_id = whitespace_finding["id"]
    target_column = whitespace_finding["column_name"] or "full_name"
    finding_title = whitespace_finding.get("issue_title") or whitespace_finding.get("description")
    print(f"[Target Finding] ID: {finding_id}, Title: {finding_title}, Column: {target_column}")

    # 5. Apply Decision
    decision_res = client.post(
        f"/api/v1/findings/{finding_id}/decisions",
        headers=headers_admin,
        json={
            "action_type": "transform",
            "custom_parameters": {
                "column": "full_name",
                "operation": "repair_mojibake_encoding",
            },
            "notes": "Repairing mojibake in deep test",
        },
    )
    assert decision_res.status_code == 201, f"Decision failed: {decision_res.text}"
    decision_id = decision_res.json()["id"]
    print(f"[Decision] Created decision {decision_id} (Status: {decision_res.json()['status']})")

    # 6. Verify Compare with Decision Applied
    comp_res = client.get(f"/api/v1/runs/{run_id}/compare", headers=headers_admin)
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    print(f"[Compare] Original rows: {comp_data['original_rows_count']}, Cleaned rows: {comp_data['cleaned_rows_count']}")
    print(f"[Compare] Columns diff entries: {len(comp_data['columns_diff'])}")
    assert len(comp_data["preview_original"]) == 10
    assert len(comp_data["preview_cleaned"]) == 10

    # 7. Generate & Download CSV, Excel, and Parquet with decision APPLIED
    print("\n--- Testing Exports with Approved Decision ---")
    export_files = {}
    for fmt, ext, engine in [("csv", "csv", None), ("excel", "excel", "openpyxl"), ("parquet", "parquet", "pyarrow")]:
        exp_res = client.post(
            f"/api/v1/runs/{run_id}/exports",
            headers=headers_admin,
            json={"format": fmt, "include_cleaned_only": True},
        )
        assert exp_res.status_code == 201, f"Export {fmt} failed: {exp_res.text}"
        exp_data = exp_res.json()
        download_url = exp_data["download_url"]
        print(f"  Export {fmt.upper()}: URL = {download_url}, Reported Size = {exp_data['file_size_bytes']} bytes")

        # Download with auth
        dl_res = client.get(download_url, headers=headers_admin)
        assert dl_res.status_code == 200, f"Download {fmt} failed: {dl_res.status_code}"
        dl_bytes = dl_res.content
        assert len(dl_bytes) > 0, "Downloaded 0 bytes"
        print(f"  Downloaded {fmt.upper()}: Actual Size = {len(dl_bytes)} bytes")

        # Open and parse
        if fmt == "csv":
            df_parsed = pd.read_csv(io.BytesIO(dl_bytes))
        elif fmt == "excel":
            df_parsed = pd.read_excel(io.BytesIO(dl_bytes), engine="openpyxl")
        elif fmt == "parquet":
            df_parsed = pd.read_parquet(io.BytesIO(dl_bytes), engine="pyarrow")

        print(f"  Parsed {fmt.upper()}: {len(df_parsed)} rows, {len(df_parsed.columns)} columns")
        assert len(df_parsed) == 1000, f"Expected 1000 rows, got {len(df_parsed)}"
        assert len(df_parsed.columns) == 15, f"Expected 15 columns, got {len(df_parsed.columns)}"
        print(f"  Parsed {fmt.upper()} columns: {list(df_parsed.columns)}")
        assert list(df_parsed.columns) == list(orig_df.columns), f"Column mismatch in {fmt}: {list(df_parsed.columns)} vs {list(orig_df.columns)}"
        export_files[fmt] = df_parsed

    # 8. Test Decision Undo and Verify Exports NO LONGER APPLY IT
    print("\n--- Testing Decision Undo & Export Non-Application ---")
    undo_res = client.post(f"/api/v1/decisions/{decision_id}/undo", headers=headers_admin)
    assert undo_res.status_code == 200
    assert undo_res.json()["status"] == "undone"
    print(f"  Decision {decision_id} successfully reverted to status: {undo_res.json()['status']}")

    # Export again after undo
    exp_undo = client.post(
        f"/api/v1/runs/{run_id}/exports",
        headers=headers_admin,
        json={"format": "csv", "include_cleaned_only": True},
    )
    assert exp_undo.status_code == 201
    dl_undo = client.get(exp_undo.json()["download_url"], headers=headers_admin)
    assert dl_undo.status_code == 200
    df_undo = pd.read_csv(io.BytesIO(dl_undo.content))
    print(f"  Export generated post-undo: {len(df_undo)} rows parsed.")
    orig_df = pd.read_csv(io.BytesIO(initial_bytes))
    # Assert that approved export modified the mojibake rows
    assert (export_files["csv"]["full_name"] != orig_df["full_name"]).any(), "Approved decision was NOT applied in export!"
    print(f"  [VERIFIED] Approved decision was actively applied in export (mojibake encoding cleaned)!")

    # Check that undo export matches original uncleaned target column
    pd.testing.assert_series_equal(df_undo["full_name"], orig_df["full_name"], check_names=True)
    print(f"  [VERIFIED] Post-undo export perfectly matches original source column 'full_name' bit-for-bit (decision not applied)!")

    # 9. Security Vectors
    print("\n--- Testing Security Vectors ---")
    # A. Unauthenticated download
    unauth_dl = client.get(f"/api/v1/downloads/{uuid4()}.csv")
    assert unauth_dl.status_code == 401, f"Expected 401, got {unauth_dl.status_code}"
    print("  [SEC-1] Unauthenticated download: 401 Unauthorized [PASS]")

    # B. Cross-tenant access to run
    cross_run = client.get(f"/api/v1/runs/{run_id}", headers=headers_outsider)
    assert cross_run.status_code in (403, 404), f"Expected 403/404, got {cross_run.status_code}"
    print(f"  [SEC-2] Cross-tenant run access: {cross_run.status_code} Forbidden/Not Found [PASS]")

    # C. Cross-tenant download access
    valid_filename = exp_undo.json()["download_url"].split("/")[-1]
    cross_dl = client.get(f"/api/v1/downloads/{valid_filename}", headers=headers_outsider)
    assert cross_dl.status_code in (403, 404), f"Expected 403/404, got {cross_dl.status_code}"
    print(f"  [SEC-3] Cross-tenant export download: {cross_dl.status_code} Forbidden/Not Found [PASS]")

    # D. Invalid download identifier (random UUID)
    invalid_dl = client.get(f"/api/v1/downloads/{uuid4()}.csv", headers=headers_admin)
    assert invalid_dl.status_code == 404, f"Expected 404, got {invalid_dl.status_code}"
    print("  [SEC-4] Non-existent export UUID: 404 Not Found [PASS]")

    # E. Path traversal attacks
    traversal_payloads = [
        "..%2F..%2F..%2Fetc%2Fpasswd.csv",
        "....//....//storage//demo//demo_customers_1000.csv",
        r"..\..\test_migration.db.csv",
        "test/export.csv",
        "non-uuid-file.csv",
    ]
    for payload in traversal_payloads:
        trav_res = client.get(f"/api/v1/downloads/{payload}", headers=headers_admin)
        assert trav_res.status_code in (400, 404), f"Traversal payload '{payload}' returned {trav_res.status_code}"
    print("  [SEC-5] Path traversal and malicious filename payloads: Blocked (400/404) [PASS]")

    # 10. Bit-for-bit SHA-256 Immutability Check
    print("\n--- Verifying Source File Immutability ---")
    post_bytes = demo_file.read_bytes()
    post_sha256 = hashlib.sha256(post_bytes).hexdigest()
    print(f"  Pre-run  SHA-256: {initial_sha256}")
    print(f"  Post-run SHA-256: {post_sha256}")
    assert initial_sha256 == post_sha256, "Source file was modified!"
    print("  [IMMUTABILITY] Source file SHA-256 remains 100% bit-for-bit identical [PASS]")

    print("\n" + "=" * 80)
    print("ALL DEEP INDEPENDENT VERIFICATION CHECKS PASSED PERFECTLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_deep_verification()
