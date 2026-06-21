const STEPS = [
  { key: "call", label: "Call", icon: "📞" },
  { key: "talk", label: "Conversation", icon: "💬" },
  { key: "facts", label: "Facts", icon: "🔎" },
  { key: "note", label: "Note", icon: "📝" },
  { key: "email", label: "Email", icon: "✉️" },
  { key: "triggered", label: "Triggered", icon: "⚡" },
];

// activeIndex: how far the close-the-loop pipeline has progressed (0..6).
export default function PipelineStepper({ activeIndex }: { activeIndex: number }) {
  return (
    <div className="pipeline">
      {STEPS.map((s, i) => {
        const cls = i < activeIndex ? "pstep done" : i === activeIndex ? "pstep active" : "pstep";
        return (
          <div key={s.key} className={cls}>
            <div className="pdot">{i < activeIndex ? "✓" : s.icon}</div>
            <div className="plbl">{s.label}</div>
          </div>
        );
      })}
    </div>
  );
}
