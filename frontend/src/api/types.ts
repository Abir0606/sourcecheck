export type FindingStatus =
  | "supported"
  | "partially_supported"
  | "unsupported_by_sources"
  | "conflicts_with_sources"
  | "citation_issue";

export type DocumentRole = "target" | "source";

export type DocumentStatus =
  | "uploaded"
  | "validating"
  | "extracting"
  | "ocr"
  | "chunking"
  | "embedding"
  | "ready"
  | "failed"
  | "unsupported"
  | "empty";

export type AnalysisStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export type ReviewState = "unreviewed" | "accepted" | "corrected" | "dismissed";

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
  is_staff: boolean;
}

export interface Session {
  authenticated: boolean;
  user: User | null;
  csrfToken: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  data_region: string;
  retention_days: number;
  is_archived: boolean;
  role: WorkspaceRole | null;
  member_count: number;
  created_at: string;
}

export type WorkspaceRole = "owner" | "admin" | "editor" | "viewer";

export interface Document {
  id: string;
  role: DocumentRole;
  role_label: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  status: DocumentStatus;
  status_label: string;
  stage_detail: string;
  page_count: number;
  char_count: number;
  language: string;
  ocr_used: boolean;
  error_code: string;
  error_message: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface TargetPassage {
  id: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  chunk_index: number;
  text: string;
}

export interface Evidence {
  id: number;
  source_document_id: string;
  filename: string;
  page_number: number | null;
  rank: number;
  score: number;
  snippet: string;
  is_validated: boolean;
}

export interface Finding {
  id: string;
  analysis_job_id: string;
  status: FindingStatus;
  status_label: string;
  status_description: string;
  claim_text: string;
  explanation: string;
  confidence: number;
  needs_human_review: boolean;
  model_name: string;
  model_version: string;
  review_state: ReviewState;
  review_state_label: string;
  review_note: string;
  target_passage: TargetPassage;
  evidence: Evidence[];
  created_at: string;
}

export interface AnalysisJob {
  id: string;
  target_document_id: string;
  target_filename: string;
  status: AnalysisStatus;
  status_label: string;
  stage: string;
  stage_label: string;
  progress: number;
  total_claims: number;
  processed_claims: number;
  error_code: string;
  error_message: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface FindingsSummary {
  total: number;
  by_status: Record<string, number>;
  needs_human_review: number;
}

export interface FindingsResponse {
  results?: Finding[];
  summary: FindingsSummary;
  count?: number;
  next?: string | null;
  previous?: string | null;
}

export interface WritingSuggestion {
  id: string;
  category: string;
  category_label: string;
  severity: string;
  message: string;
  suggestion: string;
  passage_ref: { page_number: number | null; chunk_index: number } | null;
}

export interface ExportJob {
  id: string;
  status: string;
  status_label: string;
  size_bytes: number;
  is_expired: boolean;
  error_message: string;
  created_at: string;
  completed_at: string | null;
  expires_at: string | null;
}

export interface DeletionRequest {
  id: string;
  scope: string;
  status: string;
  status_label: string;
  result: Record<string, number>;
  error_message: string;
  created_at: string;
  completed_at: string | null;
}

export interface PrivacyOverview {
  workspace: {
    id: string;
    name: string;
    data_region: string;
    retention_days: number;
  };
  data_inventory: { documents: number; analyses: number; findings: number };
  notes: string;
}

export interface EnumsPayload {
  finding_status: { value: FindingStatus; label: string }[];
  finding_status_descriptions: Record<string, string>;
  document_role: { value: DocumentRole; label: string }[];
  document_status: { value: DocumentStatus; label: string }[];
  workspace_role: { value: WorkspaceRole; label: string }[];
  analysis_status: { value: AnalysisStatus; label: string }[];
  review_state: { value: ReviewState; label: string }[];
  writing_category: { value: string; label: string }[];
}

export interface ApiError {
  code: string;
  message: string;
  detail?: unknown;
}
