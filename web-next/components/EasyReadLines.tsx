import type { EasyReadLine } from "@/lib/types";

export function EasyReadLines({ lines }: { lines: EasyReadLine[] }) {
  return (
    <div>
      {lines.map((l, i) => (
        <div key={i} className="er-line">
          {l.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={l.image_url} alt={l.keyword ?? ""} loading="lazy" />
          ) : (
            <div className="noimg">no picture</div>
          )}
          <span className="er-text">{l.text}</span>
        </div>
      ))}
      <p className="hint">
        Pictograms: <a href="https://arasaac.org">ARASAAC</a> (CC BY-NC-SA) — Government of Aragón,
        author Sergio Palao. Non-commercial use.
      </p>
    </div>
  );
}
