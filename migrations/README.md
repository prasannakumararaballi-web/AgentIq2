# Database Migrations

This directory hosts Alembic database migration scripts for AgentIQ v2 (Supabase PostgreSQL).

In Phase 2, Alembic will be initialized with asyncpg/psycopg to manage schemas for:
- Workspaces and Workspace Memberships (RBAC)
- Projects
- File Upload metadata
- Execution Runs and Stages
- Anomaly Findings
- Human Remediation Decisions
- Audit Log events
- Export jobs

