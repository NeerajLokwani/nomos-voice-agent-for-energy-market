"""Fact extraction with a strict never-fabricate rule.

  1. Take ElevenLabs' auto-extracted `analysis` fields as candidates.
  2. Ground every candidate against the actual transcript. If a value cannot be
     traced back to something that was said, drop it to None.
  3. For numeric fields (MaLo, ticket) run a deterministic extractor over the
     transcript, including German spoken-digit readbacks ("acht acht sieben ..."),
     so we recover the final corrected number even after back-and-forth.
  4. needs_human and analysis_confidence are derived, never invented.
"""
from __future__ import annotations

import re
from typing import Optional

from .schema import ExtractedFacts, WebhookPayload

_GERMAN_DIGITS = {
    "null": "0", "eins": "1", "ein": "1", "eine": "1", "zwei": "2", "zwo": "2",
    "drei": "3", "vier": "4", "fuenf": "5", "fünf": "5", "sechs": "6",
    "sieben": "7", "acht": "8", "neun": "9",
}

MALO_LEN = 11


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _agent_user_text(payload: WebhookPayload) -> tuple[str, str, str]:
    full, user, agent = [], [], []
    for turn in payload.transcript:
        m = _normalize(turn.message)
        full.append(m)
        (user if turn.role == "user" else agent).append(m)
    return " ".join(full), " ".join(user), " ".join(agent)


def _digit_runs_from_german(text: str) -> list[str]:
    tokens = re.findall(r"[a-zäöü]+", text)
    runs: list[str] = []
    current: list[str] = []
    for tok in tokens:
        if tok in _GERMAN_DIGITS:
            current.append(_GERMAN_DIGITS[tok])
        elif current:
            runs.append("".join(current))
            current = []
    if current:
        runs.append("".join(current))
    return runs


def _digit_runs_from_numerals(text: str) -> list[str]:
    runs: list[str] = []
    for m in re.finditer(r"(?:\d\s+){2,}\d", text):
        runs.append(re.sub(r"\s+", "", m.group()))
    for m in re.finditer(r"\d{2,}", text):
        runs.append(m.group())
    return runs


def _all_digit_runs(text: str) -> list[str]:
    return _digit_runs_from_german(text) + _digit_runs_from_numerals(text)


def _find_malo_in_transcript(full_text: str) -> Optional[str]:
    candidates = [r for r in _all_digit_runs(full_text) if len(r) == MALO_LEN]
    return candidates[-1] if candidates else None  # last = most recent/corrected


def _digits_only(value: Optional[str]) -> str:
    return re.sub(r"\D", "", value or "")


def _ground_malo(candidate: Optional[str], full_text: str, notes: list[str]) -> Optional[str]:
    transcript_malo = _find_malo_in_transcript(full_text)
    cand_digits = _digits_only(candidate)

    if cand_digits and len(cand_digits) == MALO_LEN:
        spoken_runs = set(_all_digit_runs(full_text))
        if cand_digits in spoken_runs or cand_digits in full_text:
            if transcript_malo and transcript_malo != cand_digits:
                notes.append(
                    f"MaLo: analysis sagt {cand_digits}, Transkript endet auf "
                    f"{transcript_malo} -> Transkript-Wert bevorzugt."
                )
                return transcript_malo
            return cand_digits
        notes.append(f"MaLo {cand_digits} aus analysis nicht im Transkript belegt -> verworfen.")

    if transcript_malo:
        notes.append(f"MaLo {transcript_malo} aus Transkript-Readback rekonstruiert.")
        return transcript_malo

    if cand_digits and len(cand_digits) != MALO_LEN:
        notes.append(
            f"MaLo-Kandidat {cand_digits} hat {len(cand_digits)} statt {MALO_LEN} Stellen -> verworfen."
        )
    return None


def _ground_freetext(candidate: Optional[str], field: str,
                     ref_text: str, notes: list[str]) -> Optional[str]:
    if not candidate or not candidate.strip():
        return None
    cand = _normalize(candidate)
    words = [w for w in re.findall(r"[a-zäöü]+", cand) if len(w) > 3]
    if not words:
        return candidate.strip()
    overlap = sum(1 for w in words if w in ref_text)
    if overlap / len(words) >= 0.2 or overlap >= 2:
        return candidate.strip()
    notes.append(f"{field}: zu wenig Rueckhalt im Transkript (Overlap {overlap}/{len(words)}) -> verworfen.")
    return None


def _ground_ticket(candidate: Optional[str], full_text: str, notes: list[str]) -> Optional[str]:
    if not candidate:
        return None
    norm_cand = re.sub(r"[^a-z0-9]", "", candidate.lower())
    norm_full = re.sub(r"[^a-z0-9]", "", full_text)
    if norm_cand and norm_cand in norm_full:
        return candidate.strip()
    notes.append(f"Ticket/Vorgangsnummer {candidate} nicht im Transkript belegt -> verworfen.")
    return None


def extract_facts(payload: WebhookPayload) -> ExtractedFacts:
    notes: list[str] = []
    full_text, user_text, _agent_text = _agent_user_text(payload)
    a = payload.analysis

    malo = _ground_malo(a.malo_id, full_text, notes)
    stuck = _ground_freetext(a.stuck_reason, "stuck_reason", user_text, notes)
    nxt = _ground_freetext(a.next_step, "next_step", full_text, notes)
    ticket = _ground_ticket(a.ticket_number, full_text, notes)

    core_present = [bool(malo), bool(stuck), bool(nxt)]
    score = sum(core_present) / len(core_present)
    needs_human = not (stuck or nxt) or not malo
    confidence = round(0.15 + 0.85 * score, 2)
    if not payload.transcript:
        confidence = 0.0
        needs_human = True
        notes.append("Leeres Transkript -> needs_human.")

    return ExtractedFacts(
        malo_id=malo,
        stuck_reason=stuck,
        next_step=nxt,
        ticket_number=ticket,
        needs_human=needs_human,
        analysis_confidence=confidence,
        grounding_notes=notes,
        source="deterministic",
    )
