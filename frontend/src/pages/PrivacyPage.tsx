import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/endpoints";
import type { DeletionRequest, ExportJob } from "../api/types";
import { useWorkspaceContext } from "../hooks/useWorkspaceContext";
import { EmptyState, ErrorNotice } from "../components/States";
import { StatusBadge } from "../components/StatusBadge";
import { formatBytes, formatDateTime } from "../lib/format";

function SettingsForm() {
  const { workspace, canWrite } = useWorkspaceContext();
  const queryClient = useQueryClient();
  const isAdmin = workspace.role === "owner" || workspace.role === "admin";
  const [name, setName] = useState(workspace.name);
  const [region, setRegion] = useState(workspace.data_region);
  const [retention, setRetention] = useState(workspace.retention_days);

  const mutation = useMutation({
    mutationFn: () => api.updateWorkspaceSettings(workspace.id, {
      name,
      data_region: region,
      retention_days: Number(retention),
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workspaces"] }),
  });

  return (
    <section className="card" aria-labelledby="retention-settings">
      <h2 id="retention-settings">Retention &amp; region</h2>
      <p className="muted">
        These are configuration values. The actual retention period, lawful basis and transfer
        mechanism are decisions for your controller/DPO — see the project's privacy documentation.
      </p>
      <div className="field">
        <label htmlFor="ws-name-edit">Workspace name</label>
        <input id="ws-name-edit" value={name} onChange={(e) => setName(e.target.value)} disabled={!isAdmin} />
      </div>
      <div className="field">
        <label htmlFor="ws-region">Data region label</label>
        <input
          id="ws-region"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          disabled={!isAdmin}
          placeholder="e.g. uksouth"
        />
      </div>
      <div className="field">
        <label htmlFor="ws-retention">Retention (days; 0 = until deleted)</label>
        <input
          id="ws-retention"
          type="number"
          min={0}
          value={retention}
          onChange={(e) => setRetention(Number(e.target.value))}
          disabled={!isAdmin}
        />
      </div>
      {!isAdmin ? <p className="muted small">Only owners and admins can change these settings.</p> : null}
      <button
        type="button"
        className="button button--primary"
        disabled={!isAdmin || !canWrite || mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? "Saving…" : "Save settings"}
      </button>
      {mutation.isSuccess ? <p className="muted small" role="status">Saved.</p> : null}
      {mutation.error ? <ErrorNotice message="Could not save settings." /> : null}
    </section>
  );
}

function Inventory() {
  const { workspace } = useWorkspaceContext();
  const { data, isLoading } = useQuery({
    queryKey: ["privacy", workspace.id],
    queryFn: () => api.privacy(workspace.id),
  });
  if (isLoading || !data) return <p className="muted">Loading inventory…</p>;
  return (
    <section className="card" aria-labelledby="inventory">
      <h2 id="inventory">Data inventory</h2>
      <dl className="stat-grid">
        <div>
          <dt>Documents</dt>
          <dd>{data.data_inventory.documents}</dd>
        </div>
        <div>
          <dt>Analyses</dt>
          <dd>{data.data_inventory.analyses}</dd>
        </div>
        <div>
          <dt>Findings</dt>
          <dd>{data.data_inventory.findings}</dd>
        </div>
      </dl>
      <p className="muted small">{data.notes}</p>
    </section>
  );
}

function ExportSection() {
  const { workspace, canWrite } = useWorkspaceContext();
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ["exports", workspace.id],
    queryFn: () => api.exports(workspace.id),
    refetchInterval: (q) =>
      q.state.data?.some((e) => e.status === "pending" || e.status === "running") ? 2000 : false,
  });

  const createMutation = useMutation({
    mutationFn: () => api.createExport(workspace.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["exports", workspace.id] }),
  });

  async function download(exp: ExportJob) {
    const blob = await api.exportBlob(workspace.id, exp.id);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `export-${exp.id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="card" aria-labelledby="export-section">
      <h2 id="export-section">Export your data</h2>
      <p className="muted">
        Produces a JSON bundle covering original files' text, extracted pages, and analysis results.
        Exports expire after 24 hours.
      </p>
      <button
        type="button"
        className="button button--secondary"
        disabled={!canWrite || createMutation.isPending}
        onClick={() => createMutation.mutate()}
      >
        {createMutation.isPending ? "Requesting…" : "Request export"}
      </button>

      {data && data.length > 0 ? (
        <ul className="stack stack--tight" style={{ marginTop: "1rem" }}>
          {data.map((exp) => (
            <li key={exp.id} className="inline-between">
              <span className="muted small">
                {formatDateTime(exp.created_at)} · {formatBytes(exp.size_bytes)}
              </span>
              <span className="inline-actions">
                <StatusBadge tone={exp.status === "completed" ? "positive" : exp.status === "failed" ? "danger" : "info"}>
                  {exp.status_label}
                </StatusBadge>
                {exp.status === "completed" && !exp.is_expired ? (
                  <button type="button" className="button button--ghost" onClick={() => download(exp)}>
                    Download
                  </button>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function DeletionSection() {
  const { workspace } = useWorkspaceContext();
  const queryClient = useQueryClient();
  const isAdmin = workspace.role === "owner" || workspace.role === "admin";
  const [scope, setScope] = useState("documents");

  const { data } = useQuery({
    queryKey: ["deletions", workspace.id],
    queryFn: () => api.deletions(workspace.id),
  });

  const mutation = useMutation({
    mutationFn: () => api.createDeletion(workspace.id, scope),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["deletions", workspace.id] }),
  });

  const labels: Record<string, string> = {
    documents: "Documents and extracted data",
    analysis: "Analysis results only",
    workspace: "Entire workspace data",
  };

  return (
    <section className="card" aria-labelledby="deletion-section">
      <h2 id="deletion-section">Delete data</h2>
      <p className="muted">
        Deletion removes original files, extracted text, searchable passages and analysis results for
        the chosen scope. This cannot be undone.
      </p>
      <div className="field">
        <label htmlFor="deletion-scope">What to delete</label>
        <select id="deletion-scope" value={scope} onChange={(e) => setScope(e.target.value)} disabled={!isAdmin}>
          {Object.entries(labels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <button
        type="button"
        className="button button--danger"
        disabled={!isAdmin || mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? "Requesting…" : "Request deletion"}
      </button>
      {!isAdmin ? <p className="muted small">Only owners and admins can request deletion.</p> : null}

      {data && data.length > 0 ? (
        <ul className="stack stack--tight" style={{ marginTop: "1rem" }}>
          {data.map((req: DeletionRequest) => (
            <li key={req.id} className="inline-between">
              <span className="muted small">
                {new Date(req.created_at).toLocaleString()} · {labels[req.scope] ?? req.scope}
              </span>
              <StatusBadge tone={req.status === "completed" ? "positive" : req.status === "failed" ? "danger" : "info"}>
                {req.status_label}
              </StatusBadge>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export function PrivacyPage() {
  const { workspace } = useWorkspaceContext();
  if (workspace.role === null) {
    return <EmptyState title="No access">You don't have access to this workspace.</EmptyState>;
  }
  return (
    <>
      <header className="page-header">
        <div>
          <h1>Privacy &amp; data</h1>
          <p className="muted">
            Manage retention, exports and deletion for this workspace. These controls support your
            GDPR obligations; they do not by themselves make the service compliant.
          </p>
        </div>
      </header>
      <SettingsForm />
      <Inventory />
      <ExportSection />
      <DeletionSection />
    </>
  );
}
