import Digits from "./Digits.tsx";
import type { ConversationRecord } from "../lib/types.ts";

const STATUS_CLASS: Record<string, string> = {
  fired: "p-resolved",
  flagged: "p-needs_human",
  skipped: "p-partial",
};

/** Overview tab: the close-the-loop result, grouped into clear cards. */
export default function CloseLoopResult({ record }: { record: ConversationRecord | null }) {
  if (!record || !record.facts) {
    return (
      <div className="cards">
        <section className="card span2">
          <span className="empty">
            No result yet. Start a call to clear a case, or run Demo extraction — the
            outcome, note, email and triggered actions appear here.
          </span>
        </section>
      </div>
    );
  }
  const f = record.facts;
  const conf = Math.round((f.analysis_confidence || 0) * 100);
  return (
    <div className="cards">
      <section className="card">
        <p className="card-title">Outcome</p>
        <div className="kv">
          <div className="k">Status</div>
          <div className="v">
            <span className={`pill ${f.needs_human ? "p-needs_human" : "p-resolved"}`}>
              {f.needs_human ? "needs human" : "cleared"}
            </span>
            <span className="conf">· confidence {conf}%</span>
          </div>
          <div className="k">Reason</div><div className="v">{f.stuck_reason || "—"}</div>
          <div className="k">Next step</div><div className="v">{f.next_step || "—"}</div>
          <div className="k">Ticket (VNB)</div><div className="v">{f.ticket_number || "—"}</div>
          <div className="k">Nomos-Vorgang</div><div className="v mono">{f.vorgang_nr || "—"}</div>
        </div>
      </section>

      <section className="card">
        <p className="card-title">Market location (MaLo)</p>
        <div className="sublabel">Grounded digit-by-digit from the readback</div>
        <Digits value={f.malo_id} spoken />
      </section>

      <section className="card span2">
        <p className="card-title">Back-office note · DE</p>
        <div className="note"><div className="de">{record.note}</div></div>
      </section>

      <section className="card">
        <p className="card-title">Email draft → email agent</p>
        <div className="email">
          <div className="email-subj">{record.email_draft.subject}</div>
          <pre className="email-body">{record.email_draft.body}</pre>
        </div>
      </section>

      <section className="card">
        <p className="card-title">Triggered actions</p>
        {record.actions.map((a, i) => (
          <div key={i} className="trigger">
            <span className={`pill ${STATUS_CLASS[a.status] || "p-partial"}`}>{a.status}</span>
            <code>{a.type}</code>
            <span className="trig-detail">{a.detail}</span>
          </div>
        ))}
      </section>

      {f.grounding_notes.length > 0 && (
        <section className="card span2">
          <p className="card-title">Grounding log · never-fabricate</p>
          <ul className="grounding">
            {f.grounding_notes.map((n, i) => <li key={i}>{n}</li>)}
          </ul>
        </section>
      )}
    </div>
  );
}
