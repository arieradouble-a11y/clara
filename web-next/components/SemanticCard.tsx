import type { SemanticReport } from "@/lib/types";

export function SemanticCard({ report }: { report: SemanticReport }) {
  const clean = report.available && report.faithful && report.issues.length === 0;
  return (
    <div className={`faith ${clean ? "ok" : "review"}`}>
      {!report.available ? (
        <>
          <p className="ftitle">AI check unavailable</p>
          <p>Configure a model provider (set <code>CLARA_PROVIDER</code>) to run the semantic check.</p>
        </>
      ) : clean ? (
        <>
          <p className="ftitle">✓ AI check: faithful</p>
          <p>No meaning drift detected.</p>
        </>
      ) : (
        <>
          <p className="ftitle">⚠ AI check: review</p>
          <ul>{report.issues.map((i, k) => <li key={k}><b>{i.type}:</b> {i.detail}</li>)}</ul>
        </>
      )}
    </div>
  );
}
