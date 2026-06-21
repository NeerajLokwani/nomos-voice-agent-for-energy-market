import type { TranscriptTurn } from "../lib/types.ts";

export default function Transcript({ turns, placeholder }: { turns: TranscriptTurn[]; placeholder: string }) {
  if (!turns.length) {
    return (
      <section className="card span2">
        <span className="empty">{placeholder}</span>
      </section>
    );
  }
  return (
    <section className="card span2">
      <p className="card-title">Call transcript</p>
      <div className="transcript-list">
        {turns.map((t, i) => {
          const who = t.role.includes("agent") ? "agent" : "clerk";
          return (
            <div key={i} className={`turn ${who}`}>
              <span className="who">{who}</span>
              <span className="msg">{t.text}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
