// German digit names — mirrors app/digits.py so the UI speaks IDs the same way the
// agent does on the phone. This is the product's signature: one digit at a time.
import type { DigitTile } from "./types";

const DE: Record<string, string> = {
  "0": "null", "1": "eins", "2": "zwei", "3": "drei", "4": "vier",
  "5": "fünf", "6": "sechs", "7": "sieben", "8": "acht", "9": "neun",
};

const chars = (s: string | null | undefined): string[] =>
  [...String(s ?? "")].filter((c) => /\w/.test(c));

export const spellDE = (s: string | null | undefined): string =>
  chars(s).map((c) => DE[c] ?? c.toUpperCase()).join(" · ");

export const toTiles = (s: string | null | undefined): DigitTile[] =>
  chars(s).map((c) => ({ ch: c.toUpperCase(), alpha: /[a-z]/i.test(c) }));
