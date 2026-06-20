import Digits from "./Digits.tsx";
import type { CaseVariables } from "../lib/types.ts";

export default function Preview({ vars }: { vars: CaseVariables | null }) {
  if (!vars) {
    return <span className="empty">Pick a case → “Preview” to see the numbers it reads, digit by digit.</span>;
  }
  return (
    <>
      <div className="kv" style={{ gridTemplateColumns: "120px 1fr" }}>
        <div className="k">Goal</div><div className="v">{vars.goal || "—"}</div>
      </div>
      <div className="mt14">
        <div className="sublabel">Market location (MaLo)</div>
        <Digits value={vars.malo_id} spoken />
      </div>
      <div className="mt14">
        <div className="sublabel">Meter serial</div>
        <Digits value={vars.zaehlernummer} />
      </div>
    </>
  );
}
