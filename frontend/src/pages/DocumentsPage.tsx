import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/endpoints";
import { uploadWithProgress, RequestError } from "../api/client";
import type { Document, DocumentRole } from "../api/types";
import { useWorkspaceContext } from "../hooks/useWorkspaceContext";
import { EmptyState, ErrorNotice } from "../components/States";
import { StatusBadge } from "../components/StatusBadge";
import { documentTone, formatBytes, formatDateTime, isProcessing } from "../lib/format";

const ACCEPT = ".pdf,.docx,.txt,.md,.rtf,.odt,.xlsx,.csv";

function UploadPanel({
  role,
  title,
  description,
}: {
  role: DocumentRole;
  title: string;
  description: string;
}) {
  const { workspace, canWrite } = useWorkspaceContext();
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const mutation = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("role", role);
      form.append("file", file);
      return uploadWithProgress<Document>(`/api/v1/workspaces/${workspace.id}/documents`, form, setProgress);
    },
    onSuccess: () => {
      setProgress(null);
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["documents", workspace.id] });
    },
    onError: (err) => {
      setProgress(null);
      setError(err instanceof RequestError ? err.message : "Upload failed.");
    },
  });

  function handleFiles(files: FileList | null) {
    setError(null);
    const file = files?.[0];
    if (file) mutation.mutate(file);
  }

  return (
    <section className="card" aria-labelledby={`upload-${role}`}>
      <h2 id={`upload-${role}`}>{title}</h2>
      <p className="muted">{description}</p>

      <div
        className={dragOver ? "dropzone dropzone--active" : "dropzone"}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (canWrite) handleFiles(e.dataTransfer.files);
        }}
      >
        <input
          ref={inputRef}
          id={`file-${role}`}
          type="file"
          accept={ACCEPT}
          className="visually-hidden"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={!canWrite || mutation.isPending}
        />
        <label htmlFor={`file-${role}`} className="button button--secondary">
          Choose file
        </label>
        <span className="muted">or drag and drop ({ACCEPT})</span>
        {!canWrite ? <p className="muted">You have read-only access.</p> : null}
      </div>

      {progress !== null ? (
        <div className="progress" role="status" aria-live="polite">
          <div className="progress__bar" style={{ width: `${progress}%` }} />
          <span className="progress__label">Uploading… {progress}%</span>
        </div>
      ) : null}

      {error ? <ErrorNotice message={error} /> : null}
    </section>
  );
}

function DocumentRow({ document }: { document: Document }) {
  const { workspace, canWrite } = useWorkspaceContext();
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["documents", workspace.id] });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteDocument(workspace.id, document.id),
    onSuccess: invalidate,
  });
  const reprocessMutation = useMutation({
    mutationFn: () => api.reprocessDocument(workspace.id, document.id),
    onSuccess: invalidate,
  });

  return (
    <li className="doc-row">
      <div className="doc-row__main">
        <div>
          <strong>{document.original_filename}</strong>
          <div className="muted small">
            {formatBytes(document.size_bytes)}
            {document.page_count ? ` · ${document.page_count} page(s)` : ""}
            {document.ocr_used ? " · OCR used" : ""} · added {formatDateTime(document.created_at)}
          </div>
        </div>
        <StatusBadge tone={documentTone(document.status)}>{document.status_label}</StatusBadge>
      </div>

      {document.stage_detail ? <p className="muted small">{document.stage_detail}</p> : null}
      {document.status === "failed" || document.status === "unsupported" || document.status === "empty" ? (
        <p className="notice notice--warning small" role="status">
          {document.error_message || "This document could not be processed."}
          {document.error_code ? ` (code: ${document.error_code})` : ""}
        </p>
      ) : null}

      {canWrite ? (
        <div className="doc-row__actions">
          {document.status === "failed" || document.status === "empty" ? (
            <button
              type="button"
              className="button button--ghost"
              onClick={() => reprocessMutation.mutate()}
              disabled={reprocessMutation.isPending}
            >
              {reprocessMutation.isPending ? "Retrying…" : "Retry processing"}
            </button>
          ) : null}
          {confirming ? (
            <>
              <span className="muted small">Delete this document and its data?</span>
              <button
                type="button"
                className="button button--danger"
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? "Deleting…" : "Confirm delete"}
              </button>
              <button type="button" className="button button--ghost" onClick={() => setConfirming(false)}>
                Cancel
              </button>
            </>
          ) : (
            <button type="button" className="button button--ghost" onClick={() => setConfirming(true)}>
              Delete
            </button>
          )}
        </div>
      ) : null}
    </li>
  );
}

function DocumentList({ role, title }: { role: DocumentRole; title: string }) {
  const { workspace } = useWorkspaceContext();
  const { data, isLoading, error } = useQuery({
    queryKey: ["documents", workspace.id, role],
    queryFn: () => api.documents(workspace.id, role),
    refetchInterval: (query) =>
      query.state.data?.some((doc) => isProcessing(doc.status)) ? 2000 : false,
  });

  return (
    <section aria-labelledby={`list-${role}`}>
      <h2 id={`list-${role}`}>{title}</h2>
      {isLoading ? <p className="muted">Loading…</p> : null}
      {error ? <ErrorNotice message="Could not load documents." /> : null}
      {data && data.length === 0 ? (
        <EmptyState title={`No ${role} documents yet`}>
          Upload one above to get started.
        </EmptyState>
      ) : null}
      {data && data.length > 0 ? (
        <ul className="stack">
          {data.map((doc) => (
            <DocumentRow key={doc.id} document={doc} />
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export function DocumentsPage() {
  return (
    <>
      <UploadPanel
        role="target"
        title="Target document"
        description="The document whose claims and citations you want to check. Upload one target per analysis."
      />
      <UploadPanel
        role="source"
        title="Source documents"
        description="The sources to check against. Findings are based only on these documents — never the public internet."
      />
      <DocumentList role="target" title="Your target documents" />
      <DocumentList role="source" title="Your source documents" />
    </>
  );
}
