"use client";

import type { Readability } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

export function ReadabilityBadges({ src, out }: { src: Readability; out: Readability }) {
  const { t } = useI18n();
  const hasGrade = src.flesch_kincaid_grade != null && out.flesch_kincaid_grade != null;
  return (
    <div className="badges">
      {hasGrade && (
        <span className="badge">
          {t("reading_grade")} <b>{src.flesch_kincaid_grade}</b> → <b>{out.flesch_kincaid_grade}</b>
        </span>
      )}
      <span className="badge">
        {t("flesch_ease")} <b>{src.flesch_reading_ease}</b> → <b>{out.flesch_reading_ease}</b>
      </span>
    </div>
  );
}
