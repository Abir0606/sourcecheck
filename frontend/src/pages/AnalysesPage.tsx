import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/endpoints";
import type { AnalysisJob } from "../api/types";
import { useWorkspaceContext } from "../hooks/useWorkspaceContext";
import { EmptyState, ErrorNotice } from "../components/States";
import { StatusBadge } from "../components/StatusBadge";
import { formatDateTime } from "../lib/format";

function analysisTone(status: AnalysisJob["status"]) {
  switch (status) {
    case "succeeded":
      return "positive" as const;
    case "running":
    case "queued":
      return "info" as const;
    case "failed":
      return "danger" as const;
    default:
      return "neutral" as const;
  }
}

function StartAnalysisForm() {
  const { workspace, canWrite } = useWorkspaceContext();
  const queryClient = useQueryClient();
  const [targetId, setTargetId] = useState("");

  const { data: targets } = useQuery({
    queryKey: ["documents", workspace.id, "target"],
    queryFn: () => api.documents(workspace.id, "target"),
  });
  const { data: sources } = useQuery({
    queryKey: ["documents", workspace.id, "source"],
    queryFn: () => api.documents(workspace.id, "source"),
  });

  const readyTargets = useMemo(
    () => (targets ?? []).filter((d) => d.status === "ready"),
    [targets],
  );
  const readySources = useMemo(
    () => (sources ?? []).filter((d) => d.status === "ready"),
    [sources],
  );

  const mutation = useMutation({
    mutationFn: () =>
      api.startAnalysis(workspace.id, targetId, crypto.randomUUID()),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["analyses", workspace.id] });
    },
  });

  if (!canWrite) return <p className="muted">You have read-only access to this workspace.</p>;

  const disabled = !targetId || readySources.length === 0 || mutation.isPending;

  return (
    <section className="card" aria-labelledby="start-analysis">
      <h2 id="start-analysis">Run a source check</h2>
      <p className="muted">
        Choose a processed target document. Every claim in it is checked against your processed source
        documents only.
      </p>
      <div className="field">
        <label htmlFor="target-select">Target document</label>
        <select
          id="target-select"
          value={targetId}
          onChange={(e) => setTargetId(e.target.value)}
        >
          <option value="">Select a target document…</option>
          {readyTargets.map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.original_filename}
            </option>
          ))}
        </select>
      </div>

      {readySources.length === 0 ? (
        <p className="notice notice--warning" role="status">
          Upload and process at least one source document before running a check.
        </p>
      ) : (
        <p className="muted small">{readySources.length} source document(s) available.</p>
      )}

      {targets && targets.length > 0 && readyTargets.length === 0 ? (
        <p className="muted small">
          Target documents are still being processed. This page updates automatically.
        </p>
      ) : null}

      <button
        type="button"
        className="button button--primary"
        disabled={disabled}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? "Starting…" : "Start analysis"}
      </button>

      {mutation.error ? <ErrorNotice message="Could not start the analysis." /> : null}
    </section>
  );
}

function AnalysisRow({ job }: { job: AnalysisJob }) {
  const { workspace, canWrite } = useWorkspaceContext();
  const queryClient = useQueryClient();
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["analyses", workspace.id] });

  const cancelMutation = useMutation({
    mutationFn: () => api.cancelAnalysis(workspace.id, job.id),
    onSuccess: invalidate,
  });
  const retryMutation = useMutation({
    mutationFn: () => api.retryAnalysis(workspace.id, job.id),
    onSuccess: invalidate,
  });

  return (
    <li className="doc-row">
      <div className="doc-row__main">
        <div>
          <strong>{job.target_filename}</strong>
          <div className="muted small">
            Started {formatDateTime(job.created_at)} · {job.processed_claims}/{job.total_claims || "?"} claim(s)
          </div>
        </div>
        <StatusBadge tone={analysisTone(job.status)}>{job.status_label}</StatusBadge>
      </div>

      {job.status === "running" || job.status === "queued" ? (
        <div className="progress" role="status" aria-live="polite">
          <div className="progress__bar" style={{ width: `${job.progress}%` }} />
          <span className="progress__label">
            {job.stage_label} — {job.progress}%
          </span>
        </div>
      ) : null}

      {job.error_message ? (
        <p className="notice notice--danger small" role="alert">
          {job.error_message} {job.error_code ? `(${job.error_code})` : ""}
        </p>
      ) : null}

      <div className="doc-row__actions">
        {job.status === "succeeded" ? (
          <Link className="button button--primary" to={`analyses/${job.id}`}>
            View findings
          </Link>
        ) : null}
        {canWrite && (job.status === "running" || job.status === "queued") ? (
          <button
            type="button"
            className="button button--ghost"
            onClick={() => cancelMutation.mutate()}
            disabled={cancelMutation.isPending}
          >
            Cancel
          </button>
        ) : null}
        {canWrite && job.status === "failed" ? (
          <button
            type="button"
            className="button button--ghost"
            onClick={() => retryMutation.mutate()}
            disabled={retryMutation.isPending}
          >
            {retryMutation.isPending ? "Retrying…" : "Retry"}
          </button>
        ) : null}
      </div>
    </li>
  );
}

export function AnalysesPage() {
  const { workspace } = useWorkspaceContext();
  const { data, isLoading, error } = useQuery({
    queryKey: ["analyses", workspace.id],
    queryFn: () => api.analyses(workspace.id),
    refetchInterval: (query) =>
      query.state.data?.some((job) => job.status === "running" || job.status === "queued")
        ? 2500
        : false,
  });

  return (
    <>
      <StartAnalysisForm />

      <section aria-labelledby="analysis-history">
        <h2 id="analysis-history">Analyses</h2>
        {isLoading ? <p className="muted">Loading…</p> : null}
        {error ? <ErrorNotice message="Could not load analyses." /> : null}
        {data && data.length === 0 ? (
          <EmptyState title="No analyses yet">Run your first source check above.</EmptyState>
        ) : null}
        {data && data.length > 0 ? (
          <ul className="stack">
            {data.map((job) => (
              <AnalysisRow key={job.id} job={job} />
            ))}
          </ul>
        ) : null}
      </section>
    </>
  );
}
