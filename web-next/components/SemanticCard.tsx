"use client";

import type { SemanticReport } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

export function SemanticCard({ report }: { report: SemanticReport }) {
  const { t } = useI18n();
  const clean = report.available && report.faithful && report.issues.length === 0;
  return (
    <div className={`faith ${clean ? "ok" : "review"}`}>
      {!report.available ? (
        <>
          <p className="ftitle">{t("ai_unavailable")}</p>
          <p>{t("ai_unavailable_body")}</p>
        </>
      ) : clean ? (
        <>
          <p className="ftitle">{t("ai_faithful")}</p>
          <p>{t("ai_faithful_body")}</p>
        </>
      ) : (
        <>
          <p className="ftitle">{t("ai_review")}</p>
          <ul>{report.issues.map((i, k) => <li key={k}><b>{i.type}:</b> {i.detail}</li>)}</ul>
        </>
      )}
    </div>
  );
}
