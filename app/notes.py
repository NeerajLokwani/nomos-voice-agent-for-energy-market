"""Generate the plain-German back-office note (+ short English gloss).

This is "exactly what our back office would write down" — a couple of sentences, plain
German, stating the reason and the next step. The English gloss is for the judges/demo.
"""
from __future__ import annotations

from typing import Optional

from .schema import MeterStatus, NextAction


def _sentence(text: str) -> str:
    """Ensure a fragment ends with sentence punctuation."""
    text = text.strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text

_NEXT_DE = {
    NextAction.trigger_signup_step: "Korrigierte MaLo übernommen, Anmeldung wird neu angestoßen.",
    NextAction.contact_customer: "Kunde wird kontaktiert.",
    NextAction.create_new_anlage: "Neue Anlage erforderlich, zurück zum Kunden.",
    NextAction.await_processing: "Anmeldung liegt korrekt vor und wird bearbeitet, wird verfolgt.",
    NextAction.needs_human_followup: "Manuelle Nachverfolgung durch Kollegen nötig.",
    NextAction.none: "Kein nächster Schritt erfasst.",
}

_NEXT_EN = {
    NextAction.trigger_signup_step: "Corrected MaLo recorded; re-triggering the registration.",
    NextAction.contact_customer: "Customer will be contacted.",
    NextAction.create_new_anlage: "New connection (Anlage) needed; back to the customer.",
    NextAction.await_processing: "Registration is valid and in process; tracking it.",
    NextAction.needs_human_followup: "Needs manual follow-up by a colleague.",
    NextAction.none: "No next step captured.",
}


def build_notes(
    case: dict,
    reason: str,
    next_action: NextAction,
    corrected_malo: Optional[str] = None,
    vorgangsnummer: Optional[str] = None,
    meter_status: MeterStatus = MeterStatus.unknown,
) -> tuple:
    """Return (note_de, note_en_gloss)."""
    vnb = case.get("vnb_name", "der Netzbetreiber")
    ort = case.get("lieferstelle", "")

    de_parts = [f"Anruf bei {vnb} zur Lieferstelle {ort}."]
    if reason:
        de_parts.append(_sentence(f"Ergebnis: {reason}"))
    if meter_status == MeterStatus.removed:
        de_parts.append("Zähler ist ausgebaut.")
    if corrected_malo:
        de_parts.append(f"Korrigierte MaLo: {corrected_malo}.")
    if vorgangsnummer:
        de_parts.append(f"Vorgangsnummer: {vorgangsnummer}.")
    de_parts.append("Nächster Schritt: " + _NEXT_DE.get(next_action, _NEXT_DE[NextAction.none]))
    note_de = " ".join(de_parts)

    en_parts = [f"Call to {vnb} re delivery point {ort}."]
    if reason:
        en_parts.append(_sentence(f"Outcome: {reason}"))
    if corrected_malo:
        en_parts.append(f"Corrected MaLo: {corrected_malo}.")
    if vorgangsnummer:
        en_parts.append(f"Reference no.: {vorgangsnummer}.")
    en_parts.append("Next step: " + _NEXT_EN.get(next_action, _NEXT_EN[NextAction.none]))
    note_en = " ".join(en_parts)

    return note_de, note_en
