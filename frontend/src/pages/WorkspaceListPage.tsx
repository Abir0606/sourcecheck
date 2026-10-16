import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/endpoints";
import { LoadingScreen } from "../components/LoadingScreen";
import { EmptyState, ErrorNotice } from "../components/States";
import { useSession } from "../session";
import { AppHeader } from "../components/AppHeader";

export function WorkspaceListPage() {
  const queryClient = useQueryClient();
  const { session, refresh } = useSession();
  const [name, setName] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["workspaces"],
    queryFn: api.workspaces,
  });

  const createMutation = useMutation({
    mutationFn: () => api.createWorkspace(name.trim()),
    onSuccess: () => {
      setName("");
      void queryClient.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });

  async function signOut() {
    await api.logout();
    refresh();
  }

  return (
    <div className="page">
      <AppHeader>
        <span className="muted">{session?.user?.display_name}</span>
        <button type="button" className="button button--ghost" onClick={signOut}>
          Sign out
        </button>
      </AppHeader>

      <main className="container">
        <header className="page-header">
          <h1>Your workspaces</h1>
          <p className="muted">
            A workspace groups one target document with the source documents you check it against.
          </p>
        </header>

        <section aria-labelledby="create-ws" className="card">
          <h2 id="create-ws">Create a workspace</h2>
          <form
            className="inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (name.trim()) createMutation.mutate();
            }}
          >
            <div className="field field--grow">
              <label htmlFor="ws-name">Workspace name</label>
              <input
                id="ws-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Annual report review"
                required
              />
            </div>
            <button type="submit" className="button button--primary" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Creating…" : "Create"}
            </button>
          </form>
          {createMutation.error ? <ErrorNotice message="Could not create the workspace." /> : null}
        </section>

        <section aria-labelledby="ws-list">
          <h2 id="ws-list">Workspaces</h2>
          {isLoading ? <LoadingScreen label="Loading workspaces…" /> : null}
          {error ? <ErrorNotice message="Could not load workspaces." /> : null}
          {data && data.length === 0 ? (
            <EmptyState title="No workspaces yet">
              Create your first workspace above to begin.
            </EmptyState>
          ) : null}
          {data && data.length > 0 ? (
            <ul className="card-grid">
              {data.map((workspace) => (
                <li key={workspace.id} className="card card--link">
                  <h3>
                    <Link to={`/workspaces/${workspace.id}/documents`}>{workspace.name}</Link>
                  </h3>
                  <p className="muted">
                    {workspace.role} · {workspace.member_count} member
                    {workspace.member_count === 1 ? "" : "s"} · region {workspace.data_region}
                  </p>
                  <p className="muted">
                    Retention:{" "}
                    {workspace.retention_days === 0
                      ? "until deleted"
                      : `${workspace.retention_days} days`}
                  </p>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </main>
    </div>
  );
}
