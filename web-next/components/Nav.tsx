"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AuthWidget } from "./AuthWidget";

const LINKS = [
  { href: "/", label: "Simplify" },
  { href: "/check", label: "Check a rewrite" },
  { href: "/reviews", label: "Reviews" },
];

export function Nav() {
  const path = usePathname();
  return (
    <header className="nav">
      <span className="brand">Clara</span>
      {LINKS.map((l) => (
        <Link key={l.href} href={l.href} className={path === l.href ? "active" : ""}>
          {l.label}
        </Link>
      ))}
      <AuthWidget />
    </header>
  );
}
