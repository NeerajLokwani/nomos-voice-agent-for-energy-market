import Digits from "./Digits.tsx";
import type { CallResult } from "../lib/types.ts";

export default function Outcome({ result }: { result: CallResult | null }) {
  if (!result) {
    return <span className="empty">No outcome yet — the result lands here when the call ends.</span>;
  }
  const r = result;
  const triggers = r.triggered || [];
  return (
    <>
      <div className="kv">
        <div className="k">Case</div><div className="v">{r.case_id}</div>
        <div className="k">Status</div>
        <div className="v"><span className={`pill p-${r.status}`}>{r.status.replace("_", " ")}</span></div>
        <div className="k">Reason</div><div className="v">{r.reason || "—"}</div>
        <div className="k">Meter</div><div className="v">{r.meter_status}</div>
        <div className="k">Next action</div><div className="v">{r.next_action.replace(/_/g, " ")}</div>
      </div>

      <div className="mt16">
        <div className="sublabel">Corrected MaLo</div>
        <Digits value={r.corrected_malo} spoken />
      </div>
      <div className="mt14">
        <div className="sublabel">Vorgangsnummer</div>
        <Digits value={r.vorgangsnummer} />
      </div>

      <div className="note">
        <div className="nlabel">Back-office note · DE</div>
        <div className="de">{r.note_de}</div>
        <div className="en"><b>EN</b> · {r.note_en_gloss}</div>
      </div>

      <div className="mt16">
        <p className="section-label" style={{ marginBottom: 8 }}>Triggered action</p>
        {triggers.length === 0 ? (
          <span className="empty">none</span>
        ) : (
          triggers.map((t, i) => (
            <div key={i} className="trigger"><span className="zap">⚡</span><code>{t}</code></div>
          ))
        )}
      </div>
    </>
  );
}
