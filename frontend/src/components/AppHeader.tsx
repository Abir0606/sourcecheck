import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export function AppHeader({ children }: { children?: ReactNode }) {
  return (
    <header className="app-header">
      <Link to="/workspaces" className="app-header__brand">
        SourceCheck
      </Link>
      <div className="app-header__actions">{children}</div>
    </header>
  );
}
