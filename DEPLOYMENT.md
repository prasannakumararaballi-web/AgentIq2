# AgentIQ v2 — Production Deployment Guide

## Overview

AgentIQ v2 is structured for modern cloud hosting with a decoupled frontend, containerized backend API, managed PostgreSQL database, and persistent file storage:

```
[ Browser / Client ]
        │
        ▼ (HTTPS)
[ Vercel: Next.js 15 App Router ] ── (Public API calls / JWT)
        │
        ▼ (HTTPS)
[ Render: FastAPI Container + DuckDB Engine ]
   ├── Persistent Disk (/app/storage)
   └── Supabase Managed PostgreSQL (pgvector, RLS, Alembic Migrations)
```

---

## 1. Prerequisites & Required Services

1. **GitHub Repository**: Central source code repository connected to Vercel and Render for automated continuous deployment.
2. **Supabase Project**: Managed PostgreSQL instance for tenant schemas, dataset profiling metadata, anomaly findings, and cryptographic audit log.
3. **Render Account**: Web Service host running Dockerfile container with persistent SSD storage disk.
4. **Vercel Account**: Production hosting for Next.js 15 with edge caching and SSL termination.

---

## 2. Step 1: Database Setup (Supabase PostgreSQL)

1. Create a new project in your Supabase dashboard or connect an existing project.
2. Under **Project Settings > Database**:
   - Copy the **Connection String (URI)** for Transaction Pooler (port 6543) or Direct Connection (port 5432).
   - Format for asynchronous SQLAlchemy (`DATABASE_URL`):
     ```
     postgresql+asyncpg://postgres.[PROJECT-REF]:[DB-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?ssl=require
     ```
   - Format for synchronous Alembic runner (`DIRECT_DATABASE_URL`):
     ```
     postgresql://postgres:[DB-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require
     ```
3. Run Alembic migrations against the cloud database:
   ```bash
   export DIRECT_DATABASE_URL="postgresql://postgres:[DB-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require"
   alembic upgrade head
   ```
   This executes migrations `001_initial_schema`, `002_add_upload_hash_and_metadata`, and `003_add_finding_card_fields`.

---

## 3. Step 2: Backend Deployment (Render)

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New > Web Service** and select your GitHub repository `AgentIQ-v2`.
3. Choose **Docker** as the runtime (pointing to `Dockerfile`).
4. Set Instance Type to **Starter** or higher (required for persistent disk support).
5. Add a **Persistent Disk**:
   - **Name**: `agentiq-storage`
   - **Mount Path**: `/app/storage`
   - **Size**: 10 GB (expandable)
6. Configure Environment Variables in Render:
   - `ENVIRONMENT`: `production`
   - `DATABASE_URL`: `postgresql+asyncpg://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?ssl=require`
   - `DIRECT_DATABASE_URL`: `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require`
   - `SUPABASE_URL`: `https://[PROJECT-REF].supabase.co`
   - `SUPABASE_JWT_SECRET`: `[YOUR-SUPABASE-JWT-SECRET]`
   - `SUPABASE_ANON_KEY`: `[YOUR-SUPABASE-ANON-KEY]`
   - `STORAGE_BACKEND`: `local`
   - `LOCAL_STORAGE_PATH`: `/app/storage`
   - `CORS_ORIGINS`: `https://[YOUR-VERCEL-DOMAIN].vercel.app`
7. Click **Create Web Service**.
8. Verify deployment by visiting `https://[YOUR-RENDER-APP].onrender.com/health`.
   Expected response:
   ```json
   {"status":"healthy","version":"0.1.0","timestamp":"...","database":"connected"}
   ```

---

## 4. Step 3: Frontend Deployment (Vercel)

1. Log in to [Vercel Dashboard](https://vercel.com).
2. Click **Add New > Project** and import the GitHub repository.
3. In the project configuration:
   - **Root Directory**: Select `apps/web`.
   - **Framework Preset**: Next.js.
4. Add Environment Variables:
   - `NEXT_PUBLIC_API_URL`: `https://[YOUR-RENDER-APP].onrender.com/api/v1`
   - `NEXT_PUBLIC_SUPABASE_URL`: `https://[PROJECT-REF].supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: `[YOUR-SUPABASE-ANON-KEY]`
5. Click **Deploy**.
6. Once deployed, copy your production Vercel domain (e.g. `https://agentiq-v2.vercel.app`) and add it to `CORS_ORIGINS` in your Render backend settings.

---

## 5. Step 4: Verification Checklist

1. Open `https://[YOUR-VERCEL-DOMAIN].vercel.app/login` in any browser.
2. Authenticate using Supabase credentials or custom JWT.
3. Create a project and upload a test CSV dataset.
4. Verify SHA-256 integrity hash is computed and stored.
5. Trigger automated profiling run and observe real TabularEngine detection cards.
6. Test decision approval and reversal (undo).
7. Download CSV, Excel, and Parquet exports to confirm file persistence.
