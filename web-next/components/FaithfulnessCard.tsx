import type { Faithfulness } from "@/lib/types";

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
  const clean = f.ok && f.warnings.length === 0;
  if (clean) {
    return (
      <div className="faith ok">
        <p className="ftitle">✓ Faithful</p>
        <p>All numbers and dates were preserved.</p>
      </div>
    );
  }
  return (
    <div className="faith review">
      <p className="ftitle">⚠ Needs review</p>
      {f.dropped_quantities.length > 0 && (
        <div><b>Dropped numbers</b>{chips(f.dropped_quantities)}</div>
      )}
      {f.invented_quantities.length > 0 && (
        <div><b>Invented numbers</b>{chips(f.invented_quantities)}</div>
      )}
      {f.dropped_dates.length > 0 && <div><b>Dropped dates</b>{chips(f.dropped_dates)}</div>}
      {f.invented_dates.length > 0 && <div><b>Invented dates</b>{chips(f.invented_dates)}</div>}
      {f.warnings.length > 0 && (
        <ul>{f.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
      )}
    </div>
  );
}
