"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { type NormalizedResult, type VerifyResult } from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { ResultPanel } from "@/components/ResultPanel";

export default function CheckPage() {
  const { t, lang } = useI18n();
  const [source, setSource] = useState("");
  const [output, setOutput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<NormalizedResult | null>(null);
  const [runId, setRunId] = useState(0);

  async function check() {
    if (!source.trim() || !output.trim()) return setError(t("fill_both"));
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
      <h1>{t("tab_check")}</h1>
      <p className="sub">{t("sub_check")}</p>

      <div className="card">
        <div className="grid2">
          <div className="field">
            <label htmlFor="csrc">{t("check_original")}</label>
            <textarea id="csrc" value={source} onChange={(e) => setSource(e.target.value)}
              placeholder={t("check_original_ph")} />
          </div>
          <div className="field">
            <label htmlFor="cout">{t("check_rewrite")}</label>
            <textarea id="cout" value={output} onChange={(e) => setOutput(e.target.value)}
              placeholder={t("check_rewrite_ph")} />
          </div>
        </div>
        <div className="row">
          <button className="btn" onClick={check} disabled={busy}>
            {busy ? t("checking") : t("check")}
          </button>
        </div>
      </div>

      {error && <div className="error" role="alert">{error}</div>}
      {result && <ResultPanel key={runId} result={result} />}
    </>
  );
}
