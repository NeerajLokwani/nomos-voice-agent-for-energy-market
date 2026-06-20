"""Live server-tools the ElevenLabs agent calls mid-conversation.

Design constraint: every response is tiny and fast — latency is what makes Helga hang
up. validate_id is a pure local computation; the others just accumulate state into the
live store, to be finalized by the post-call pipeline.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .store import append_transcript, get_live, set_live
from .validation import validate

router = APIRouter(prefix="/tools", tags=["live-tools"])


def _findings(call_id: str) -> dict:
    live = get_live(call_id)
    if live is None:
        raise HTTPException(status_code=404, detail="unknown call")
    return live.setdefault("findings", {})


class ValidateIdReq(BaseModel):
    call_id: str
    id_type: str  # "malo" | "vorgangsnummer"
    value: str


@router.post("/validate_id")
def validate_id(req: ValidateIdReq) -> dict:
    _findings(req.call_id)  # ensures call exists
    result = validate(req.id_type, req.value)
    # Hand the agent a ready-to-speak, digit-by-digit form for readback.
    return {
        "ok": bool(result["format_ok"]),
        "spoken": result["spoken"],
        "format_ok": result["format_ok"],
        "check_digit_ok": result["check_digit_ok"],
        "hint": (
            "Lies diese Nummer Ziffer für Ziffer zurück und lass dir bestätigen, dass "
            "sie stimmt."
        ),
    }


class RecordFindingReq(BaseModel):
    call_id: str
    reason: Optional[str] = None
    corrected_malo: Optional[str] = None
    vorgangsnummer: Optional[str] = None
    meter_status: Optional[str] = None  # active | removed | unknown


@router.post("/record_finding")
def record_finding(req: RecordFindingReq) -> dict:
    findings = _findings(req.call_id)
    for key in ("reason", "corrected_malo", "vorgangsnummer", "meter_status"):
        val = getattr(req, key)
        if val:
            findings[key] = val
    set_live(req.call_id, findings=findings)
    return {"ok": True, "recorded": {k: v for k, v in findings.items()}}


class EndCallReq(BaseModel):
    call_id: str
    status: str  # resolved | partial | needs_human
    next_action: Optional[str] = None
    summary: Optional[str] = None


@router.post("/end_call")
def end_call(req: EndCallReq) -> dict:
    if get_live(req.call_id) is None:
        raise HTTPException(status_code=404, detail="unknown call")
    set_live(
        req.call_id,
        status="ended",
        end={
            "status": req.status,
            "next_action": req.next_action,
            "summary": req.summary,
        },
    )
    return {"ok": True, "status": req.status}


class GetCaseContextReq(BaseModel):
    call_id: str


@router.post("/get_case_context")
def get_case_context(req: GetCaseContextReq) -> dict:
    """Safety-net only — the case normally arrives via dynamic variables at call start."""
    live = get_live(req.call_id)
    if live is None:
        raise HTTPException(status_code=404, detail="unknown call")
    return {"ok": True, "dynamic_variables": live.get("dynamic_variables", {})}
