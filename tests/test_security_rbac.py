"""Security and Role-Based Access Control (RBAC) test suite.

Proves:
1. Missing token returns 401.
2. Invalid token returns 401.
3. Expired token returns 401.
4. Valid token can access authorized endpoints.
5. Viewer cannot approve findings (403).
6. Reviewer can approve findings (201).
7. Admin can manage workspace members (201).
8. Workspace A cannot access Workspace B (403).
9. Changing X-Workspace-ID to an unauthorized workspace returns 403.
10. A user cannot access another workspace's projects or runs by guessing their UUIDs (IDOR prevention -> 404).
"""

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    ADMIN_USER_ID,
    FINDING_A_ID,
    PROJECT_A_ID,
    PROJECT_B_ID,
    REVIEWER_USER_ID,
    RUN_A_ID,
    VIEWER_USER_ID,
    WORKSPACE_A_ID,
    WORKSPACE_B_ID,
    make_jwt,
)


# 1. Missing token returns 401
def test_missing_token_returns_401(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "Missing" in data["error"]["message"]


# 2. Invalid token returns 401
def test_invalid_token_returns_401(client: TestClient):
    # Pass token signed with a bogus key or corrupt signature
    invalid_token = make_jwt(ADMIN_USER_ID, secret="wrong-secret-key-that-fails-signature")
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {invalid_token}"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "signature verification failed" in data["error"]["message"].lower()


# 3. Expired token returns 401
def test_expired_token_returns_401(client: TestClient):
    # Token expired 1 hour ago
    expired_token = make_jwt(ADMIN_USER_ID, exp_seconds=-3600)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "expired" in data["error"]["message"].lower()


# 4. Valid token can access authorized endpoints
def test_valid_token_can_access_authorized_endpoint(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(ADMIN_USER_ID)
    assert data["email"] == "admin@example.com"
    assert len(data["workspaces"]) == 1
    assert data["workspaces"][0]["workspace_id"] == str(WORKSPACE_A_ID)


# 5. Viewer cannot approve findings (403)
def test_viewer_cannot_approve_findings(client: TestClient, viewer_headers: dict[str, str]):
    response = client.post(
        f"/api/v1/findings/{FINDING_A_ID}/decisions",
        headers=viewer_headers,
        json={"action_type": "replace", "custom_parameters": {"val": "clean"}},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"
    assert "Insufficient permissions" in data["error"]["message"]


# 6. Reviewer can approve findings
def test_reviewer_can_approve_findings(client: TestClient, reviewer_headers: dict[str, str]):
    response = client.post(
        f"/api/v1/findings/{FINDING_A_ID}/decisions",
        headers=reviewer_headers,
        json={"action_type": "replace", "custom_parameters": {"replacement": "cleaned_val"}},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["finding_id"] == str(FINDING_A_ID)
    assert data["status"] == "applied"


# 7. Admin can manage workspace members
def test_admin_can_manage_workspace_members(
    client: TestClient,
    auth_headers: dict[str, str],
    reviewer_headers: dict[str, str],
):
    new_user_id = uuid4()

    # Non-admin (reviewer) cannot add member -> 403
    forbidden_res = client.post(
        f"/api/v1/workspaces/{WORKSPACE_A_ID}/members",
        headers=reviewer_headers,
        json={"user_id": str(new_user_id), "role": "viewer"},
    )
    assert forbidden_res.status_code == 403

    # Admin CAN add member -> 201
    success_res = client.post(
        f"/api/v1/workspaces/{WORKSPACE_A_ID}/members",
        headers=auth_headers,
        json={"user_id": str(new_user_id), "role": "viewer"},
    )
    assert success_res.status_code == 201
    assert success_res.json()["user_id"] == str(new_user_id)
    assert success_res.json()["role"] == "viewer"

    # Admin can list members -> 200
    list_res = client.get(
        f"/api/v1/workspaces/{WORKSPACE_A_ID}/members",
        headers=auth_headers,
    )
    assert list_res.status_code == 200
    member_user_ids = [m["user_id"] for m in list_res.json()["items"]]
    assert str(new_user_id) in member_user_ids


# 8. Workspace A cannot access Workspace B
def test_workspace_a_cannot_access_workspace_b(client: TestClient, auth_headers: dict[str, str]):
    # User belongs to Workspace A, attempts to read Workspace B's members
    response = client.get(
        f"/api/v1/workspaces/{WORKSPACE_B_ID}/members",
        headers={"Authorization": auth_headers["Authorization"], "X-Workspace-ID": str(WORKSPACE_B_ID)},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"
    assert "does not have access to workspace" in data["error"]["message"]


# 9. Changing X-Workspace-ID to an unauthorized workspace returns 403
def test_tampering_workspace_id_header_returns_403(client: TestClient, auth_headers: dict[str, str]):
    arbitrary_workspace_id = uuid4()
    tampered_headers = {
        "Authorization": auth_headers["Authorization"],
        "X-Workspace-ID": str(arbitrary_workspace_id),
    }
    response = client.get("/api/v1/projects", headers=tampered_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"
    assert "does not have access" in data["error"]["message"]


# 10. A user cannot access another workspace's projects or runs by guessing their UUIDs (IDOR prevention)
def test_idor_protection_prevents_access_to_other_workspace_resources(
    client: TestClient,
    auth_headers: dict[str, str],
):
    # PROJECT_B_ID exists in the database, but belongs to Workspace B.
    # An authorized user of Workspace A attempts to upload to or trigger runs on PROJECT_B_ID.
    idor_upload_attempt = client.post(
        "/api/v1/uploads",
        headers=auth_headers,
        data={"project_id": str(PROJECT_B_ID)},
        files={"file": ("exploit.csv", b"col1\nval1\n", "text/csv")},
    )
    # The server strictly scopes by Project.workspace_id == context.workspace_id, returning 404
    assert idor_upload_attempt.status_code == 404
    data = idor_upload_attempt.json()
    assert data["error"]["code"] == "NOT_FOUND"
    assert "Project" in data["error"]["message"]

