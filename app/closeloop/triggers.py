"""Trigger engine (mock-friendly). Maps grounded facts to downstream actions.

Each branch is a seam where a real API call / webhook would go; set the env var to
fire for real, otherwise it stays in mock mode. Nothing fires on invented data.
"""
from __future__ import annotations

import os

import httpx

from .schema import ExtractedFacts, TriggeredAction

_EMAIL_KEYWORDS = ("kunde", "kunden", "email", "e-mail", "schriftlich",
                   "postfach", "anmelden", "anmeldung", "klaeren", "klären")


def _maybe_post(url_env: str, payload: dict) -> tuple[bool, str]:
    url = os.getenv(url_env)
    if not url:
        return False, "mock (kein Endpoint konfiguriert)"
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.post(url, json=payload)
        return True, f"POST {url} -> {r.status_code}"
    except Exception as exc:  # noqa: BLE001 - demo resilience
        return False, f"POST {url} fehlgeschlagen: {exc}"


def run_triggers(facts: ExtractedFacts, conversation_id: str) -> list[TriggeredAction]:
    actions: list[TriggeredAction] = []

    if facts.malo_id:
        _live, detail = _maybe_post(
            "NOMOS_WRITE_MALO_URL",
            {"conversation_id": conversation_id, "malo_id": facts.malo_id,
             "next_step": facts.next_step},
        )
        actions.append(TriggeredAction(
            type="write_malo", status="fired",
            detail=f"Marktlokation {facts.malo_id} ins System geschrieben. [{detail}]",
            target=facts.malo_id,
        ))

    next_lower = (facts.next_step or "").lower()
    if any(k in next_lower for k in _EMAIL_KEYWORDS):
        _live, detail = _maybe_post(
            "NOMOS_EMAIL_AGENT_URL",
            {"conversation_id": conversation_id, "reason": facts.stuck_reason,
             "next_step": facts.next_step},
        )
        actions.append(TriggeredAction(
            type="start_email_agent", status="fired",
            detail=f"Email-Agent ausgeloest fuer Kundenkontakt. [{detail}]",
            target="email_agent",
        ))

    if facts.needs_human:
        actions.append(TriggeredAction(
            type="flag_human_review", status="flagged",
            detail=("Fuer manuelle Pruefung markiert (needs_human=true). "
                    "Es wurde nichts erfunden -- offene Felder bleiben leer."),
            target="human_queue",
        ))

    if not actions:
        actions.append(TriggeredAction(
            type="none", status="skipped",
            detail="Keine Aktion noetig -- keine belastbaren Fakten zum Handeln.",
        ))
    return actions
