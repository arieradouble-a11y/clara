"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { LANGUAGES, type NormalizedResult, type VerifyResult } from "@/lib/types";
import { ResultPanel } from "@/components/ResultPanel";

export default function CheckPage() {
  const [source, setSource] = useState("");
  const [output, setOutput] = useState("");
  const [lang, setLang] = useState("en");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<NormalizedResult | null>(null);
  const [runId, setRunId] = useState(0);

  async function check() {
    if (!source.trim() || !output.trim()) return setError("Fill in both the original and the rewrite.");
    setBusy(true);
    setError(null);
    try {
      const d = await api<VerifyResult>("verify", { source, output, lang });
      setResult({
        original: source,
        outputText: output,
        srcR: d.source_readability,
        outR: d.output_readability,
        faithfulness: d.faithfulness,
        lang,
        level: "check",
        kind: "text",
      });
      setRunId((n) => n + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Check a rewrite</h1>
      <p className="sub">Paste an original and any plain-language rewrite — get the faithfulness report. No model needed.</p>

      <div className="card">
        <div className="grid2">
          <div className="field">
            <label htmlFor="csrc">Original</label>
            <textarea id="csrc" value={source} onChange={(e) => setSource(e.target.value)}
              placeholder="The original, authoritative text…" />
          </div>
          <div className="field">
            <label htmlFor="cout">Rewrite to check</label>
            <textarea id="cout" value={output} onChange={(e) => setOutput(e.target.value)}
              placeholder="A plain-language version to verify…" />
          </div>
        </div>
        <div className="row">
          <div className="field">
            <label htmlFor="lang">Language</label>
            <select id="lang" value={lang} onChange={(e) => setLang(e.target.value)}>
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>
          <button className="btn" onClick={check} disabled={busy}>
            {busy ? "Checking…" : "Check faithfulness"}
          </button>
        </div>
      </div>

      {error && <div className="error" role="alert">{error}</div>}
      {result && <ResultPanel key={runId} result={result} />}
    </>
  );
}
