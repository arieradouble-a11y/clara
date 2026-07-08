"use client";

import { useState, type ChangeEvent } from "react";
import { api, toBase64 } from "@/lib/api";
import {
  type EasyReadResult,
  type NormalizedResult,
  type SimplifyResult,
} from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { ResultPanel } from "@/components/ResultPanel";

export default function SimplifyPage() {
  const { t, lang } = useI18n();   // the global language selector drives content + chrome
  const [text, setText] = useState("");
  const [level, setLevel] = useState("plain");
  const [grade, setGrade] = useState(5);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<NormalizedResult | null>(null);
  const [runId, setRunId] = useState(0);

  async function run() {
    if (!text.trim()) return setError(t("enter_text"));
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
      <h1>{t("tab_simplify")}</h1>
      <p className="sub">{t("sub_simplify")}</p>

      <div className="card">
        <div className="actions" style={{ marginBottom: 12 }}>
          <input
            type="text"
            placeholder={t("import_url_ph")}
            aria-label={t("import_url_ph")}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            style={{ flex: 1, minWidth: 200 }}
          />
          <button className="btn secondary" onClick={importUrl}>{t("import_url")}</button>
          <label className="btn secondary" style={{ cursor: "pointer" }}>
            {t("import_file")}
            <input
              type="file"
              accept=".txt,.html,.htm,.pdf,.docx"
              onChange={importFile}
              style={{ display: "none" }}
            />
          </label>
        </div>

        <label htmlFor="src">{t("source")}</label>
        <textarea
          id="src"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t("source_ph")}
        />

        <div className="row">
          <div className="field">
            <label htmlFor="level">{t("level")}</label>
            <select id="level" value={level} onChange={(e) => setLevel(e.target.value)}>
              <option value="plain">{t("level_plain")}</option>
              <option value="easy_read">{t("level_easy")}</option>
              <option value="grade">{t("level_grade")}</option>
            </select>
          </div>
          {level === "grade" && (
            <div className="field">
              <label htmlFor="grade">{t("grade")}</label>
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
            {busy ? t("working") : t("simplify")}
          </button>
        </div>
        <p className="hint" style={{ marginTop: 10 }}>{t("provider_hint")}</p>
      </div>

      {error && <div className="error" role="alert">{error}</div>}
      {result && <ResultPanel key={runId} result={result} />}
    </>
  );
}
