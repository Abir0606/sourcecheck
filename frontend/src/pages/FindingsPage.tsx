import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/endpoints";
import type { Finding, FindingStatus, ReviewState } from "../api/types";
import { useWorkspaceContext } from "../hooks/useWorkspaceContext";
import { EmptyState, ErrorNotice } from "../components/States";
import { StatusBadge } from "../components/StatusBadge";
import { confidenceLabel, findingTone } from "../lib/format";

const STATUS_ORDER: FindingStatus[] = [
  "supported",
  "partially_supported",
  "unsupported_by_sources",
  "conflicts_with_sources",
  "citation_issue",
];

function ReportButtons({ jobId }: { jobId: string }) {
  const { workspace } = useWorkspaceContext();
  const [busy, setBusy] = useState<string | null>(null);

  async function download(kind: "json" | "csv") {
    setBusy(kind);
    try {
      const blob = await api.reportBlob(workspace.id, jobId, kind);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `sourcecheck-report-${jobId}.${kind}`;
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="report-actions">
      <button type="button" className="button button--secondary" onClick={() => download("csv")} disabled={busy !== null}>
        {busy === "csv" ? "Preparing…" : "Export CSV"}
      </button>
      <button type="button" className="button button--secondary" onClick={() => download("json")} disabled={busy !== null}>
        {busy === "json" ? "Preparing…" : "Export JSON"}
      </button>
    </div>
  );
}

function EvidencePanel({ finding }: { finding: Finding }) {
  const { workspace, canWrite } = useWorkspaceContext();
  const queryClient = useQueryClient();
  const [note, setNote] = useState(finding.review_note ?? "");

  const reviewMutation = useMutation({
    mutationFn: ({ state }: { state: ReviewState }) =>
      api.reviewFinding(workspace.id, finding.id, state, note),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["findings", workspace.id] });
    },
  });

  return (
    <aside className="evidence-panel" aria-label="Evidence and review">
      <header className="evidence-panel__header">
        <div>
          <StatusBadge tone={findingTone(finding.status)}>{finding.status_label}</StatusBadge>
          <p className="muted small">{finding.status_description}</p>
        </div>
        <div className="confidence" title={`Confidence ${finding.confidence}`}>
          <span className={`confidence__dot confidence__dot--${confidenceLabel(finding.confidence).toLowerCase()}`} />
          {confidenceLabel(finding.confidence)} confidence ({(finding.confidence * 100).toFixed(0)}%)
        </div>
      </header>

      {finding.needs_human_review ? (
        <p className="notice notice--warning" role="status">
          This finding is marked <strong>needs human review</strong> because the evidence is uncertain.
        </p>
      ) : null}

      <div className="passage-grid">
        <section aria-label="Target passage" className="passage">
          <h4>Target document</h4>
          <p className="muted small">
            {finding.target_passage.filename}
            {finding.target_passage.page_number ? ` · page ${finding.target_passage.page_number}` : ""}
          </p>
          <blockquote>{finding.target_passage.text}</blockquote>
        </section>

        <section aria-label="Source evidence" className="passage">
          <h4>Evidence from your sources</h4>
          {finding.evidence.length === 0 ? (
            <p className="muted">No matching evidence was found in the uploaded sources.</p>
          ) : (
            <ul className="stack stack--tight">
              {finding.evidence.map((ev) => (
                <li key={ev.id} className="evidence-item">
                  <p className="muted small">
                    <span>Source: </span>
                    {ev.filename}
                    {ev.page_number ? ` · page ${ev.page_number}` : ""} · score {ev.score.toFixed(2)}
                    {ev.is_validated ? "" : " · unverified"}
                  </p>
                  <blockquote>{ev.snippet}</blockquote>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <p className="explanation">
        <strong>Explanation:</strong> {finding.explanation}
      </p>

      {canWrite ? (
        <section aria-label="Human review" className="review">
          <h4>Human review</h4>
          <div className="field">
            <label htmlFor={`note-${finding.id}`}>Review note (optional)</label>
            <textarea
              id={`note-${finding.id}`}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
            />
          </div>
          <div className="review__actions">
            {(["accepted", "corrected", "dismissed"] as ReviewState[]).map((state) => (
              <button
                key={state}
                type="button"
                className={finding.review_state === state ? "button button--primary" : "button button--secondary"}
                onClick={() => reviewMutation.mutate({ state })}
                disabled={reviewMutation.isPending}
              >
                {state === "accepted" ? "Accept" : state === "corrected" ? "Mark corrected" : "Dismiss"}
              </button>
            ))}
          </div>
          {finding.review_state !== "unreviewed" ? (
            <p className="muted small">Current review state: {finding.review_state_label}</p>
          ) : null}
        </section>
      ) : null}
    </aside>
  );
}

function WritingTab({ jobId }: { jobId: string }) {
  const { workspace } = useWorkspaceContext();
  const { data, isLoading } = useQuery({
    queryKey: ["writing", workspace.id, jobId],
    queryFn: () => api.writing(workspace.id, jobId),
  });
  if (isLoading) return <p className="muted">Loading writing feedback…</p>;
  if (!data || data.length === 0) {
    return <EmptyState title="No writing suggestions">No clarity, grammar or readability issues were flagged.</EmptyState>;
  }
  return (
    <ul className="stack">
      {data.map((s) => (
        <li key={s.id} className="card">
          <StatusBadge tone="info">{s.category_label}</StatusBadge>
          <p>{s.message}</p>
          {s.suggestion ? <p className="muted small">Suggestion: {s.suggestion}</p> : null}
          {s.passage_ref ? (
            <p className="muted small">
              Passage {s.passage_ref.chunk_index + 1}
              {s.passage_ref.page_number ? ` · page ${s.passage_ref.page_number}` : ""}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

export function FindingsPage() {
  const { workspaceId = "", jobId = "" } = useParams();
  const { workspace } = useWorkspaceContext();
  const [statusFilter, setStatusFilter] = useState<FindingStatus | "">("");
  const [reviewFilter, setReviewFilter] = useState<ReviewState | "">("");
  const [onlyNeedsReview, setOnlyNeedsReview] = useState(false);
  const [tab, setTab] = useState<"findings" | "writing">("findings");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const jobQuery = useQuery({
    queryKey: ["analysis", workspace.id, jobId],
    queryFn: () => api.analysis(workspace.id, jobId),
    refetchInterval: (query) =>
      query.state.data && (query.state.data.status === "running" || query.state.data.status === "queued")
        ? 2500
        : false,
  });

  const query = useMemo(() => {
    const params: Record<string, string> = {};
    if (statusFilter) params.status = statusFilter;
    if (reviewFilter) params.review_state = reviewFilter;
    if (onlyNeedsReview) params.needs_human_review = "true";
    return params;
  }, [statusFilter, reviewFilter, onlyNeedsReview]);

  const findingsQuery = useQuery({
    queryKey: ["findings", workspace.id, jobId, query],
    queryFn: () => api.findings(workspace.id, jobId, query),
    enabled: tab === "findings",
  });

  const findings = findingsQuery.data?.results ?? [];
  const summary = findingsQuery.data?.summary;
  const selected = findings.find((f) => f.id === selectedId) ?? findings[0] ?? null;

  if (jobQuery.isLoading) return <p className="muted">Loading analysis…</p>;
  if (jobQuery.error || !jobQuery.data) return <ErrorNotice message="This analysis could not be loaded." />;

  const job = jobQuery.data;

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Findings: {job.target_filename}</h1>
          <p className="muted">
            {job.status_label}
            {job.total_claims ? ` · ${job.total_claims} claim(s) checked` : ""}
          </p>
        </div>
        <ReportButtons jobId={jobId} />
      </header>

      <p className="notice notice--info" role="note">
        These results compare the target document with <strong>only the source documents you uploaded</strong>.
        "Unsupported by uploaded sources" means the statement was not found — it is not a statement that
        it is false. This is not plagiarism detection.
      </p>

      <div className="tabs" role="tablist" aria-label="Result views">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "findings"}
          className={tab === "findings" ? "tab tab--active" : "tab"}
          onClick={() => setTab("findings")}
        >
          Source check findings
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "writing"}
          className={tab === "writing" ? "tab tab--active" : "tab"}
          onClick={() => setTab("writing")}
        >
          Writing feedback
        </button>
      </div>

      {tab === "writing" ? (
        <WritingTab jobId={jobId} />
      ) : (
        <>
          <section aria-label="Summary" className="summary-bar">
            {summary ? (
              <>
                <span className="summary-chip">Total: {summary.total}</span>
                {STATUS_ORDER.map((status) => {
                  const count = summary.by_status[status] ?? 0;
                  return (
                    <button
                      key={status}
                      type="button"
                      className={statusFilter === status ? "summary-chip summary-chip--active" : "summary-chip"}
                      onClick={() => setStatusFilter(statusFilter === status ? "" : status)}
                      aria-pressed={statusFilter === status}
                    >
                      {status.replace(/_/g, " ")}: {count}
                    </button>
                  );
                })}
                {summary.needs_human_review > 0 ? (
                  <button
                    type="button"
                    className={onlyNeedsReview ? "summary-chip summary-chip--active" : "summary-chip"}
                    onClick={() => setOnlyNeedsReview((v) => !v)}
                    aria-pressed={onlyNeedsReview}
                  >
                    Needs review: {summary.needs_human_review}
                  </button>
                ) : null}
              </>
            ) : (
              <span className="muted">Loading summary…</span>
            )}
          </section>

          <div className="filters">
            <div className="field">
              <label htmlFor="review-filter">Review state</label>
              <select id="review-filter" value={reviewFilter} onChange={(e) => setReviewFilter(e.target.value as ReviewState | "")}>
                <option value="">All</option>
                <option value="unreviewed">Needs review</option>
                <option value="accepted">Accepted</option>
                <option value="corrected">Corrected</option>
                <option value="dismissed">Dismissed</option>
              </select>
            </div>
          </div>

          {findingsQuery.isLoading ? <p className="muted">Loading findings…</p> : null}
          {findingsQuery.error ? <ErrorNotice message="Could not load findings." /> : null}

          {!findingsQuery.isLoading && findings.length === 0 ? (
            <EmptyState title="No findings match these filters">
              Try clearing the filters, or run the analysis once the documents are processed.
            </EmptyState>
          ) : null}

          {findings.length > 0 ? (
            <div className="findings-layout">
              <ol className="findings-list" aria-label="Findings">
                {findings.map((finding) => (
                  <li key={finding.id}>
                    <button
                      type="button"
                      className={selected?.id === finding.id ? "finding-item finding-item--active" : "finding-item"}
                      onClick={() => setSelectedId(finding.id)}
                      aria-current={selected?.id === finding.id}
                    >
                      <StatusBadge tone={findingTone(finding.status)}>{finding.status_label}</StatusBadge>
                      <p className="finding-item__claim">{finding.claim_text.slice(0, 140)}</p>
                      <span className="muted small">
                        {confidenceLabel(finding.confidence)} confidence
                        {finding.needs_human_review ? " · needs review" : ""}
                        {finding.evidence.length ? ` · ${finding.evidence.length} source(s)` : ""}
                      </span>
                    </button>
                  </li>
                ))}
              </ol>

              {selected ? <EvidencePanel key={selected.id} finding={selected} /> : null}
            </div>
          ) : null}
        </>
      )}

      <p className="muted small" aria-hidden="true" data-workspace={workspaceId} />
    </>
  );
}
