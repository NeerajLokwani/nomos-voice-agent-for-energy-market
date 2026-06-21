"""Optional LLM refinement over the deterministic extraction.

Disabled unless NOMOS_LLM_PROVIDER=openai and OPENAI_API_KEY are set. The LLM may
only refine the phrasing of grounded free-text fields or recover a reason the
deterministic pass missed -- it is told to return null rather than invent. The
deterministic MaLo (numeric ground truth) is never overridden.
"""
from __future__ import annotations

import json
import os

from .schema import ExtractedFacts, WebhookPayload

_SYSTEM = (
    "Du extrahierst Fakten aus einem deutschen Telefon-Transkript zwischen einem "
    "KI-Agenten (Nomos) und einem Sachbearbeiter eines Stromnetzbetreibers. "
    "REGEL: Erfinde nichts. Wenn eine Information nicht klar im Transkript steht, "
    "gib null zurueck. Gib NUR JSON zurueck mit den Schluesseln "
    "stuck_reason, next_step (jeweils kurzer deutscher Satz oder null)."
)


def refine_facts(payload: WebhookPayload, facts: ExtractedFacts) -> ExtractedFacts:
    if os.getenv("NOMOS_LLM_PROVIDER") != "openai" or not os.getenv("OPENAI_API_KEY"):
        return facts
    try:
        from openai import OpenAI  # local import so the dep stays optional
    except ImportError:
        return facts

    transcript_text = "\n".join(f"{t.role}: {t.message}" for t in payload.transcript)
    try:
        client = OpenAI()
        resp = client.chat.completions.create(
            model=os.getenv("NOMOS_LLM_MODEL", "gpt-5.5"),
            max_completion_tokens=2000,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": transcript_text},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        text = text[text.find("{"): text.rfind("}") + 1]
        data = json.loads(text)
    except Exception as exc:  # noqa: BLE001
        facts.grounding_notes.append(f"LLM-Pass uebersprungen: {exc}")
        return facts

    refined = facts.model_copy()
    if data.get("stuck_reason") and not facts.stuck_reason:
        refined.stuck_reason = str(data["stuck_reason"]).strip()
        refined.grounding_notes.append("stuck_reason via LLM-Pass ergaenzt.")
    if data.get("next_step") and not facts.next_step:
        refined.next_step = str(data["next_step"]).strip()
        refined.grounding_notes.append("next_step via LLM-Pass ergaenzt.")
    refined.source = "llm+deterministic"
    refined.needs_human = not (refined.stuck_reason or refined.next_step) or not refined.malo_id
    return refined
