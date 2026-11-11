# AgentIQ v2 — API Specification & Contract Reference

**Base URL:** `http://localhost:8000`  
**API Prefix:** `/api/v1`  
**OpenAPI Specification:** [`contracts/openapi.json`](../contracts/openapi.json) | [`contracts/api-spec.yaml`](../contracts/api-spec.yaml)

---

## 1. Global Conventions

### 1.1 Field Naming and Serialization
- All JSON property keys use `snake_case`.
- All timestamps are serialized as ISO 8601 UTC strings (e.g., `2026-11-11T12:00:00Z`).
- All entity identifiers (`id`, `workspace_id`, `project_id`, `run_id`, etc.) are standard RFC 4122 UUID v4 strings.

### 1.2 Standardized Error Responses
Every HTTP error (4xx and 5xx) strictly follows this uniform schema:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable explanation",
    "details": null
  }
}
```

Common error codes:
| Error Code | HTTP Status | Description |
|---|---|---|
| `UNAUTHORIZED` | 401 | Missing or invalid Bearer JWT token |
| `FORBIDDEN` | 403 | User has insufficient role permissions in the target workspace |
| `NOT_FOUND` | 404 | Requested entity does not exist |
| `VALIDATION_ERROR` | 422 | Request body, query parameter, or file failed schema validation |
| `CONTENT_TOO_LARGE` | 413 | Uploaded payload exceeds size limit (100MB) |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled server exception |

### 1.3 State Enums
- **Run Statuses:** `queued`, `processing`, `completed`, `failed`, `cancelled`
- **Run Stages:** `reading`, `detecting`, `grouping`, `explaining`, `summarizing`
- **Workspace Roles:** `admin`, `reviewer`, `viewer`
- **Finding Severities:** `low`, `medium`, `high`, `critical`
- **Finding Categories:** `missing_value`, `outlier`, `type_mismatch`, `duplicate`, `format_inconsistency`, `business_rule_violation`
- **Finding Actions:** `drop_row`, `impute`, `replace`, `transform`, `ignore`
- **Decision Statuses:** `applied`, `undone`
- **Export Formats:** `csv`, `parquet`, `excel`

---

## 2. API Endpoint Inventory

| Method | Endpoint | Auth | Required Role | Summary |
|---|---|---|---|---|
| `GET` | `/health` | None | None | Service liveness and version check |
| `GET` | `/api/v1/auth/me` | Bearer Token | Authenticated User | Authenticated user profile & workspaces |
| `GET` | `/api/v1/projects` | Bearer Token | `admin`, `reviewer`, `viewer` | List projects for active workspace |
| `POST` | `/api/v1/projects` | Bearer Token | `admin` | Create project within workspace |
| `POST` | `/api/v1/uploads` | Bearer Token | `admin`, `reviewer` | Upload dataset file (multipart/form-data) |
| `POST` | `/api/v1/runs` | Bearer Token | `admin`, `reviewer` | Trigger async profiling & cleaning run |
| `GET` | `/api/v1/runs/{run_id}` | Bearer Token | `admin`, `reviewer`, `viewer` | Poll run status & stage progress (2s poll) |
| `GET` | `/api/v1/runs/{run_id}/summary` | Bearer Token | `admin`, `reviewer`, `viewer` | Summary metrics & anomaly counts |
| `GET` | `/api/v1/runs/{run_id}/findings` | Bearer Token | `admin`, `reviewer`, `viewer` | Paginated detected findings & AI actions |
| `POST` | `/api/v1/findings/{finding_id}/decisions` | Bearer Token | `admin`, `reviewer` | Submit reviewer remediation decision |
| `POST` | `/api/v1/decisions/{decision_id}/undo` | Bearer Token | `admin`, `reviewer` | Revert remediation decision |
| `GET` | `/api/v1/runs/{run_id}/compare` | Bearer Token | `admin`, `reviewer`, `viewer` | Side-by-side diff (raw vs cleaned) |
| `GET` | `/api/v1/runs/{run_id}/audit` | Bearer Token | `admin`, `reviewer`, `viewer` | Immutable chronological audit trail |
| `POST` | `/api/v1/runs/{run_id}/exports` | Bearer Token | `admin`, `reviewer` | Generate downloadable cleaned dataset |

---

## 3. Endpoint Specifications

### 3.1 `GET /health`
- **Summary:** Service Health Check
- **Authentication:** Public
- **Permissions:** None
- **Response `200 OK`:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-11-11T12:00:00Z"
}
```

---

### 3.2 `GET /api/v1/auth/me`
- **Summary:** Authenticated User Profile & Workspace Memberships
- **Authentication:** `Authorization: Bearer <supabase_jwt>`
- **Permissions:** Valid Supabase authenticated user
- **Possible Errors:** `401 Unauthorized`
- **Response `200 OK`:**
```json
{
  "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "email": "reviewer@example.com",
  "full_name": "Jane Doe",
  "workspaces": [
    {
      "workspace_id": "00000000-0000-0000-0000-000000000001",
      "workspace_name": "Acme Analytics",
      "role": "reviewer"
    }
  ],
  "created_at": "2026-01-15T08:30:00Z"
}
```

---

### 3.3 `GET /api/v1/projects`
- **Summary:** List Projects in Active Workspace
- **Headers:** `X-Workspace-ID: <uuid>`, `Authorization: Bearer <token>`
- **Query Params:** `limit` (default 20), `offset` (default 0)
- **Permissions:** `viewer` or higher
- **Possible Errors:** `401 Unauthorized`, `403 Forbidden`
- **Response `200 OK`:**
```json
{
  "items": [
    {
      "id": "11111111-1111-1111-1111-111111111111",
      "workspace_id": "00000000-0000-0000-0000-000000000001",
      "name": "Q4 Customer Churn",
      "description": "Customer demographic and churn dataset",
      "created_at": "2026-11-10T10:00:00Z",
      "updated_at": "2026-11-10T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

### 3.4 `POST /api/v1/projects`
- **Summary:** Create Project
- **Headers:** `X-Workspace-ID: <uuid>`, `Authorization: Bearer <token>`
- **Permissions:** `admin`
- **Request Body:**
```json
{
  "name": "Q4 Sales Data",
  "description": "Monthly retail transactional logs",
  "workspace_id": "00000000-0000-0000-0000-000000000001"
}
```
- **Response `201 Created`:**
```json
{
  "id": "77777777-7777-7777-7777-777777777777",
  "workspace_id": "00000000-0000-0000-0000-000000000001",
  "name": "Q4 Sales Data",
  "description": "Monthly retail transactional logs",
  "created_at": "2026-11-11T12:05:00Z",
  "updated_at": "2026-11-11T12:05:00Z"
}
```

---

### 3.5 `POST /api/v1/uploads`
- **Summary:** Upload Raw Dataset File
- **Content-Type:** `multipart/form-data`
- **Headers:** `X-Workspace-ID: <uuid>`, `Authorization: Bearer <token>`
- **Permissions:** `reviewer` or higher
- **Form Fields:**
  - `file`: Binary file (`.csv`, `.parquet`, `.xlsx`, `.json`)
  - `project_id`: UUID
- **Possible Errors:** `400 Bad Request` (unsupported extension), `413 Content Too Large` (>100MB), `403 Forbidden`
- **Response `201 Created`:**
```json
{
  "id": "22222222-2222-2222-2222-222222222222",
  "project_id": "11111111-1111-1111-1111-111111111111",
  "filename": "customers_raw.csv",
  "file_size_bytes": 1048576,
  "mime_type": "text/csv",
  "row_count": null,
  "column_count": null,
  "storage_path": "storage/raw/11111111-1111-1111-1111-111111111111/22222222-2222-2222-2222-222222222222_customers_raw.csv",
  "created_at": "2026-11-11T12:06:00Z"
}
```

---

### 3.6 `POST /api/v1/runs`
- **Summary:** Trigger Cleaning & Profiling Run
- **Headers:** `X-Workspace-ID: <uuid>`, `Authorization: Bearer <token>`
- **Permissions:** `reviewer` or higher
- **Request Body:**
```json
{
  "project_id": "11111111-1111-1111-1111-111111111111",
  "upload_id": "22222222-2222-2222-2222-222222222222",
  "config": {
    "enable_ai_explanations": true,
    "sample_size": 50000,
    "anomaly_threshold": 0.85,
    "parameters": {}
  }
}
```
- **Response `202 Accepted`:**
```json
{
  "id": "44444444-4444-4444-4444-444444444444",
  "project_id": "11111111-1111-1111-1111-111111111111",
  "upload_id": "22222222-2222-2222-2222-222222222222",
  "status": "queued",
  "stage": null,
  "progress": {
    "current_stage": null,
    "stage_percent": 0,
    "total_percent": 0,
    "message": "Run enqueued for asynchronous worker processing"
  },
  "started_at": null,
  "completed_at": null,
  "error_message": null,
  "created_at": "2026-11-11T12:07:00Z"
}
```

---

### 3.7 `GET /api/v1/runs/{run_id}`
- **Summary:** Poll Run Status & Progress (poll interval: 2 seconds)
- **Headers:** `X-Workspace-ID: <uuid>`, `Authorization: Bearer <token>`
- **Permissions:** `viewer` or higher
- **Response `200 OK`:**
```json
{
  "id": "44444444-4444-4444-4444-444444444444",
  "project_id": "11111111-1111-1111-1111-111111111111",
  "upload_id": "22222222-2222-2222-2222-222222222222",
  "status": "processing",
  "stage": "explaining",
  "progress": {
    "current_stage": "explaining",
    "stage_percent": 60,
    "total_percent": 75,
    "message": "Generating Gemini AI explanations for detected outliers..."
  },
  "started_at": "2026-11-11T12:07:02Z",
  "completed_at": null,
  "error_message": null,
  "created_at": "2026-11-11T12:07:00Z"
}
```

---

### 3.8 `GET /api/v1/runs/{run_id}/summary`
- **Summary:** High-level Statistical Quality Summary
- **Headers:** `X-Workspace-ID: <uuid>`, `Authorization: Bearer <token>`
- **Permissions:** `viewer` or higher
- **Response `200 OK`:**
```json
{
  "run_id": "44444444-4444-4444-4444-444444444444",
  "total_rows": 10000,
  "total_columns": 12,
  "dirty_rows": 145,
  "clean_rows": 9855,
  "total_findings": 160,
  "findings_by_severity": {
    "critical": 10,
    "high": 35,
    "medium": 75,
    "low": 40
  },
  "findings_by_category": {
    "missing_value": 80,
    "outlier": 35,
    "type_mismatch": 25,
    "duplicate": 20
  },
  "estimated_quality_score": 94.2
}
```

---

### 3.9 `GET /api/v1/runs/{run_id}/findings`
- **Summary:** Paginated Anomalies with AI Remediations
- **Headers:** `X-Workspace-ID: <uuid>`, `Authorization: Bearer <token>`
- **Query Params:** `category`, `severity`, `limit` (default 50), `offset` (default 0)
- **Permissions:** `viewer` or higher
- **Response `200 OK`:**
```json
{
  "items": [
    {
      "id": "33333333-3333-3333-3333-333333333333",
      "run_id": "44444444-4444-4444-4444-444444444444",
      "row_index": 42,
      "column_name": "email",
      "category": "format_inconsistency",
      "severity": "high",
      "description": "Value does not match RFC standard email formatting pattern.",
      "affected_value": "user@@domain..com",
      "suggested_action": {
        "action_type": "replace",
        "parameters": {
          "regex_replace": "@+",
          "replacement": "@"
        },
        "rationale": "AI detected redundant consecutive '@' symbols likely originating from form copy-paste error."
      },
      "is_resolved": false,
      "created_at": "2026-11-11T12:07:30Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### 3.10 `POST /api/v1/findings/{finding_id}/decisions`
- **Summary:** Submit Remediation Decision
- **Headers:** `X-Workspace-ID: <uuid>`, `Authorization: Bearer <token>`
- **Permissions:** `reviewer` or higher
- **Request Body:**
```json
{
  "action_type": "replace",
  "custom_parameters": {
    "replacement": "user@domain.com"
  },
  "notes": "Verified against customer master records."
}
```
- **Response `201 Created`:**
```json
{
  "id": "55555555-5555-5555-5555-555555555555",
  "finding_id": "33333333-3333-3333-3333-333333333333",
  "run_id": "44444444-4444-4444-4444-444444444444",
  "user_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "action_type": "replace",
  "parameters": {
    "replacement": "user@domain.com"
  },
  "status": "applied",
  "decided_at": "2026-11-11T12:10:00Z"
}
```

---

### 3.11 `POST /api/v1/decisions/{decision_id}/undo`
- **Summary:** Revert Decision
- **Headers:** `X-Workspace-ID: <uuid>`, `Authorization: Bearer <token>`
- **Permissions:** `reviewer` or higher
- **Response `200 OK`:**
```json
{
  "decision_id": "55555555-5555-5555-5555-555555555555",
  "status": "undone",
  "undone_at": "2026-11-11T12:12:00Z",
  "message": "Decision 55555555-5555-5555-5555-555555555555 was successfully reverted."
}
```

---

### 3.12 `GET /api/v1/runs/{run_id}/compare`
- **Summary:** Compare Raw vs Cleaned Dataset
- **Headers:** `X-Workspace-ID: <uuid>`, `Authorization: Bearer <token>`
- **Permissions:** `viewer` or higher
- **Response `200 OK`:**
```json
{
  "run_id": "44444444-4444-4444-4444-444444444444",
  "original_rows_count": 10000,
  "cleaned_rows_count": 9980,
  "columns_diff": [
    {
      "column_name": "email",
      "original_nulls": 45,
      "cleaned_nulls": 0,
      "changes_count": 120
    }
  ],
  "preview_original": [
    {"id": 1, "email": "invalid@@domain.com"}
  ],
  "preview_cleaned": [
    {"id": 1, "email": "invalid@domain.com"}
  ]
}
```

---

### 3.13 `GET /api/v1/runs/{run_id}/audit`
- **Summary:** Audit Trail of Run & Decision Events
- **Headers:** `X-Workspace-ID: <uuid>`, `Authorization: Bearer <token>`
- **Permissions:** `viewer` or higher
- **Response `200 OK`:**
```json
{
  "run_id": "44444444-4444-4444-4444-444444444444",
  "events": [
    {
      "id": "66666666-6666-6666-6666-666666666666",
      "run_id": "44444444-4444-4444-4444-444444444444",
      "user_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "action": "finding.decided",
      "details": {
        "finding_id": "33333333-3333-3333-3333-333333333333",
        "action_type": "replace"
      },
      "timestamp": "2026-11-11T12:10:00Z"
    }
  ],
  "total": 1
}
```

---

### 3.14 `POST /api/v1/runs/{run_id}/exports`
- **Summary:** Generate Cleaned Dataset Download
- **Headers:** `X-Workspace-ID: <uuid>`, `Authorization: Bearer <token>`
- **Permissions:** `reviewer` or higher
- **Request Body:**
```json
{
  "format": "parquet",
  "include_cleaned_only": true
}
```
- **Response `201 Created`:**
```json
{
  "id": "88888888-8888-8888-8888-888888888888",
  "run_id": "44444444-4444-4444-4444-444444444444",
  "format": "parquet",
  "file_size_bytes": 1048576,
  "download_url": "/api/v1/downloads/88888888-8888-8888-8888-888888888888.parquet",
  "expires_at": "2026-11-12T12:00:00Z",
  "created_at": "2026-11-11T12:00:00Z"
}
```

