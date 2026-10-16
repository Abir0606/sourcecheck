import type { ReactNode } from "react";

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state" role="status">
      <h3>{title}</h3>
      {children ? <div className="muted">{children}</div> : null}
      {action ? <div className="empty-state__action">{action}</div> : null}
    </div>
  );
}

export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="notice notice--danger" role="alert">
      <span>{message}</span>
      {onRetry ? (
        <button type="button" className="button button--ghost" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}
