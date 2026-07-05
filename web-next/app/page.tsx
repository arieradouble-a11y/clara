"use client";

import { useState, type ChangeEvent } from "react";
import { api, toBase64 } from "@/lib/api";
import {
  LANGUAGES,
  type EasyReadResult,
  type NormalizedResult,
  type SimplifyResult,
} from "@/lib/types";
import { ResultPanel } from "@/components/ResultPanel";

export default function SimplifyPage() {
  const [text, setText] = useState("");
  const [lang, setLang] = useState("en");
  const [level, setLevel] = useState("plain");
  const [grade, setGrade] = useState(5);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<NormalizedResult | null>(null);
  const [runId, setRunId] = useState(0);

  async function run() {
    if (!text.trim()) return setError("Enter some text to simplify.");
    setBusy(true);
    setError(null);
    try {
      let next: NormalizedResult;
      if (level === "easy_read") {
        const d = await api<EasyReadResult>("easyread", { text, lang });
        next = {
          original: d.original,
          outputText: d.lines.map((l) => l.text).join("\n"),
          srcR: d.source_readability,
          outR: d.output_readability,
          faithfulness: d.faithfulness,
          lang,
          level: "easy_read",
          kind: "easyread",
          lines: d.lines,
        };
      } else {
        const body: Record<string, unknown> = { text, level, lang };
        if (level === "grade") body.grade = grade;
        const d = await api<SimplifyResult>("simplify", body);
        next = {
          original: d.original,
          outputText: d.simplified,
          srcR: d.source_readability,
          outR: d.output_readability,
          faithfulness: d.faithfulness,
          lang,
          level,
          kind: "text",
        };
      }
      setResult(next);
      setRunId((n) => n + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function importUrl() {
    if (!url.trim()) return;
    setError(null);
    try {
      const d = await api<{ text: string }>("ingest", { url });
      setText(d.text ?? "");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function importFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    try {
      const content_b64 = toBase64(await file.arrayBuffer());
      const d = await api<{ text: string }>("ingest", { filename: file.name, content_b64 });
      setText(d.text ?? "");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      e.target.value = "";
    }
  }

  return (
    <>
      <h1>Simplify</h1>
      <p className="sub">Turn complex text into verified plain language.</p>

      <div className="card">
        <div className="actions" style={{ marginBottom: 12 }}>
          <input
            type="text"
            placeholder="Import from a URL…"
            aria-label="Import from a URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            style={{ flex: 1, minWidth: 200 }}
          />
          <button className="btn secondary" onClick={importUrl}>Import URL</button>
          <label className="btn secondary" style={{ cursor: "pointer" }}>
            Import file
            <input
              type="file"
              accept=".txt,.html,.htm,.pdf,.docx"
              onChange={importFile}
              style={{ display: "none" }}
            />
          </label>
        </div>

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
              <option value="easy_read">Easy Read</option>
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
            {busy ? "Working…" : "Simplify"}
          </button>
        </div>
        <p className="hint" style={{ marginTop: 10 }}>
          Runs on the backend&apos;s configured model. With the default <code>mock</code> provider it
          echoes the text — set <code>CLARA_PROVIDER</code> for real rewriting.
        </p>
      </div>

      {error && <div className="error" role="alert">{error}</div>}
      {result && <ResultPanel key={runId} result={result} />}
    </>
  );
}
