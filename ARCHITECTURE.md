# AgentIQ v2 — Production Architecture Specification

## 1. System Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Vercel Edge Network                  │
│                                                        │
│   Next.js 15.2.1 App Router (React 19, TypeScript)     │
│   - Canvas UI (#F6F7FB) & Obsidian Navigation          │
│   - SVG QualityGauge & Dynamic Radial Telemetry        │
│   - Real-time TanStack React Query Cache               │
│   - Multi-tenant Session & RBAC Workspace Context      │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTPS / JSON / Streaming Blobs
                           ▼
┌────────────────────────────────────────────────────────┐
│                   Render Container Host                │
│                                                        │
│   FastAPI Web Service (Python 3.12 / 3.13)             │
│   - Multi-worker Uvicorn with Proxy Headers            │
│   - Strict Workspace Isolation Dependency Injection    │
│   - Cryptographic JWT Bearer Token Verification        │
│   - Synchronous Engine Analysis Router                 │
│                                                        │
│   Data Quality Engine                                  │
│   - TabularEngine (DuckDB + Vectorized Pandas)         │
│   - 8 Independent Anomaly Detection Category Modules   │
│   - Human-in-the-Loop Decision & Reversal (Undo)       │
│                                                        │
│   Mounted Persistent SSD Volume (/app/storage)         │
│   - /raw/{workspace_id}/{project_id}/...               │
│   - /cleaned/{workspace_id}/{project_id}/...           │
│   - /exports/{workspace_id}/{export_id}.{format}       │
└──────────────────────────┬─────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│   Supabase PostgreSQL    │   │  Persistent File Storage │
│                          │   │                          │
│ - Multi-tenant Schemas   │   │ - Render SSD 10GB Volume │
│ - Alembic Migrations     │   │ - SHA-256 Immutability   │
│   (001, 002, 003)        │   │ - CSV, Excel, Parquet    │
│ - Findings & Decisions   │   │ - Authenticated Streams  │
│ - Immutable Audit Trail  │   │ - Traversal Protection   │
└──────────────────────────┘   └──────────────────────────┘
```

---

## 2. Security Boundaries & Tenancy

1. **Workspace Boundary**: Every dataset, run, finding card, decision, and audit record is strictly partitioned by `workspace_id`.
2. **Access Control (RBAC)**:
   - `admin`: Full configuration, profiling, remediation, decision undo, and export authority.
   - `reviewer`: Human-in-the-loop finding review, approval/rejection, undo, and export download.
   - `viewer`: Read-only telemetry inspection. Cannot trigger runs, approve mutations, or undo records.
3. **Storage Security**:
   - Files are stored with sanitized names under directory hierarchies prefixed by `workspace_id`.
   - File downloads are proxied through `/api/v1/downloads/{filename}`, requiring valid JWT authorization and tenant verification.
   - Path traversal attempts (e.g. `../../etc/passwd`) are detected and rejected with HTTP 400.
4. **File Integrity**:
   - Every uploaded dataset has its SHA-256 cryptographic digest calculated during ingestion and stored in the database.
   - Analysis execution is read-only against the raw input; the raw file's hash is re-verified after engine execution to ensure zero bit-level tampering.

---

## 3. Background Processing Roadmap (Phase 3)

The current production release executes dataset analysis synchronously during the HTTP request lifecycle (`sync=True`), completing profiling and anomaly detection on 1,000 rows in under 0.5 seconds.

For enterprise datasets (> 100,000 rows), Phase 3 will introduce:
- Asynchronous Celery / Procrastinate task worker queue backed by Redis or PostgreSQL `pgmq`.
- WebSocket or Server-Sent Events (SSE) telemetry pipeline for row-by-row streaming progress.
- Decoupled worker autoscaling independent of the HTTP API web servers.
