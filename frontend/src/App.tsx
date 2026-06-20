import { useEffect, useRef, useState } from "react";
import { api } from "./lib/api.ts";
import CaseCard from "./components/CaseCard.tsx";
import LiveCall from "./components/LiveCall.tsx";
import Outcome from "./components/Outcome.tsx";
import Preview from "./components/Preview.tsx";
import type { CallResult, CaseSummary, CaseVariables, LiveState } from "./lib/types.ts";

function stageFromStatus(st: string | undefined, hasResult: boolean): number {
  if (hasResult || st === "ended" || (st || "").includes("completed")) return 4;
  if ((st || "").includes("answered")) return 2;
  if (st === "dialing" || (st || "").includes("initiated") || (st || "").includes("ringing")) return 1;
  return 0;
}

const IDLE: LiveState = { on: false, meta: "idle", transcript: [] };

export default function App() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [dryRun, setDryRun] = useState(true);
  const [vars, setVars] = useState<CaseVariables | null>(null);
  const [result, setResult] = useState<CallResult | null>(null);
  const [stageIndex, setStageIndex] = useState(0);
  const [live, setLive] = useState<LiveState>(IDLE);

  const callRef = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    api.listCases().then(setCases);
    return () => clearTimeout(timerRef.current);
  }, []);

  async function preview(id: string) {
    setVars(await api.caseVariables(id));
  }

  async function startCall(id: string) {
    const r = await api.startCall(id, dryRun);
    if ("error" in r) {
      setLive({ on: false, meta: "refused", transcript: [], note: r.error });
      return;
    }
    callRef.current = r.call_id;
    setResult(null);
    setStageIndex(1);
    setLive({
      on: true,
      meta: dryRun ? "dry run" : "dialing",
      transcript: [],
      note: dryRun
        ? `Prepared ${r.call_id.slice(0, 8)} — no number dialed (dry run). In a live run the agent navigates the menu, declares it is an AI, and speaks now.`
        : null,
    });
    poll();
  }

  async function poll() {
    clearTimeout(timerRef.current);
    if (!callRef.current) return;
    try {
      const l = await api.live(callRef.current);
      const turns = l.transcript || [];
      setLive((prev) => ({ ...prev, transcript: turns, note: turns.length ? null : prev.note }));
      setStageIndex(stageFromStatus(l.status, false));
      if ((l.status || "").includes("completed") || l.status === "ended") {
        finalize();
        return;
      }
    } catch {
      /* transient — keep polling */
    }
    timerRef.current = setTimeout(poll, 1500);
  }

  async function finalize() {
    clearTimeout(timerRef.current);
    if (!callRef.current) return;
    const r = await api.finalize(callRef.current);
    if ("error" in r) return;
    setResult(r);
    setStageIndex(4);
    setLive((prev) => ({ ...prev, on: false, meta: "call ended" }));
  }

  const showSimulate = live.on && dryRun && live.transcript.length === 0;

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <span className="mark">nomos<span className="bolt">.</span></span>
          <span className="tag">clearing calls</span>
        </div>
        <div className="lede">
          Autonomous phone agent that clears stuck market-communication cases with grid
          operators — <b>in German, end to end.</b>
        </div>
      </header>

      <div className="app">
        <aside className="queue">
          <label className="toggle">
            <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
            Dry run — prepare the call without dialing
          </label>
          <p className="section-label">Case queue</p>
          {cases.map((c) => (
            <CaseCard key={c.id} c={c} onStart={startCall} onPreview={preview} />
          ))}
        </aside>

        <main className="stage">
          <LiveCall
            live={{ ...live, placeholder: "Pick a case on the left to place a clearing call." }}
            stageIndex={stageIndex}
            onSimulate={showSimulate ? finalize : null}
          />

          <div className="grid-2">
            <section className="panel">
              <div className="pbody">
                <p className="section-label">Outcome</p>
                <Outcome result={result} />
              </div>
            </section>
            <section className="panel">
              <div className="pbody">
                <p className="section-label">What the agent will say</p>
                <Preview vars={vars} />
              </div>
            </section>
          </div>
        </main>
      </div>
    </>
  );
}
