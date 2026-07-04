"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Simplify" },
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
    </header>
  );
}
