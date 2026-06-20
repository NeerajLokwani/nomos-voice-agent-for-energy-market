import { spellDE, toTiles } from "../lib/digits.ts";

interface Props {
  value: string | null | undefined;
  spoken?: boolean;
}

// The signature element: a long ID rendered as individual digit tiles, with the
// spoken German underneath — exactly how the agent reads it back on the call.
export default function Digits({ value, spoken = false }: Props) {
  if (!value) return <span className="empty">—</span>;
  return (
    <>
      <div className="digits">
        {toTiles(value).map((t, i) => (
          <span key={i} className={t.alpha ? "d alpha" : "d"}>{t.ch}</span>
        ))}
      </div>
      {spoken && <div className="spoken">„{spellDE(value)}"</div>}
    </>
  );
}
