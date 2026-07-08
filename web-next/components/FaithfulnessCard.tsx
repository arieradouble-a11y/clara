"use client";

import type { Faithfulness } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

function chips(items: string[]) {
  return (
    <div className="chips">
      {items.map((x, i) => (
        <span key={i} className="chip">{x}</span>
      ))}
    </div>
  );
}

export function FaithfulnessCard({ f }: { f: Faithfulness }) {
  const { t } = useI18n();
  const clean = f.ok && f.warnings.length === 0;
  if (clean) {
    return (
      <div className="faith ok">
        <p className="ftitle">{t("faithful")}</p>
        <p>{t("faithful_body")}</p>
      </div>
    );
  }
  const block = (labelKey: string, items?: string[]) =>
    items && items.length > 0 ? <div><b>{t(labelKey)}</b>{chips(items)}</div> : null;
  return (
    <div className="faith review">
      <p className="ftitle">{t("needs_review")}</p>
      {block("dropped_numbers", f.dropped_quantities)}
      {block("invented_numbers", f.invented_quantities)}
      {block("dropped_dates", f.dropped_dates)}
      {block("invented_dates", f.invented_dates)}
      {block("changed_ids_dropped", f.dropped_identifiers)}
      {block("changed_ids_added", f.invented_identifiers)}
      {f.warnings.length > 0 && (
        <ul>{f.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
      )}
    </div>
  );
}
