"""Integration tests for all API endpoints, RBAC, and error handlers."""

from io import BytesIO
from uuid import uuid4
from fastapi.testclient import TestClient
from tests.conftest import (
    ADMIN_USER_ID,
    DECISION_A_ID,
    FINDING_A_ID,
    PROJECT_A_ID,
    RUN_A_ID,
    UPLOAD_A_ID,
    WORKSPACE_A_ID,
)


def test_auth_me_without_token_returns_401(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "Missing" in data["error"]["message"]


def test_auth_me_with_valid_token_returns_user(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@example.com"
    assert len(data["workspaces"]) > 0
    assert data["workspaces"][0]["workspace_id"] == str(WORKSPACE_A_ID)


def test_projects_endpoints(client: TestClient, auth_headers: dict[str, str]):
    # 1. List Projects
    res_list = client.get("/api/v1/projects", headers=auth_headers)
    assert res_list.status_code == 200
    assert "items" in res_list.json()

    # 2. Create Project
    res_create = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={
            "name": "Integration Test Project",
            "description": "Testing project creation",
            "workspace_id": auth_headers["X-Workspace-ID"],
        },
    )
    assert res_create.status_code == 201
    assert res_create.json()["name"] == "Integration Test Project"


def test_upload_endpoint(client: TestClient, auth_headers: dict[str, str]):
    file_content = b"col1,col2\nval1,val2\n"
    res = client.post(
        "/api/v1/uploads",
        headers={"Authorization": auth_headers["Authorization"], "X-Workspace-ID": auth_headers["X-Workspace-ID"]},
        data={"project_id": str(PROJECT_A_ID)},
        files={"file": ("dataset.csv", BytesIO(file_content), "text/csv")},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["filename"] == "dataset.csv"
    assert data["file_size_bytes"] == len(file_content)


def test_upload_invalid_extension_returns_400(client: TestClient, auth_headers: dict[str, str]):
    res = client.post(
        "/api/v1/uploads",
        headers={"Authorization": auth_headers["Authorization"], "X-Workspace-ID": auth_headers["X-Workspace-ID"]},
        data={"project_id": str(PROJECT_A_ID)},
        files={"file": ("malicious.exe", BytesIO(b"MZ..."), "application/octet-stream")},
    )
    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "BAD_REQUEST"
    assert "Unsupported file format" in data["error"]["message"]


def test_runs_lifecycle_and_auxiliary_endpoints(client: TestClient, auth_headers: dict[str, str]):
    # 1. Trigger Run (POST /api/v1/runs)
    res_run = client.post(
        "/api/v1/runs",
        headers=auth_headers,
        json={"project_id": str(PROJECT_A_ID), "upload_id": str(UPLOAD_A_ID)},
    )
    assert res_run.status_code == 202
    run_id = res_run.json()["id"]

    # 2. Poll Run Status (GET /api/v1/runs/{run_id})
    res_poll = client.get(f"/api/v1/runs/{run_id}", headers=auth_headers)
    assert res_poll.status_code == 200
    assert "progress" in res_poll.json()

    # 3. Get Summary (GET /api/v1/runs/{run_id}/summary)
    res_sum = client.get(f"/api/v1/runs/{run_id}/summary", headers=auth_headers)
    assert res_sum.status_code == 200
    assert "estimated_quality_score" in res_sum.json()

    # 4. Get Findings (GET /api/v1/runs/{run_id}/findings)
    res_findings = client.get(f"/api/v1/runs/{run_id}/findings", headers=auth_headers)
    assert res_findings.status_code == 200
    assert "items" in res_findings.json()

    # 5. Submit Decision (POST /api/v1/findings/{finding_id}/decisions)
    res_dec = client.post(
        f"/api/v1/findings/{FINDING_A_ID}/decisions",
        headers=auth_headers,
        json={
            "action_type": "replace",
            "custom_parameters": {"replacement": "cleaned_val"},
            "notes": "Reviewed and fixed",
        },
    )
    assert res_dec.status_code == 201
    decision_id = res_dec.json()["id"]

    # 6. Undo Decision (POST /api/v1/decisions/{decision_id}/undo)
    res_undo = client.post(f"/api/v1/decisions/{decision_id}/undo", headers=auth_headers)
    assert res_undo.status_code == 200
    assert res_undo.json()["status"] == "undone"

    # 7. Compare Raw vs Cleaned (GET /api/v1/runs/{run_id}/compare)
    res_comp = client.get(f"/api/v1/runs/{run_id}/compare", headers=auth_headers)
    assert res_comp.status_code == 200
    assert "columns_diff" in res_comp.json()

    # 8. Audit Trail (GET /api/v1/runs/{run_id}/audit)
    res_audit = client.get(f"/api/v1/runs/{run_id}/audit", headers=auth_headers)
    assert res_audit.status_code == 200
    assert "events" in res_audit.json()

    # 9. Create Export (POST /api/v1/runs/{run_id}/exports)
    res_export = client.post(
        f"/api/v1/runs/{run_id}/exports",
        headers=auth_headers,
        json={"format": "parquet", "include_cleaned_only": True},
    )
    assert res_export.status_code == 201
    assert "download_url" in res_export.json()


def test_validation_error_format_422(client: TestClient, auth_headers: dict[str, str]):
    # Send invalid JSON missing required project_id and upload_id
    response = client.post("/api/v1/runs", headers=auth_headers, json={})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(data["error"]["details"], list)
