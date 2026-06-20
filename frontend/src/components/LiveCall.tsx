import type { LiveState } from "../lib/types.ts";

const STEPS = ["Dial", "Menu", "Clerk", "Cleared"];

function Stages({ index }: { index: number }) {
  return (
    <div className="stages">
      {STEPS.map((s, i) => {
        const cls = i < index ? "step done" : i === index ? "step active" : "step";
        return (
          <div key={s} className={cls}>
            <div className="dot">{i < index ? "✓" : i + 1}</div>
            <div className="lbl">{s}</div>
          </div>
        );
      })}
    </div>
  );
}

interface Props {
  live: LiveState;
  stageIndex: number;
  onSimulate: (() => void) | null;
}

export default function LiveCall({ live, stageIndex, onSimulate }: Props) {
  const on = live.on;
  const turns = live.transcript || [];
  return (
    <section className="panel">
      <div className="live-head">
        <span className={on ? "pulse on" : "pulse"} />
        <span className="title">Live call</span>
        <span className={on ? "wave on" : "wave"}>
          {Array.from({ length: 6 }).map((_, i) => <span key={i} />)}
        </span>
        <span className="meta">{live.meta || "idle"}</span>
      </div>
      <Stages index={stageIndex} />
      <div className="transcript">
        {turns.length === 0 && !live.note && (
          <span className="empty">{live.placeholder || "Pick a case to place a clearing call."}</span>
        )}
        {turns.map((t, i) => {
          const who = t.role.includes("agent") ? "agent" : "clerk";
          return (
            <div key={i} className={`turn ${who}`}>
              <span className="who">{who}</span>
              <span className="msg">{t.text}</span>
            </div>
          );
        })}
        {live.note && <span className="empty">{live.note}</span>}
      </div>
      {onSimulate && (
        <div style={{ padding: "0 20px 18px" }}>
          <button className="btn-ghost" onClick={onSimulate}>Simulate outcome →</button>
        </div>
      )}
    </section>
  );
}
