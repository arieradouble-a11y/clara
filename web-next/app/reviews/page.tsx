"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { useI18n } from "@/lib/i18n";
import type { Review, ReviewSummary } from "@/lib/types";

const STATUSES = ["", "in_review", "changes_requested", "approved", "rejected", "draft"];
const STATUS_KEY: Record<string, string> = {
  in_review: "filter_in_review", changes_requested: "filter_changes_requested",
  approved: "filter_approved", rejected: "filter_rejected", draft: "filter_draft",
};

export default function ReviewsPage() {
  const auth = useAuth();
  const { t } = useI18n();
  const statusLabel = (s: string) => (s ? (STATUS_KEY[s] ? t(STATUS_KEY[s]) : s.replace(/_/g, " ")) : t("filter_all"));
  const StatusBadge = ({ status }: { status: string }) =>
    <span className={`badge-status st-${status}`}>{statusLabel(status)}</span>;
  const [rows, setRows] = useState<ReviewSummary[]>([]);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<Review | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [author, setAuthor] = useState("");
  const [body, setBody] = useState("");
  const [revision, setRevision] = useState("");

  const locked = auth.enabled && !auth.user;

  const load = useCallback(async () => {
    if (auth.enabled && !auth.user) {
      setRows([]);
      setSelected(null);
      return;
    }
    setError(null);
    try {
      const d = await api<{ reviews: ReviewSummary[] }>("reviews/list", filter ? { status: filter } : {});
      setRows(d.reviews);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [filter, auth.enabled, auth.user]);

  useEffect(() => {
    if (auth.ready) void load();
  }, [load, auth.ready]);

  async function open(id: number) {
    setError(null);
    try {
      const r = await api<Review>("reviews/get", { id });
      setSelected(r);
      setRevision(r.output);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function act(path: string, payload: object) {
    try {
      const r = await api<Review>(path, payload);
      setSelected(r);
      setRevision(r.output);
      void load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <>
      <h1>{t("tab_reviews")}</h1>
      <p className="sub">{t("sub_reviews")}</p>

      <div className="actions" style={{ marginBottom: 12 }}>
        <button className="btn secondary" onClick={() => void load()}>{t("refresh")}</button>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{statusLabel(s)}</option>
          ))}
        </select>
      </div>

      {error && <div className="error" role="alert">{error}</div>}

      {locked ? (
        <p className="hint">{t("please_signin")}</p>
      ) : rows.length === 0 ? (
        <p className="hint">{t("no_reviews")}</p>
      ) : (
        rows.map((r) => (
          <div key={r.id} className="rv-row" onClick={() => void open(r.id)}>
            <div>
              <div style={{ fontWeight: 600 }}>{r.title}</div>
              <div className="hint">#{r.id} · {r.lang}/{r.level} · {r.updated_at}</div>
            </div>
            <StatusBadge status={r.status} />
          </div>
        ))
      )}

      {selected && (
        <section className="card" style={{ marginTop: 16 }} aria-live="polite">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <div><b>{selected.title}</b> <span className="hint">#{selected.id} · {selected.lang}/{selected.level}</span></div>
            <StatusBadge status={selected.status} />
          </div>

          <div className="grid2" style={{ marginBottom: 12 }}>
            <div className="card panel" lang={selected.lang}><h3>{t("original")}</h3><div className="body">{selected.source}</div></div>
            <div className="card panel" lang={selected.lang}>
              <h3>
                {t("current_output")}{" "}
                {selected.faithful != null && (
                  <span className={`badge-status ${selected.faithful ? "st-approved" : "st-changes_requested"}`}>
                    {selected.faithful ? t("facts_preserved") : t("facts_need_review")}
                  </span>
                )}
              </h3>
              <div className="body">{selected.output}</div>
            </div>
          </div>

          <div className="actions" style={{ marginBottom: 16 }}>
            <button className="btn secondary" onClick={() => void act("reviews/status", { id: selected.id, status: "approved" })}>{t("approve")}</button>
            <button className="btn secondary" onClick={() => void act("reviews/status", { id: selected.id, status: "changes_requested" })}>{t("request_changes")}</button>
            <button className="btn secondary" onClick={() => void act("reviews/status", { id: selected.id, status: "rejected" })}>{t("reject")}</button>
            <span className="hint">{t("versions_n", { n: selected.versions.length })}</span>
          </div>

          <h3 style={{ margin: "0 0 8px", fontSize: 14, textTransform: "uppercase", letterSpacing: ".04em", color: "var(--muted)" }}>
            {t("comments")}
          </h3>
          {selected.comments.length === 0 ? (
            <p className="hint">{t("no_comments")}</p>
          ) : (
            selected.comments.map((c) => (
              <div key={c.id} className="rv-comment">
                <div className="who">{c.author} · {c.created_at}</div>
                {c.body}
              </div>
            ))
          )}
          <div className="actions">
            <input type="text" placeholder={t("your_name")} value={author} onChange={(e) => setAuthor(e.target.value)} style={{ width: 150 }} />
            <input type="text" placeholder={t("add_comment_ph")} value={body} onChange={(e) => setBody(e.target.value)} style={{ flex: 1, minWidth: 180 }} />
            <button
              className="btn secondary"
              onClick={() => {
                if (!body.trim()) return;
                void act("reviews/comment", { id: selected.id, author, body }).then(() => setBody(""));
              }}
            >
              {t("comment")}
            </button>
          </div>

          <div style={{ marginTop: 16 }}>
            <label htmlFor="rev">{t("save_revision")}</label>
            <textarea id="rev" value={revision} onChange={(e) => setRevision(e.target.value)} />
            <div style={{ marginTop: 8 }}>
              <button
                className="btn secondary"
                onClick={() => void act("reviews/revision", { id: selected.id, output: revision, note: "edited in reviewer" })}
              >
                {t("save_revision_btn")}
              </button>
            </div>
          </div>
        </section>
      )}
    </>
  );
}
