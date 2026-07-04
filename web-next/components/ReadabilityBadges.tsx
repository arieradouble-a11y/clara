import type { Readability } from "@/lib/types";

export function ReadabilityBadges({ src, out }: { src: Readability; out: Readability }) {
  const hasGrade = src.flesch_kincaid_grade != null && out.flesch_kincaid_grade != null;
  return (
    <div className="badges">
      {hasGrade && (
        <span className="badge">
          Reading grade <b>{src.flesch_kincaid_grade}</b> → <b>{out.flesch_kincaid_grade}</b>
        </span>
      )}
      <span className="badge">
        Flesch ease <b>{src.flesch_reading_ease}</b> → <b>{out.flesch_reading_ease}</b>
      </span>
    </div>
  );
}
