"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api-client";
import { rolePath, saveSession } from "@/lib/session";

const DEMO_ACCOUNTS = [
  { label: "Student — Rahul Verma", email: "rahul@student.eis.edu", accent: "#4f7cff" },
  { label: "Parent — Sunita Verma", email: "sunita@parent.eis.edu", accent: "#00a389" },
  { label: "Teacher — Anita Sharma", email: "anita@teacher.eis.edu", accent: "#7a5cf0" },
  { label: "Principal — Dr. Meera Iyer", email: "principal@eis.edu", accent: "#c2683a" },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await api.login(email.trim(), password);
      saveSession({ token: result.token, user: result.user, sessionId: result.session_id });
      router.replace(rolePath[result.user.role]);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <div className="login__panel">
        <span className="brand__mark brand__mark--lg">EIS</span>
        <h1>EIS AI</h1>
        <p className="login__tagline">
          One assistant, four roles. Your portal is chosen by your account — never by what you type.
        </p>

        <form onSubmit={submit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              required
              autoComplete="username"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="rahul@student.eis.edu"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              required
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error && <p className="login__error">{error}</p>}
          <button className="button button--wide" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="login__demo">
          <p>Demo accounts (password <code>password123</code>)</p>
          <div className="login__chips">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                style={{ ["--accent" as string]: account.accent }}
                onClick={() => setEmail(account.email)}
              >
                {account.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
