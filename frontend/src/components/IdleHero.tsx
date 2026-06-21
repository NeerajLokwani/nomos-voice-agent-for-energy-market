import { useRef } from "react";

const BARS = Array.from({ length: 28 });
const prefersReduced = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/**
 * The idle "call stage": a glowing voice waveform on an electric-grid backdrop.
 * Shown in the Overview when no result is loaded — turns dead space into an
 * on-brand invitation to start a call. Pointer-parallax gives it depth (3D).
 */
export default function IdleHero({ connecting }: { connecting: boolean }) {
  const stageRef = useRef<HTMLDivElement | null>(null);

  function onMove(e: React.PointerEvent) {
    if (prefersReduced() || !stageRef.current) return;
    const r = stageRef.current.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    stageRef.current.style.transform = `rotateY(${px * 9}deg) rotateX(${-py * 9}deg)`;
  }
  function onLeave() {
    if (stageRef.current) stageRef.current.style.transform = "rotateY(0deg) rotateX(0deg)";
  }

  return (
    <div className="hero-perspective" onPointerMove={onMove} onPointerLeave={onLeave}>
      <div className="hero" ref={stageRef}>
        <div className="hero-grid" />
        <div className="hero-glow" />

        <div className="hero-rings">
          <span /><span /><span />
        </div>

        <div className="hero-content">
          <div className="wavebig" aria-hidden="true">
            {BARS.map((_, i) => (
              <span key={i} style={{ animationDelay: `${(i % 7) * 0.09}s` }} />
            ))}
          </div>
          <h2>{connecting ? "On the line…" : "Ready to clear a case"}</h2>
          <p>
            {connecting
              ? "The agent is navigating the menu and speaking. Facts, note, email and actions fill in here when the call ends."
              : "Pick a case, then Start call to dial the grid operator — or Demo extraction to watch the whole pipeline run."}
          </p>
        </div>

        <span className="chip-float f1">Spricht Deutsch</span>
        <span className="chip-float f2">Liest Nummern Ziffer für Ziffer</span>
        <span className="chip-float f3">Erfindet nichts</span>
      </div>
    </div>
  );
}
