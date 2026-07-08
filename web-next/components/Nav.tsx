"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n } from "@/lib/i18n";
import { LANGUAGES } from "@/lib/types";
import { AuthWidget } from "./AuthWidget";

const LINKS = [
  { href: "/", key: "tab_simplify" },
  { href: "/check", key: "tab_check" },
  { href: "/reviews", key: "tab_reviews" },
];

export function Nav() {
  const path = usePathname();
  const { t, lang, setLang } = useI18n();
  return (
    <header className="nav">
      <span className="brand">Clara</span>
      {LINKS.map((l) => (
        <Link key={l.href} href={l.href} className={path === l.href ? "active" : ""}>
          {t(l.key)}
        </Link>
      ))}
      <label style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6, color: "var(--muted)" }}>
        <span className="hint">{t("language")}</span>
        <select value={lang} onChange={(e) => setLang(e.target.value)} aria-label={t("language")}>
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>{l.label}</option>
          ))}
        </select>
      </label>
      <AuthWidget />
    </header>
  );
}
