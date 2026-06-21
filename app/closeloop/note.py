"""German back-office note + email draft, strictly templated from grounded facts."""
from __future__ import annotations

from .schema import EmailDraft, ExtractedFacts


def _malo_readback(malo: str) -> str:
    return " ".join(malo)  # digit-by-digit, the way it was confirmed on the call


def generate_note(facts: ExtractedFacts) -> str:
    parts: list[str] = []
    if facts.malo_id:
        parts.append(
            f"Telefonische Klaerung zur Marktlokation {facts.malo_id} "
            f"(Ziffern: {_malo_readback(facts.malo_id)})."
        )
    else:
        parts.append("Telefonische Klaerung; Marktlokation konnte nicht bestaetigt werden.")

    if facts.stuck_reason:
        parts.append(f"Ursache laut Netzbetreiber: {facts.stuck_reason}.")
    else:
        parts.append("Es wurde keine eindeutige Ursache genannt.")

    if facts.next_step:
        parts.append(f"Naechster Schritt: {facts.next_step}.")
    if facts.ticket_number:
        parts.append(f"Vorgangsnummer (Netzbetreiber): {facts.ticket_number}.")
    if facts.vorgang_nr:
        parts.append(f"Nomos-Vorgang: {facts.vorgang_nr}.")
    if facts.needs_human:
        parts.append("Hinweis: Bearbeitung durch Sachbearbeiter erforderlich (offene Punkte).")

    return " ".join(parts)


def generate_email_draft(facts: ExtractedFacts) -> EmailDraft:
    subject = (
        f"Nomos – Klärung Marktlokation {facts.malo_id}"
        if facts.malo_id else "Nomos – Klärung gestörte Anmeldung (Rückfrage)"
    )
    lines = ["Sehr geehrte Damen und Herren,", "",
             "im Nachgang zu unserem Telefonat fassen wir den Sachstand zusammen:", ""]
    if facts.malo_id:
        lines.append(f"• Marktlokation: {facts.malo_id}")
    if facts.stuck_reason:
        lines.append(f"• Sachstand: {facts.stuck_reason}")
    if facts.next_step:
        lines.append(f"• Nächster Schritt: {facts.next_step}")
    if facts.ticket_number:
        lines.append(f"• Vorgangsnummer (Netzbetreiber): {facts.ticket_number}")
    if facts.vorgang_nr:
        lines.append(f"• Nomos-Vorgang: {facts.vorgang_nr}")
    if not (facts.stuck_reason or facts.next_step):
        lines.append("• Es konnte am Telefon keine abschließende Klärung erzielt werden.")
    lines += ["", "Für Rückfragen stehen wir gern zur Verfügung.", "",
              "Mit freundlichen Grüßen", "Nomos"]

    return EmailDraft(subject=subject, body="\n".join(lines), needs_human=facts.needs_human)
