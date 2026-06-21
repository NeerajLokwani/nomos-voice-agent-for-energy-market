"""Pydantic models for the close-the-loop pipeline.

The webhook payload mirrors what ElevenLabs Conversational AI sends after a call.
Inbound models are permissive (extra fields allowed) so we never drop a call just
because ElevenLabs added a field.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Inbound webhook payload (from ElevenLabs)
# --------------------------------------------------------------------------- #
class TranscriptTurn(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: Literal["agent", "user"]
    message: str = ""


class ElevenLabsAnalysis(BaseModel):
    """Auto-extracted fields ElevenLabs produces. All optional / nullable."""
    model_config = ConfigDict(extra="allow")
    malo_id: Optional[str] = None
    stuck_reason: Optional[str] = None
    next_step: Optional[str] = None
    ticket_number: Optional[str] = None


class WebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    conversation_id: str
    agent_id: Optional[str] = None
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    analysis: ElevenLabsAnalysis = Field(default_factory=ElevenLabsAnalysis)
    metadata: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Extracted facts (our schema — never fabricated)
# --------------------------------------------------------------------------- #
class ExtractedFacts(BaseModel):
    malo_id: Optional[str] = None
    stuck_reason: Optional[str] = None
    next_step: Optional[str] = None
    ticket_number: Optional[str] = None
    vorgang_nr: Optional[str] = None  # Nomos-internal, always assigned
    needs_human: bool = True
    analysis_confidence: float = 0.0
    grounding_notes: list[str] = Field(default_factory=list)
    source: str = "deterministic"  # or "llm+deterministic"


# --------------------------------------------------------------------------- #
# Trigger / action engine output
# --------------------------------------------------------------------------- #
ActionStatus = Literal["fired", "skipped", "flagged"]


class TriggeredAction(BaseModel):
    type: str
    status: ActionStatus
    detail: str
    target: Optional[str] = None
    fired_at: datetime = Field(default_factory=_now)


# --------------------------------------------------------------------------- #
# Full conversation record (what the dashboard consumes)
# --------------------------------------------------------------------------- #
class EmailDraft(BaseModel):
    subject: str = ""
    body: str = ""
    needs_human: bool = True


class ConversationRecord(BaseModel):
    conversation_id: str
    call_id: Optional[str] = None       # our internal id (from dynamic variables)
    agent_id: Optional[str] = None
    case: Optional[str] = None
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    raw_analysis: ElevenLabsAnalysis = Field(default_factory=ElevenLabsAnalysis)
    facts: ExtractedFacts = Field(default_factory=ExtractedFacts)
    note: str = ""
    email_draft: EmailDraft = Field(default_factory=EmailDraft)
    actions: list[TriggeredAction] = Field(default_factory=list)
    received_at: datetime = Field(default_factory=_now)
