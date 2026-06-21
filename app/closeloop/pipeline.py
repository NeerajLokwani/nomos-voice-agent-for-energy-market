"""Close-the-loop pipeline: payload -> facts -> note -> email -> triggers -> record."""
from __future__ import annotations

import hashlib

from .extract import extract_facts
from .llm import refine_facts
from .note import generate_email_draft, generate_note
from .schema import ConversationRecord, WebhookPayload
from .triggers import run_triggers


def _vorgang_nr(seed: str) -> str:
    """Stable Nomos-internal Vorgangsnummer (separate from the clerk's ticket)."""
    n = int(hashlib.sha1(seed.encode("utf-8")).hexdigest(), 16) % 100000
    return f"NOM-2026-{n:05d}"


def process_call(payload: WebhookPayload) -> ConversationRecord:
    facts = extract_facts(payload)
    facts = refine_facts(payload, facts)  # no-op unless OpenAI LLM pass enabled
    case = payload.metadata.get("case") or ""
    facts.vorgang_nr = _vorgang_nr(f"{case}|{payload.conversation_id}|{facts.malo_id or ''}")
    note = generate_note(facts)
    email_draft = generate_email_draft(facts)
    actions = run_triggers(facts, payload.conversation_id)

    return ConversationRecord(
        conversation_id=payload.conversation_id,
        call_id=payload.metadata.get("call_id"),
        agent_id=payload.agent_id,
        case=payload.metadata.get("case"),
        transcript=payload.transcript,
        raw_analysis=payload.analysis,
        facts=facts,
        note=note,
        email_draft=email_draft,
        actions=actions,
    )
