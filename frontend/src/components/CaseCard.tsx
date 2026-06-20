import type { CaseSummary } from "../lib/types.ts";

interface Props {
  c: CaseSummary;
  onStart: (id: string) => void;
  onPreview: (id: string) => void;
}

export default function CaseCard({ c, onStart, onPreview }: Props) {
  return (
    <article className="case">
      <div className="head">
        <span className="vnb">{c.vnb_name}</span>
        <span className="cid">{c.id}</span>
      </div>
      <h3>{c.case_title}</h3>
      <p className="sym">{c.symptom}</p>
      <div className="actions">
        <button className="btn-primary" onClick={() => onStart(c.id)}>
          <span className="play">▸</span>Start call
        </button>
        <button className="btn-ghost" onClick={() => onPreview(c.id)}>Preview</button>
      </div>
    </article>
  );
}
