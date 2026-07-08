"use client";

import { useState } from "react";
import { useAuth } from "./AuthProvider";
import { useI18n } from "@/lib/i18n";

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
  const { t } = useI18n();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!auth.enabled) return null;

  const wrap = { display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" } as const;

  if (auth.user) {
    return (
      <span style={wrap}>
        <span className="hint">{auth.user.username} ({auth.user.role})</span>
        <button className="btn secondary" onClick={() => void auth.logout()}>{t("logout")}</button>
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
      <input type="text" placeholder={first ? t("new_admin_username") : t("username")} value={username}
        onChange={(e) => setUsername(e.target.value)} style={inputStyle} aria-label={t("username")} />
      <input type="password" placeholder={t("password")} value={password}
        onChange={(e) => setPassword(e.target.value)} style={inputStyle} aria-label={t("password")} />
      <button className="btn secondary" onClick={go}>{first ? t("create_admin") : t("signin")}</button>
    </span>
  );
}
