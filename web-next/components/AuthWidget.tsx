"use client";

import { useState } from "react";
import { useAuth } from "./AuthProvider";

const inputStyle = {
  height: 32,
  padding: "0 8px",
  border: "1px solid var(--line)",
  borderRadius: 8,
  background: "var(--surface)",
  color: "var(--text)",
} as const;

export function AuthWidget() {
  const auth = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!auth.enabled) return null;

  const wrap = { marginLeft: "auto", display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" } as const;

  if (auth.user) {
    return (
      <span style={wrap}>
        <span className="hint">{auth.user.username} ({auth.user.role})</span>
        <button className="btn secondary" onClick={() => void auth.logout()}>Log out</button>
      </span>
    );
  }

  const first = auth.users === 0;
  async function go() {
    setError(null);
    try {
      if (first) await auth.register(username, password);
      else await auth.login(username, password);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <span style={wrap}>
      {error && <span className="hint" style={{ color: "var(--bad)" }}>{error}</span>}
      <input type="text" placeholder={first ? "New admin username" : "Username"} value={username}
        onChange={(e) => setUsername(e.target.value)} style={inputStyle} aria-label="Username" />
      <input type="password" placeholder="Password" value={password}
        onChange={(e) => setPassword(e.target.value)} style={inputStyle} aria-label="Password" />
      <button className="btn secondary" onClick={go}>{first ? "Create admin" : "Sign in"}</button>
    </span>
  );
}
