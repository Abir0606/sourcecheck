import { Navigate, Route, Routes } from "react-router-dom";
import { useSession } from "./session";
import { LoginPage } from "./pages/LoginPage";
import { WorkspaceListPage } from "./pages/WorkspaceListPage";
import { WorkspaceLayout } from "./pages/WorkspaceLayout";
import { DocumentsPage } from "./pages/DocumentsPage";
import { AnalysesPage } from "./pages/AnalysesPage";
import { FindingsPage } from "./pages/FindingsPage";
import { PrivacyPage } from "./pages/PrivacyPage";
import { LoadingScreen } from "./components/LoadingScreen";

export function App() {
  const { session, isLoading } = useSession();

  if (isLoading) return <LoadingScreen label="Checking your session…" />;

  const authed = Boolean(session?.authenticated);

  return (
    <Routes>
      <Route path="/login" element={authed ? <Navigate to="/workspaces" replace /> : <LoginPage />} />
      <Route
        path="/workspaces"
        element={authed ? <WorkspaceListPage /> : <Navigate to="/login" replace />}
      />
      <Route
        path="/workspaces/:workspaceId"
        element={authed ? <WorkspaceLayout /> : <Navigate to="/login" replace />}
      >
        <Route index element={<Navigate to="documents" replace />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="analyses" element={<AnalysesPage />} />
        <Route path="analyses/:jobId" element={<FindingsPage />} />
        <Route path="privacy" element={<PrivacyPage />} />
      </Route>
      <Route path="*" element={<Navigate to={authed ? "/workspaces" : "/login"} replace />} />
    </Routes>
  );
}
