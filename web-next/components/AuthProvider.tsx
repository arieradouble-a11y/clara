"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getJson, setToken } from "@/lib/api";

interface User {
  id: number;
  username: string;
  role: string;
}

interface AuthStatus {
  enabled: boolean;
  users: number;
  user: User | null;
}

interface AuthContextValue extends AuthStatus {
  ready: boolean;
  refresh: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

const EMPTY: AuthStatus = { enabled: false, users: 0, user: null };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>(EMPTY);
  const [ready, setReady] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setStatus(await getJson<AuthStatus>("auth/status"));
    } catch {
      setStatus(EMPTY);
    }
    setReady(true);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (username: string, password: string) => {
    const d = await api<{ token: string }>("auth/login", { username, password });
    setToken(d.token);
    await refresh();
  }, [refresh]);

  const register = useCallback(async (username: string, password: string) => {
    const d = await api<{ token: string }>("auth/register", { username, password });
    setToken(d.token);
    await refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    try {
      await api("auth/logout", {});
    } catch {
      /* ignore */
    }
    setToken("");
    await refresh();
  }, [refresh]);

  return (
    <AuthContext.Provider value={{ ...status, ready, refresh, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
