import { useState, type FormEvent } from "react";
import { api } from "../api/endpoints";
import { RequestError } from "../api/client";
import { useSession } from "../session";

export function LoginPage() {
  const { refresh } = useSession();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") await api.login(email, password);
      else await api.register(email, password);
      refresh();
    } catch (err) {
      setError(err instanceof RequestError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-layout">
      <div className="auth-card">
        <h1>SourceCheck</h1>
        <p className="muted">
          Check claims and citations in a document against the sources you upload. Results never
          claim a statement is false just because it wasn't found.
        </p>

        <div className="tabs" role="tablist" aria-label="Sign in or create an account">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "login"}
            className={mode === "login" ? "tab tab--active" : "tab"}
            onClick={() => setMode("login")}
          >
            Sign in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "register"}
            className={mode === "register" ? "tab tab--active" : "tab"}
            onClick={() => setMode("register")}
          >
            Create account
          </button>
        </div>

        <form onSubmit={onSubmit} className="form" noValidate>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={10}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-describedby={mode === "register" ? "pw-help" : undefined}
            />
            {mode === "register" ? (
              <small id="pw-help" className="muted">
                At least 10 characters.
              </small>
            ) : null}
          </div>

          {error ? (
            <div className="notice notice--danger" role="alert">
              {error}
            </div>
          ) : null}

          <button type="submit" className="button button--primary" disabled={busy}>
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
      </div>
    </main>
  );
}
