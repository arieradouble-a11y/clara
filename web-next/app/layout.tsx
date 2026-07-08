import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AuthProvider } from "@/components/AuthProvider";
import { I18nProvider } from "@/lib/i18n";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "Clara — verified plain language",
  description: "Turn complex text into verified plain language.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <I18nProvider>
          <AuthProvider>
            <Nav />
            <main className="wrap">{children}</main>
          </AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
