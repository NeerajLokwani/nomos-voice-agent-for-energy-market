"""The fixed structured result of a clearing call.

This is what "closing the loop" produces: typed facts a downstream workflow can key
off, plus a plain-German back-office note (what Nomos staff would actually write) and
a short English gloss for readability.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class CallStatus(str, Enum):
    resolved = "resolved"        # real reason + correct next step captured
    partial = "partial"          # some info gathered, not fully cleared
    needs_human = "needs_human"  # could not proceed; flagged for a human colleague


class MeterStatus(str, Enum):
    active = "active"
    removed = "removed"          # "ausgebaut" (e.g. Baustromzähler)
    unknown = "unknown"


class NextAction(str, Enum):
    none = "none"
    trigger_signup_step = "trigger_signup_step"      # write ID / advance sign-up
    contact_customer = "contact_customer"            # hand to email agent
    create_new_anlage = "create_new_anlage"          # new connection needed
    await_processing = "await_processing"            # registration in process, track it
    needs_human_followup = "needs_human_followup"


class CallResult(BaseModel):
    case_id: str
    call_id: Optional[str] = None
    status: CallStatus
    reason: str = Field("", description="The real reason the case was stuck, in plain language.")
    corrected_malo: Optional[str] = None
    vorgangsnummer: Optional[str] = None
    meter_status: MeterStatus = MeterStatus.unknown
    next_action: NextAction = NextAction.none
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    note_de: str = Field("", description="Plain-German back-office note.")
    note_en_gloss: str = Field("", description="Short English gloss for judges/demo.")
    transcript_ref: Optional[str] = None
    triggered: List[str] = Field(default_factory=list, description="Mock services fired.")
    reconciliation: Optional[dict] = None
    email_status: Optional[str] = None
    email_ref: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class ReconciliationItem(BaseModel):
    field: str
    old: str = ""
    new: str = ""
    kind: str


class ReconciliationReport(BaseModel):
    case_id: str
    items: List[ReconciliationItem] = Field(default_factory=list)
    verification_status: Literal["verifiziert", "abweichung", "mensch_noetig"]
    summary_points: List[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
