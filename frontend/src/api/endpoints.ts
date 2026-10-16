import { request, requestBlob } from "./client";
import type {
  AnalysisJob,
  DeletionRequest,
  Document,
  DocumentRole,
  EnumsPayload,
  ExportJob,
  Finding,
  FindingsResponse,
  PrivacyOverview,
  ReviewState,
  Session,
  Workspace,
  WorkspaceRole,
  WritingSuggestion,
} from "./types";

const ws = (id: string) => `/api/v1/workspaces/${id}`;

export const api = {
  session: () => request<Session>("/api/v1/auth/session"),
  login: (email: string, password: string) =>
    request<Session>("/api/v1/auth/login", { method: "POST", body: { email, password } }),
  register: (email: string, password: string) =>
    request<Session>("/api/v1/auth/register", { method: "POST", body: { email, password } }),
  logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),
  enums: () => request<EnumsPayload>("/api/v1/meta/enums"),

  workspaces: () => request<Workspace[]>("/api/v1/workspaces"),
  createWorkspace: (name: string) =>
    request<Workspace>("/api/v1/workspaces", { method: "POST", body: { name } }),
  workspaceSettings: (id: string) => request<Workspace>(`${ws(id)}/settings`),
  updateWorkspaceSettings: (id: string, data: Partial<Pick<Workspace, "name" | "data_region" | "retention_days">>) =>
    request<Workspace>(`${ws(id)}/settings`, { method: "PATCH", body: data }),

  documents: (id: string, role?: DocumentRole) =>
    request<Document[]>(`${ws(id)}/documents${role ? `?role=${role}` : ""}`),
  uploadDocument: (id: string, role: DocumentRole, file: File) => {
    const form = new FormData();
    form.append("role", role);
    form.append("file", file);
    return request<Document>(`${ws(id)}/documents`, { method: "POST", body: form, isForm: true });
  },
  deleteDocument: (id: string, documentId: string) =>
    request<void>(`${ws(id)}/documents/${documentId}`, { method: "DELETE" }),
  reprocessDocument: (id: string, documentId: string) =>
    request<Document>(`${ws(id)}/documents/${documentId}/reprocess`, { method: "POST" }),

  analyses: (id: string) => request<AnalysisJob[]>(`${ws(id)}/analyses`),
  analysis: (id: string, jobId: string) => request<AnalysisJob>(`${ws(id)}/analyses/${jobId}`),
  startAnalysis: (id: string, targetDocumentId: string, idempotencyKey: string) =>
    request<AnalysisJob>(`${ws(id)}/analyses`, {
      method: "POST",
      body: { target_document_id: targetDocumentId, idempotency_key: idempotencyKey },
    }),
  cancelAnalysis: (id: string, jobId: string) =>
    request<AnalysisJob>(`${ws(id)}/analyses/${jobId}/cancel`, { method: "POST" }),
  retryAnalysis: (id: string, jobId: string) =>
    request<AnalysisJob>(`${ws(id)}/analyses/${jobId}/retry`, { method: "POST" }),
  findings: (id: string, jobId: string, query: Record<string, string> = {}) => {
    const params = new URLSearchParams(query).toString();
    return request<FindingsResponse>(`${ws(id)}/analyses/${jobId}/findings${params ? `?${params}` : ""}`);
  },
  writing: (id: string, jobId: string) =>
    request<WritingSuggestion[]>(`${ws(id)}/analyses/${jobId}/writing`),
  reviewFinding: (id: string, findingId: string, reviewState: ReviewState, reviewNote: string) =>
    request<Finding>(`${ws(id)}/findings/${findingId}`, {
      method: "PATCH",
      body: { review_state: reviewState, review_note: reviewNote },
    }),
  reportUrl: (id: string, jobId: string, kind: "json" | "csv") =>
    `/api/v1/workspaces/${id}/analyses/${jobId}/report?export=${kind}`,
  reportBlob: (id: string, jobId: string, kind: "json" | "csv") =>
    requestBlob(`/api/v1/workspaces/${id}/analyses/${jobId}/report?export=${kind}`),

  privacy: (id: string) => request<PrivacyOverview>(`${ws(id)}/privacy`),
  exports: (id: string) => request<ExportJob[]>(`${ws(id)}/exports`),
  createExport: (id: string) => request<ExportJob>(`${ws(id)}/exports`, { method: "POST" }),
  exportDownloadUrl: (id: string, exportId: string) => `${ws(id)}/exports/${exportId}/download`,
  exportBlob: (id: string, exportId: string) => requestBlob(`${ws(id)}/exports/${exportId}/download`),
  deletions: (id: string) => request<DeletionRequest[]>(`${ws(id)}/deletion-requests`),
  createDeletion: (id: string, scope: string) =>
    request<DeletionRequest>(`${ws(id)}/deletion-requests`, { method: "POST", body: { scope } }),
  updateMember: (
    id: string,
    userId: string,
    role: WorkspaceRole,
  ) =>
    request<unknown>(`${ws(id)}/members`, { method: "POST", body: { user: userId, role } }),
};
