export type FindingSeverity = "low" | "medium" | "high" | "critical";

export type FindingCategory =
  | "missing_value"
  | "outlier"
  | "type_mismatch"
  | "duplicate"
  | "format_inconsistency"
  | "business_rule_violation";

export type FindingActionType = "drop_row" | "impute" | "replace" | "transform" | "ignore";

export interface WorkspaceMembership {
  workspace_id: string;
  workspace_name: string;
  role: "admin" | "reviewer" | "viewer";
}

export interface UserResponse {
  id: string;
  email: string;
  full_name?: string | null;
  workspaces: WorkspaceMembership[];
  created_at: string;
}

export interface ProjectResponse {
  id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: ProjectResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface UploadResponse {
  id: string;
  project_id: string;
  workspace_id: string;
  filename: string;
  file_size_bytes: number;
  mime_type: string;
  file_hash: string;
  created_at: string;
}

export interface RunProgress {
  current_stage?: "reading" | "detecting" | "grouping" | "explaining" | "summarizing" | null;
  stage_percent: number;
  total_percent: number;
  message?: string | null;
}

export interface RunCreate {
  project_id: string;
  upload_id: string;
  config?: Record<string, unknown>;
}

export interface RunResponse {
  id: string;
  project_id: string;
  upload_id: string;
  status: "queued" | "processing" | "completed" | "failed" | "cancelled";
  stage?: string | null;
  progress: RunProgress;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface RunSummaryResponse {
  run_id: string;
  total_rows: number;
  total_columns: number;
  dirty_rows: number;
  clean_rows: number;
  total_findings: number;
  findings_by_severity: Record<string, number>;
  findings_by_category: Record<string, number>;
  estimated_quality_score: number;
}

export interface SuggestedAction {
  action_type: FindingActionType;
  parameters: Record<string, unknown>;
  rationale?: string | null;
}

export interface FindingResponse {
  id: string;
  run_id: string;
  row_index?: number | null;
  column_name?: string | null;
  category: FindingCategory;
  severity: FindingSeverity;
  description: string;
  affected_value?: string | null;
  suggested_action?: SuggestedAction | null;
  is_resolved: boolean;
  issue_title?: string | null;
  affected_row_count: number;
  affected_row_indices: number[];
  confidence: number;
  risk_tier: number;
  impact_estimate: number;
  sample_before: Array<{ row: number; value: string }>;
  sample_after: Array<{ row: number; value: string }>;
  detection_rule?: string | null;
  created_at: string;
}

export interface FindingListResponse {
  items: FindingResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface FindingDecisionCreate {
  action_type: FindingActionType;
  custom_parameters?: Record<string, unknown>;
  notes?: string;
}

export interface FindingDecisionResponse {
  id: string;
  finding_id: string;
  run_id: string;
  user_id: string;
  action_type: string;
  parameters?: Record<string, unknown> | null;
  status: string;
  decided_at: string;
}

export interface DecisionUndoResponse {
  decision_id: string;
  status: string;
  undone_at: string;
  message: string;
}

export interface AuditEventResponse {
  id: string;
  run_id: string;
  user_id?: string | null;
  action: string;
  details?: Record<string, unknown> | null;
  timestamp: string;
}

export interface RunAuditResponse {
  run_id: string;
  events: AuditEventResponse[];
  total: number;
}

export interface ColumnDiff {
  column_name: string;
  original_nulls: number;
  cleaned_nulls: number;
  changes_count: number;
}

export interface RunCompareResponse {
  run_id: string;
  original_rows_count: number;
  cleaned_rows_count: number;
  columns_diff: ColumnDiff[];
  preview_original: Array<Record<string, unknown>>;
  preview_cleaned: Array<Record<string, unknown>>;
}

export type ExportFormat = "csv" | "parquet" | "excel";

export interface RunExportCreate {
  format: ExportFormat;
  include_cleaned_only?: boolean;
}

export interface RunExportResponse {
  id: string;
  run_id: string;
  format: ExportFormat;
  file_size_bytes: number;
  download_url: string;
  expires_at: string;
  created_at: string;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ErrorResponse {
  error: ApiErrorDetail;
}
