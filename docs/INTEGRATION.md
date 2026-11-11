# AgentIQ v2 — Frontend Integration Guide

This guide is for the frontend team building with **Next.js 16**, **React 19**, and **TypeScript**. You do **not** need to install or import any Python code to integrate with AgentIQ v2. All contracts are exposed through standard OpenAPI 3.1 definitions.

---

## 1. Quick Integration Parameters

- **Backend Base URL:** `http://localhost:8000`
- **API Prefix:** `/api/v1`
- **CORS Allowed Origin:** `http://localhost:3000`
- **Interactive Swagger UI:** `http://localhost:8000/docs`
- **OpenAPI 3.1 Spec (JSON):** `http://localhost:8000/openapi.json` or local [`contracts/openapi.json`](../contracts/openapi.json)
- **OpenAPI Spec (YAML):** [`contracts/api-spec.yaml`](../contracts/api-spec.yaml)

---

## 2. Authentication & Workspace Context

### 2.1 Bearer Token Header
AgentIQ uses **Supabase Auth**. After signing in via the Supabase client in Next.js, forward the session access token on every API request:

```typescript
const headers = {
  'Authorization': `Bearer ${session.access_token}`,
  'X-Workspace-ID': activeWorkspaceId,
  'Content-Type': 'application/json',
};
```

### 2.2 Server-Side Authorization & Roles
The backend enforces role-based access control (RBAC). The user's role is resolved directly from their verified Supabase session:
- **`admin`**: Full access (project creation, settings, run triggers, reviews, exports).
- **`reviewer`**: Can upload datasets, trigger runs, submit finding decisions, and request exports.
- **`viewer`**: Read-only access (view summary, progress, findings, audit trail, diffs).

If a user lacks permission for an action, the backend responds with HTTP 403:
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Insufficient permissions. Required one of: ['admin', 'reviewer'].",
    "details": null
  }
}
```

---

## 3. TypeScript Client Generation

We recommend generating fully typed TypeScript clients directly from `contracts/openapi.json` using [`openapi-typescript`](https://github.com/openapi-ts/openapi-typescript) or [`hey-api/openapi-ts`](https://heyapi.vercel.app/).

### Option A: `openapi-typescript` (Recommended for Fetch/React Query)

1. In your Next.js application, install the CLI:
   ```bash
   npm install -D openapi-typescript
   ```

2. Add a generation script to `package.json`:
   ```json
   {
     "scripts": {
       "generate:api": "openapi-typescript ../contracts/openapi.json -o ./src/lib/api/schema.d.ts"
     }
   }
   ```
   *(Or fetch directly from the running dev backend: `openapi-typescript http://localhost:8000/openapi.json -o ./src/lib/api/schema.d.ts`)*

3. Using typed Fetch with `openapi-fetch`:
   ```typescript
   import createClient from 'openapi-fetch';
   import type { paths } from '@/lib/api/schema';

   export const api = createClient<paths>({
     baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
   });

   // Type-safe call
   const { data, error } = await api.GET('/api/v1/runs/{run_id}', {
     params: {
       path: { run_id: '44444444-4444-4444-4444-444444444444' },
       header: { 'X-Workspace-ID': activeWorkspaceId },
     },
     headers: {
       Authorization: `Bearer ${supabaseAccessToken}`,
     },
   });
   ```

---

## 4. Polling Pattern for Asynchronous Runs

When a dataset cleaning run is triggered via `POST /api/v1/runs`, the backend processes the dataset asynchronously across multiple stages:
`reading` → `detecting` → `grouping` → `explaining` → `summarizing`.

### Recommended Polling Pattern (Every 2 Seconds)
Use TanStack Query (React Query) or SWR:

```typescript
import { useQuery } from '@tanstack/react-query';

export function useRunProgress(runId: string, workspaceId: string, token: string) {
  return useQuery({
    queryKey: ['run', runId],
    queryFn: async () => {
      const res = await fetch(`http://localhost:8000/api/v1/runs/${runId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-Workspace-ID': workspaceId,
        },
      });
      if (!res.ok) throw new Error('Failed to fetch run progress');
      return res.json();
    },
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Stop polling once the run has completed, failed, or been cancelled
      if (status === 'completed' || status === 'failed' || status === 'cancelled') {
        return false;
      }
      return 2000; // Poll every 2 seconds during 'queued' and 'processing'
    },
  });
}
```

---

## 5. Dataset Upload Workflow (multipart/form-data)

Uploads must be sent using `FormData`. Note that the browser will automatically populate the `boundary` header—**do not manually set `Content-Type: multipart/form-data`**:

```typescript
export async function uploadDataset(
  file: File,
  projectId: string,
  workspaceId: string,
  token: string
) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('project_id', projectId);

  const response = await fetch('http://localhost:8000/api/v1/uploads', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-Workspace-ID': workspaceId,
      // Do NOT set Content-Type header; let browser set multipart boundary
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error.message || 'Upload failed');
  }

  return response.json();
}
```

---

## 6. Reviewer Decision Workflow

1. Retrieve detected anomalies:
   `GET /api/v1/runs/{run_id}/findings?limit=50&offset=0`
2. Submit human decision for finding:
   `POST /api/v1/findings/{finding_id}/decisions`
   ```json
   {
     "action_type": "replace",
     "custom_parameters": { "replacement": "valid@email.com" },
     "notes": "Fixed by reviewer"
   }
   ```
3. To undo a decision:
   `POST /api/v1/decisions/{decision_id}/undo`
4. Inspect diff before export:
   `GET /api/v1/runs/{run_id}/compare`
5. Generate downloadable artifact:
   `POST /api/v1/runs/{run_id}/exports` with `{ "format": "parquet" }`
