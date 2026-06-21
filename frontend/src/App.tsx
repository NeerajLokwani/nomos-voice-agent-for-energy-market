import { useEffect, useRef, useState } from "react";
import { api } from "./lib/api.ts";
import CaseCard from "./components/CaseCard.tsx";
import CloseLoopResult from "./components/CloseLoopResult.tsx";
import Transcript from "./components/Transcript.tsx";
import Preview from "./components/Preview.tsx";
import PipelineStepper from "./components/PipelineStepper.tsx";
import type {
  CaseSummary, CaseVariables, ConversationRecord, TranscriptTurn,
} from "./lib/types.ts";

type Tab = "overview" | "transcript";

export default function App() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [vars, setVars] = useState<CaseVariables | null>(null);
  const [record, setRecord] = useState<ConversationRecord | null>(null);
  const [turns, setTurns] = useState<TranscriptTurn[]>([]);
  const [phase, setPhase] = useState(0);       // 0 idle … 6 done (pipeline stepper)
  const [statusText, setStatusText] = useState("Agent ready");
  const [tab, setTab] = useState<Tab>("overview");
  const [note, setNote] = useState<string | null>(null);

  const callRef = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    api.listCases().then(setCases);
    return () => clearTimeout(timerRef.current);
  }, []);

  function reset() {
    clearTimeout(timerRef.current);
    setRecord(null);
    setTurns([]);
    setNote(null);
  }

  function showRecord(rec: ConversationRecord) {
    setRecord(rec);
    setTurns((rec.transcript || []).map((t) => ({ role: t.role, text: t.message })));
    setPhase(6);
    setStatusText("Call ended");
    setNote(null);
  }

  async function preview(id: string) {
    setVars(await api.caseVariables(id));
  }

  async function startCall(id: string) {
    reset();
    const r = await api.startCall(id, false);
    if ("error" in r) { setStatusText("Refused"); setNote(r.error); return; }
    callRef.current = r.call_id;
    setPhase(2);
    setStatusText("On call…");
    setNote("Calling the practice clerk. The agent navigates the menu, declares it is an AI, and speaks. The result appears here when the call ends.");
    setTab("overview");
    pollRecord(r.call_id);
  }

  async function pollRecord(callId: string) {
    clearTimeout(timerRef.current);
    const rec = await api.conversation(callId);
    if (!("error" in rec)) { showRecord(rec); return; }
    timerRef.current = setTimeout(() => pollRecord(callId), 2500);
  }

  async function runDemo(id: string) {
    reset();
    callRef.current = null;
    setPhase(3);
    setStatusText("Running pipeline…");
    setTab("overview");
    const rec = await api.simulatePostcall(id);
    if ("error" in rec) { setStatusText("Error"); setNote(rec.error); return; }
    showRecord(rec);
  }

  const statusOn = phase > 0 && phase < 6;

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <span className="mark">nomos<span className="bolt">.</span></span>
          <span className="tag">clearing calls</span>
        </div>
        <div className="lede">
          Calls a grid operator, clears the case in German, then extracts the facts, writes
          the note, and triggers the next action.
        </div>
        <span className={`status-chip ${statusOn ? "live" : record ? "done" : ""}`}>
          <span className="dot" /> {statusText}
        </span>
      </header>

      <div className="shell">
        <PipelineStepper activeIndex={phase} />

        <div className="app">
          <aside className="queue">
            <p className="section-label">Case queue</p>
            {cases.map((c) => (
              <CaseCard key={c.id} c={c} onStart={startCall} onDemo={runDemo} onPreview={preview} />
            ))}
            <div className="panel preview-panel">
              <div className="pbody">
                <p className="section-label">What the agent will say</p>
                <Preview vars={vars} />
              </div>
            </div>
          </aside>

          <main className="stage">
            <div className="tabs">
              <button className={`tab ${tab === "overview" ? "active" : ""}`} onClick={() => setTab("overview")}>
                Overview
              </button>
              <button className={`tab ${tab === "transcript" ? "active" : ""}`} onClick={() => setTab("transcript")}>
                Transcript <span className="count">{turns.length}</span>
              </button>
            </div>

            {note && <div className="hint-banner">{note}</div>}

            {tab === "overview"
              ? <CloseLoopResult record={record} />
              : <div className="cards"><Transcript turns={turns} placeholder="No transcript yet — start a call or run Demo extraction." /></div>}
          </main>
        </div>
      </div>
    </>
  );
}
