import {
  FindingDecisionCreate,
  FindingDecisionResponse,
  FindingListResponse,
  ProjectCreate,
  ProjectListResponse,
  ProjectResponse,
  DecisionUndoResponse,
  RunAuditResponse,
  RunCompareResponse,
  RunCreate,
  RunResponse,
  RunSummaryResponse,
  UploadResponse,
  UserResponse,
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ApiError";
  }
}

class ApiClient {
  private token: string | null = null;
  private workspaceId: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("agentiq_jwt_token");
      this.workspaceId = localStorage.getItem("agentiq_active_workspace_id");
    }
  }

  setSession(token: string | null, workspaceId: string | null) {
    this.token = token;
    this.workspaceId = workspaceId;
    if (typeof window !== "undefined") {
      if (token) localStorage.setItem("agentiq_jwt_token", token);
      else localStorage.removeItem("agentiq_jwt_token");

      if (workspaceId) localStorage.setItem("agentiq_active_workspace_id", workspaceId);
      else localStorage.removeItem("agentiq_active_workspace_id");
    }
  }

  getToken(): string | null {
    return this.token;
  }

  getWorkspaceId(): string | null {
    return this.workspaceId;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    customHeaders: Record<string, string> = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: Record<string, string> = {
      "Bypass-Tunnel-Reminder": "true",
      ...customHeaders,
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    if (this.workspaceId && !headers["X-Workspace-ID"]) {
      headers["X-Workspace-ID"] = this.workspaceId;
    }

    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let code = "UNKNOWN_ERROR";
      let message = `API request failed with status ${res.status}`;
      let details: Record<string, unknown> | undefined;

      try {
        const errorJson = await res.json();
        if (errorJson.error) {
          code = errorJson.error.code || code;
          message = errorJson.error.message || message;
          details = errorJson.error.details;
        } else if (errorJson.detail) {
          message = typeof errorJson.detail === "string" ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Fallback to text message
        const text = await res.text();
        if (text) message = text;
      }

      throw new ApiError(res.status, code, message, details);
    }

    return res.json() as Promise<T>;
  }

  // Auth endpoints
  readonly auth = {
    getMe: () => this.request<UserResponse>("/auth/me"),
  };

  // Projects endpoints
  readonly projects = {
    list: (params?: { limit?: number; offset?: number }) => {
      const q = new URLSearchParams();
      if (params?.limit) q.set("limit", String(params.limit));
      if (params?.offset) q.set("offset", String(params.offset));
      return this.request<ProjectListResponse>(`/projects?${q.toString()}`);
    },
    create: (payload: ProjectCreate) =>
      this.request<ProjectResponse>("/projects", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  };

  // Uploads endpoints
  readonly uploads = {
    uploadFile: (file: File, projectId: string) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("project_id", projectId);
      return this.request<UploadResponse>("/uploads", {
        method: "POST",
        body: formData,
      });
    },
  };

  // Runs endpoints
  readonly runs = {
    create: (payload: RunCreate, sync = true) =>
      this.request<RunResponse>(`/runs?sync=${sync}`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    get: (runId: string) => this.request<RunResponse>(`/runs/${runId}`),
    getSummary: (runId: string) => this.request<RunSummaryResponse>(`/runs/${runId}/summary`),
    getFindings: (
      runId: string,
      params?: {
        category?: string;
        severity?: string;
        risk_tier?: number;
        limit?: number;
        offset?: number;
      }
    ) => {
      const q = new URLSearchParams();
      if (params?.category) q.set("category", params.category);
      if (params?.severity) q.set("severity", params.severity);
      if (params?.risk_tier !== undefined) q.set("risk_tier", String(params.risk_tier));
      if (params?.limit) q.set("limit", String(params.limit));
      if (params?.offset) q.set("offset", String(params.offset));
      return this.request<FindingListResponse>(`/runs/${runId}/findings?${q.toString()}`);
    },
    getComparison: (runId: string) => this.request<RunCompareResponse>(`/runs/${runId}/compare`),
    getAudit: (runId: string) => this.request<RunAuditResponse>(`/runs/${runId}/audit`),
    createExport: (runId: string, format: "csv" | "parquet" | "excel" = "csv") =>
      this.request<import("@/types/api").RunExportResponse>(`/runs/${runId}/exports`, {
        method: "POST",
        body: JSON.stringify({ format }),
      }),
  };

  // Findings & Decisions
  readonly findings = {
    submitDecision: (findingId: string, payload: FindingDecisionCreate) =>
      this.request<FindingDecisionResponse>(`/findings/${findingId}/decisions`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  };

  readonly decisions = {
    undo: (decisionId: string) =>
      this.request<DecisionUndoResponse>(`/decisions/${decisionId}/undo`, {
        method: "POST",
      }),
  };
}

export const apiClient = new ApiClient();
