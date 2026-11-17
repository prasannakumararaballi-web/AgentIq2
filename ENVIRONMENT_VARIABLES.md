# AgentIQ v2 — Environment Variables Reference

This document catalogs every environment variable recognized by AgentIQ v2 across frontend and backend services. **Do not paste secret credentials into shared repositories.**

---

## 1. Backend Service (FastAPI — Render)

| Variable Name | Required | Default / Example | Purpose |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | Yes | `production` | Deployment mode (disables debug utilities) |
| `DEBUG` | No | `false` | Enable verbose tracebacks (never in production) |
| `API_HOST` | No | `0.0.0.0` | Network interface to bind HTTP listener |
| `API_PORT` | No | `8000` | Fallback port (Render automatically provides `$PORT`) |
| `CORS_ORIGINS` | Yes | `https://your-app.vercel.app` | Allowed origins (JSON array or comma-separated) |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` | Asynchronous connection string for FastAPI queries |
| `DIRECT_DATABASE_URL` | Yes | `postgresql://...` | Synchronous connection string for Alembic migrations |
| `SUPABASE_URL` | Yes | `https://xyz.supabase.co` | Supabase project API gateway |
| `SUPABASE_JWT_SECRET` | Yes | `[YOUR-SUPABASE-JWT-SECRET]` | Shared secret to cryptographically verify user tokens |
| `SUPABASE_ANON_KEY` | Yes | `[YOUR-ANON-KEY]` | Public Supabase client key |
| `STORAGE_BACKEND` | No | `local` | Storage driver (`local` for Render disk, `supabase`) |
| `LOCAL_STORAGE_PATH` | Yes | `/app/storage` | Root path of persistent mount volume |

---

## 2. Frontend Service (Next.js 15 — Vercel)

| Variable Name | Required | Default / Example | Purpose |
| :--- | :---: | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Yes | `https://agentiq-api.onrender.com/api/v1` | Public API endpoint for browser HTTP requests |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | `https://xyz.supabase.co` | Supabase gateway for browser client auth |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | `[YOUR-ANON-KEY]` | Public anonymous key for Supabase client SDK |
| `NODE_ENV` | Automatic | `production` | Set by Vercel; disables demo auth endpoints |

---

## 3. GitHub Actions CI/CD Pipeline

The GitHub Actions workflow runs inside an isolated container with ephemeral SQLite databases and dummy JWT keys. No production secrets are required in GitHub Secrets for routine CI verification.
