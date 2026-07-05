"use client";

import { useState } from "react";
import Link from "next/link";
import { api, download } from "@/lib/api";
import type { NormalizedResult, SemanticReport } from "@/lib/types";
import { ReadabilityBadges } from "./ReadabilityBadges";
import { FaithfulnessCard } from "./FaithfulnessCard";
import { SemanticCard } from "./SemanticCard";
import { EasyReadLines } from "./EasyReadLines";

const FOOTER =
  "Simplified with Clara — assistive, not authoritative. Verify against the original.";

// Shared result view + actions for Simplify, Check, and Easy Read. Reset its
// internal state by giving it a fresh `key` on each new run.
export function ResultPanel({ result }: { result: NormalizedResult }) {
  const [semantic, setSemantic] = useState<SemanticReport | null>(null);
  const [savedId, setSavedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [embed, setEmbed] = useState(false);

  const isEasy = result.kind === "easyread";

  async function runSemantic() {
    setError(null);
    try {
      setSemantic(
        await api<SemanticReport>("semantic", {
          source: result.original,
          output: result.outputText,
          lang: result.lang,
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function doExport(format: "html" | "pdf") {
    setError(null);
    const title = isEasy ? "Easy Read document" : "Plain-language document";
    const body = isEasy
      ? { format, kind: "easyread", title, lang: result.lang, lines: result.lines, footer: FOOTER, embed_images: embed }
      : { format, kind: "text", title, lang: result.lang, text: result.outputText, footer: FOOTER };
    try {
      await download("export", body, format === "pdf" ? "clara.pdf" : "clara.html");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function save() {
    setError(null);
    const first = result.original.split("\n").map((s) => s.trim()).filter(Boolean)[0] ?? "Untitled";
    const body: Record<string, unknown> = {
      title: first.length > 60 ? first.slice(0, 57) + "…" : first,
      source: result.original,
      output: result.outputText,
      lang: result.lang,
      level: result.level,
      kind: result.kind,
      faithful: result.faithfulness.ok,
    };
    if (isEasy) body.meta = { lines: result.lines };
    try {
      const r = await api<{ id: number }>("reviews/create", body);
      setSavedId(r.id);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <section aria-live="polite" style={{ marginTop: 20 }}>
      <ReadabilityBadges src={result.srcR} out={result.outR} />

      {isEasy ? (
        <>
          <div className="card panel" style={{ marginBottom: 12 }}>
            <h3>Original</h3>
            <div className="body">{result.original}</div>
          </div>
          <EasyReadLines lines={result.lines ?? []} />
        </>
      ) : (
        <div className="grid2">
          <div className="card panel"><h3>Original</h3><div className="body">{result.original}</div></div>
          <div className="card panel">
            <h3>{result.level === "check" ? "Rewrite" : "Simplified"}</h3>
            <div className="body">{result.outputText}</div>
          </div>
        </div>
      )}

      <FaithfulnessCard f={result.faithfulness} />
      {semantic && <SemanticCard report={semantic} />}
      {error && <div className="error" role="alert">{error}</div>}

      <div className="actions">
        <button className="btn secondary" onClick={runSemantic}>Run AI semantic check</button>
        <button className="btn secondary" onClick={() => doExport("html")}>Download HTML</button>
        <button className="btn secondary" onClick={() => doExport("pdf")}>Download tagged PDF</button>
        {isEasy && (
          <label style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--muted)" }}>
            <input type="checkbox" checked={embed} onChange={(e) => setEmbed(e.target.checked)} />
            Embed pictures (offline)
          </label>
        )}
        <button className="btn secondary" onClick={save}>Save to review</button>
        {savedId != null && (
          <span className="hint">Saved — <Link href="/reviews">open in Reviews</Link> (#{savedId}).</span>
        )}
      </div>
    </section>
  );
}
