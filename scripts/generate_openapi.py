"""Generate and validate contracts/openapi.json and contracts/api-spec.yaml from FastAPI."""

import json
import os
import sys
from pathlib import Path
import yaml

# Ensure project root, packages, and apps are on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "packages"))
sys.path.insert(0, str(BASE_DIR / "apps"))

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


def generate_and_validate_contracts() -> None:
    contracts_dir = BASE_DIR / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)

    openapi_schema = app.openapi()

    # 1. Validate all required operations are registered
    registered_paths = openapi_schema.get("paths", {})
    missing_ops = []
    for method, path in REQUIRED_OPERATIONS:
        if path not in registered_paths or method.lower() not in registered_paths[path]:
            missing_ops.append(f"{method} {path}")

    if missing_ops:
        print(f"ERROR: Missing required contract operations: {missing_ops}", file=sys.stderr)
        sys.exit(1)

    print(f"SUCCESS: All {len(REQUIRED_OPERATIONS)} required API endpoints are present in the schema.")

    # 2. Write contracts/openapi.json
    json_path = contracts_dir / "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"Wrote OpenAPI JSON to {json_path}")

    # 3. Write contracts/api-spec.yaml
    yaml_path = contracts_dir / "api-spec.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(openapi_schema, f, sort_keys=False, allow_unicode=True)
    print(f"Wrote OpenAPI YAML to {yaml_path}")


if __name__ == "__main__":
    generate_and_validate_contracts()
