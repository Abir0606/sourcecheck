import { NavLink, Outlet, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/endpoints";
import { AppHeader } from "../components/AppHeader";
import { LoadingScreen } from "../components/LoadingScreen";
import { useSession } from "../session";

export function WorkspaceLayout() {
  const { workspaceId = "" } = useParams();
  const { session, refresh } = useSession();

  const { data: workspaces, isLoading } = useQuery({
    queryKey: ["workspaces"],
    queryFn: api.workspaces,
  });
  const workspace = workspaces?.find((w) => w.id === workspaceId);

  if (isLoading) return <LoadingScreen label="Loading workspace…" />;
  if (!workspace) {
    return (
      <div className="container">
        <div className="notice notice--danger" role="alert">
          Workspace not found or you don't have access to it.
        </div>
      </div>
    );
  }

  const canWrite = workspace.role !== "viewer";

  return (
    <div className="page">
      <AppHeader>
        <span className="muted">{session?.user?.display_name}</span>
        <button
          type="button"
          className="button button--ghost"
          onClick={async () => {
            await api.logout();
            refresh();
          }}
        >
          Sign out
        </button>
      </AppHeader>

      <div className="workspace-banner">
        <div className="container workspace-banner__inner">
          <div>
            <h1>{workspace.name}</h1>
            <p className="muted">
              Region: {workspace.data_region} · Retention:{" "}
              {workspace.retention_days === 0 ? "until deleted" : `${workspace.retention_days} days`} ·
              Your role: {workspace.role}
              {canWrite ? "" : " (read-only)"}
            </p>
          </div>
          <nav className="tabs" aria-label="Workspace sections">
            <NavLink to="documents" className="tab">
              Documents
            </NavLink>
            <NavLink to="analyses" className="tab">
              Analyses
            </NavLink>
            <NavLink to="privacy" className="tab">
              Privacy &amp; data
            </NavLink>
          </nav>
        </div>
      </div>

      <main className="container" id="main">
        <Outlet context={{ workspace, canWrite }} />
      </main>
    </div>
  );
}
