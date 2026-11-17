# AgentIQ v2 — Production Readiness Checklist

This checklist must be verified prior to marking any deployment as complete.

| Category | Requirement | Implementation Status | Verification Method |
| :--- | :--- | :---: | :--- |
| **Security** | Secrets excluded from Git (`.env`, `.env.local`) | Verified | Git status and `.gitignore` inspection |
| **Security** | Stage demo-token endpoint disabled in production | Verified | Returns HTTP 403 Forbidden when `NODE_ENV === "production"` |
| **Security** | Database connection uses SSL | Configured | `ssl=require` appended to PostgreSQL pooler URI |
| **Security** | Cross-tenant isolation enforced | Verified | All queries filtered by `X-Workspace-ID` and verified by RBAC middleware |
| **Security** | Authenticated downloads only | Verified | `/api/v1/downloads/{filename}` requires valid JWT and tenant membership |
| **Security** | Path traversal protection on files | Verified | `sanitize_filename()` and strict path resolution checks |
| **Database** | PostgreSQL replaces SQLite in cloud | Verified | `postgresql+asyncpg://` driver configured in `Settings` |
| **Database** | Migrations 001, 002, and 003 applied | Verified | `alembic upgrade head` validated with `psycopg2-binary` |
| **Storage** | File persistence on container restart | Configured | Render 10GB persistent SSD disk mounted to `/app/storage` |
| **Storage** | Original file SHA-256 hash preservation | Verified | Re-verified 100% bit-for-bit identical after engine analysis |
| **Storage** | CSV, Excel (.xlsx), Parquet exports | Verified | Real file generators tested with openpyxl, pandas, pyarrow |
| **Backend** | Dockerfile multi-stage production build | Verified | Non-root `agentiq` user, health check, dynamic `$PORT` |
| **Backend** | Root healthcheck endpoint operational | Verified | `GET /health` returns 200 with DB status |
| **Backend** | CORS configured for Vercel domain | Verified | Dynamic JSON or comma-separated origins validator |
| **Frontend** | Monorepo root directory configured | Verified | Root set to `apps/web` |
| **Frontend** | Next.js 15 App Router static/dynamic build | Verified | `next build` passes with 0 type errors and 0 lint warnings |
| **Frontend** | Standalone demo dataset served from `/public` | Verified | `apps/web/public/demo_customers_1000.csv` bundled |
| **CI/CD** | Automated GitHub Actions workflow | Implemented | `.github/workflows/ci.yml` covering frontend and backend |
