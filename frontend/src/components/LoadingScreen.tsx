export function LoadingScreen({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="center-screen" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <p>{label}</p>
    </div>
  );
}
