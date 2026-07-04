"use client";

import { useState } from "react";
import Link from "next/link";
import { api, download } from "@/lib/api";
import { LANGUAGES, type SemanticReport, type SimplifyResult } from "@/lib/types";
import { ReadabilityBadges } from "@/components/ReadabilityBadges";
import { FaithfulnessCard } from "@/components/FaithfulnessCard";

const EXPORT_FOOTER =
  "Simplified with Clara — assistive, not authoritative. Verify against the original.";

export default function SimplifyPage() {
  const [text, setText] = useState("");
  const [lang, setLang] = useState("en");
  const [level, setLevel] = useState("plain");
  const [grade, setGrade] = useState(5);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SimplifyResult | null>(null);
  const [semantic, setSemantic] = useState<SemanticReport | null>(null);
  const [savedId, setSavedId] = useState<number | null>(null);

  async function run() {
    if (!text.trim()) return setError("Enter some text to simplify.");
    setBusy(true);
    setError(null);
    setSemantic(null);
    setSavedId(null);
    try {
      const body: Record<string, unknown> = { text, level, lang };
      if (level === "grade") body.grade = grade;
      setResult(await api<SimplifyResult>("simplify", body));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function runSemantic() {
    if (!result) return;
    setError(null);
    try {
      setSemantic(
        await api<SemanticReport>("semantic", {
          source: result.original,
          output: result.simplified,
          lang,
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function doExport(format: "html" | "pdf") {
    if (!result) return;
    setError(null);
    try {
      await download(
        "export",
        { format, kind: "text", title: "Plain-language document", lang, text: result.simplified, footer: EXPORT_FOOTER },
        format === "pdf" ? "clara.pdf" : "clara.html",
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function save() {
    if (!result) return;
    setError(null);
    try {
      const first = result.original.split("\n").map((s) => s.trim()).filter(Boolean)[0] ?? "Untitled";
      const r = await api<{ id: number }>("reviews/create", {
        title: first.length > 60 ? first.slice(0, 57) + "…" : first,
        source: result.original,
        output: result.simplified,
        lang,
        level,
        kind: "text",
        faithful: result.faithfulness.ok,
      });
      setSavedId(r.id);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <>
      <h1>Simplify</h1>
      <p className="sub">Turn complex text into verified plain language.</p>

      <div className="card">
        <label htmlFor="src">Source text</label>
        <textarea
          id="src"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste a dense notice, contract clause, or medical instruction…"
        />
        <div className="row">
          <div className="field">
            <label htmlFor="lang">Language</label>
            <select id="lang" value={lang} onChange={(e) => setLang(e.target.value)}>
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="level">Level</label>
            <select id="level" value={level} onChange={(e) => setLevel(e.target.value)}>
              <option value="plain">Plain Language</option>
              <option value="grade">Target grade</option>
            </select>
          </div>
          {level === "grade" && (
            <div className="field">
              <label htmlFor="grade">Grade</label>
              <input
                id="grade"
                type="text"
                inputMode="numeric"
                value={grade}
                onChange={(e) => setGrade(Number(e.target.value) || 1)}
                style={{ width: 80 }}
              />
            </div>
          )}
          <button className="btn" onClick={run} disabled={busy}>
            {busy ? "Simplifying…" : "Simplify"}
          </button>
        </div>
        <p className="hint" style={{ marginTop: 10 }}>
          Runs on the backend&apos;s configured model. With the default <code>mock</code> provider it
          echoes the text — set <code>CLARA_PROVIDER</code> for real rewriting.
        </p>
      </div>

      {error && <div className="error" role="alert">{error}</div>}

      {result && (
        <section aria-live="polite" style={{ marginTop: 20 }}>
          <ReadabilityBadges src={result.source_readability} out={result.output_readability} />
          <div className="grid2">
            <div className="card panel"><h3>Original</h3><div className="body">{result.original}</div></div>
            <div className="card panel"><h3>Simplified</h3><div className="body">{result.simplified}</div></div>
          </div>

          <FaithfulnessCard f={result.faithfulness} />

          {semantic && (
            <div className={`faith ${semantic.available && semantic.faithful && semantic.issues.length === 0 ? "ok" : "review"}`}>
              {!semantic.available ? (
                <>
                  <p className="ftitle">AI check unavailable</p>
                  <p>Configure a model provider (set <code>CLARA_PROVIDER</code>) to run the semantic check.</p>
                </>
              ) : semantic.faithful && semantic.issues.length === 0 ? (
                <><p className="ftitle">✓ AI check: faithful</p><p>No meaning drift detected.</p></>
              ) : (
                <>
                  <p className="ftitle">⚠ AI check: review</p>
                  <ul>{semantic.issues.map((i, k) => <li key={k}><b>{i.type}:</b> {i.detail}</li>)}</ul>
                </>
              )}
            </div>
          )}

          <div className="actions">
            <button className="btn secondary" onClick={runSemantic}>Run AI semantic check</button>
            <button className="btn secondary" onClick={() => doExport("html")}>Download HTML</button>
            <button className="btn secondary" onClick={() => doExport("pdf")}>Download tagged PDF</button>
            <button className="btn secondary" onClick={save}>Save to review</button>
            {savedId != null && (
              <span className="hint">
                Saved — <Link href="/reviews">open in Reviews</Link> (#{savedId}).
              </span>
            )}
          </div>
        </section>
      )}
    </>
  );
}
