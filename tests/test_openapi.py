"""Tests verifying OpenAPI contract compliance and schema completeness."""

import json
from pathlib import Path
from apps.api.main import app

REQUIRED_OPERATIONS = [
    ("GET", "/health"),
    ("GET", "/api/v1/auth/me"),
    ("GET", "/api/v1/projects"),
    ("POST", "/api/v1/projects"),
    ("POST", "/api/v1/uploads"),
    ("POST", "/api/v1/runs"),
    ("GET", "/api/v1/runs/{run_id}"),
    ("GET", "/api/v1/runs/{run_id}/summary"),
    ("GET", "/api/v1/runs/{run_id}/findings"),
    ("POST", "/api/v1/findings/{finding_id}/decisions"),
    ("POST", "/api/v1/decisions/{decision_id}/undo"),
    ("GET", "/api/v1/runs/{run_id}/compare"),
    ("GET", "/api/v1/runs/{run_id}/audit"),
    ("POST", "/api/v1/runs/{run_id}/exports"),
    ("GET", "/api/v1/workspaces/{workspace_id}/members"),
    ("POST", "/api/v1/workspaces/{workspace_id}/members"),
]


def test_openapi_schema_contains_all_endpoints():
    schema = app.openapi()
    paths = schema.get("paths", {})

    for method, path in REQUIRED_OPERATIONS:
        assert path in paths, f"Path {path} missing in OpenAPI schema"
        assert method.lower() in paths[path], f"Method {method} {path} missing in OpenAPI schema"


def test_openapi_json_file_matches_live_schema():
    contracts_file = Path(__file__).resolve().parent.parent / "contracts" / "openapi.json"
    assert contracts_file.exists(), "contracts/openapi.json does not exist"

    with open(contracts_file, "r", encoding="utf-8") as f:
        file_schema = json.load(f)

    live_schema = app.openapi()
    assert file_schema["info"]["title"] == live_schema["info"]["title"]
    assert set(file_schema["paths"].keys()) == set(live_schema["paths"].keys())


def test_openapi_security_scheme_defined():
    schema = app.openapi()
    security_schemes = schema.get("components", {}).get("securitySchemes", {})
    assert "HTTPBearer" in security_schemes

