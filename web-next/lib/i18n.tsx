"use client";

// UI localization for the Next app. Reads the same catalog the reference UI
// uses, fetched from the backend at /api/clara/i18n, so a translation is written
// once (clara/data/ui_i18n.json) and both front-ends stay in sync.

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { getJson } from "@/lib/api";
import bundled from "@/lib/ui_i18n.json";

type Catalog = Record<string, Record<string, string>>;

// A copy of clara/data/ui_i18n.json is bundled so the UI renders in the right
// language immediately (and offline), before the /i18n fetch confirms the latest.
// A test asserts the two files stay identical.
const FALLBACK = bundled as unknown as Catalog;

interface I18nContext {
  lang: string;
  setLang: (lang: string) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
}

const Ctx = createContext<I18nContext>({ lang: "en", setLang: () => {}, t: (k) => k });

export function I18nProvider({ children }: { children: ReactNode }) {
  const [catalog, setCatalog] = useState<Catalog>(FALLBACK);
  const [lang, setLangState] = useState("en");

  useEffect(() => {
    const saved = localStorage.getItem("clara_ui_lang") || "en";
    setLangState(saved);
    document.documentElement.lang = saved;
    getJson<Catalog>("i18n").then(setCatalog).catch(() => {});
  }, []);

  const setLang = useCallback((next: string) => {
    setLangState(next);
    localStorage.setItem("clara_ui_lang", next);
    document.documentElement.lang = next;
  }, []);

  const t = useCallback(
    (key: string, vars?: Record<string, string | number>) => {
      let s = catalog[lang]?.[key] ?? catalog.en?.[key] ?? key;
      if (vars) for (const k of Object.keys(vars)) s = s.split(`{${k}}`).join(String(vars[k]));
      return s;
    },
    [catalog, lang],
  );

  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}

export const useI18n = () => useContext(Ctx);
