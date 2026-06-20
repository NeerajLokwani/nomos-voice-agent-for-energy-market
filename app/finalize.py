"""Turn the accumulated live findings into a structured CallResult, write the note,
and fire the appropriate mock downstream action.

Called by the ElevenLabs post-call webhook (or the manual /calls/{id}/finalize route
used by the simulator/demo).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .email_agent import send_summary_email
from .fixtures import get_case
from .notes import build_notes
from .reconcile import reconcile
from .schema import CallResult, CallStatus, MeterStatus, NextAction
from .store import get_live, save_result
from .summary import build_email_summary
from .triggers import mock_email_agent, mock_signup_step, mock_track_vorgang


def _coerce_meter(value: Optional[str]) -> MeterStatus:
    try:
        return MeterStatus(value) if value else MeterStatus.unknown
    except ValueError:
        return MeterStatus.unknown


def _coerce_status(value: Optional[str]) -> CallStatus:
    try:
        return CallStatus(value) if value else CallStatus.partial
    except ValueError:
        return CallStatus.partial


def _derive_next_action(
    explicit: Optional[str],
    status: CallStatus,
    corrected_malo: Optional[str],
    vorgangsnummer: Optional[str],
    meter_status: MeterStatus,
) -> NextAction:
    if explicit:
        try:
            return NextAction(explicit)
        except ValueError:
            pass  # fall through to inference if the agent gave free text
    if status == CallStatus.needs_human:
        return NextAction.needs_human_followup
    if corrected_malo:
        return NextAction.trigger_signup_step
    if meter_status == MeterStatus.removed:
        return NextAction.create_new_anlage
    if vorgangsnummer:
        return NextAction.await_processing
    if status == CallStatus.resolved:
        return NextAction.contact_customer
    return NextAction.none


def _fire_triggers(case_id: str, result: CallResult) -> None:
    na = result.next_action
    if na in (NextAction.create_new_anlage, NextAction.contact_customer):
        result.triggered.append(mock_email_agent(case_id, result.reason))
    elif na == NextAction.trigger_signup_step and result.corrected_malo:
        result.triggered.append(mock_signup_step(case_id, result.corrected_malo))
    elif na == NextAction.await_processing and result.vorgangsnummer:
        result.triggered.append(mock_track_vorgang(case_id, result.vorgangsnummer))


def finalize_call(call_id: str) -> CallResult:
    live = get_live(call_id)
    if live is None:
        raise KeyError(call_id)
    case_id = live.get("case_id", "")
    case = get_case(case_id) or {}
    findings = live.get("findings", {})
    end = live.get("end", {})

    status = _coerce_status(end.get("status"))
    meter_status = _coerce_meter(findings.get("meter_status"))
    corrected_malo = findings.get("corrected_malo")
    vorgangsnummer = findings.get("vorgangsnummer")
    reason = findings.get("reason") or end.get("summary") or ""

    next_action = _derive_next_action(
        end.get("next_action"), status, corrected_malo, vorgangsnummer, meter_status
    )
    note_de, note_en = build_notes(
        case, reason, next_action, corrected_malo, vorgangsnummer, meter_status
    )

    result = CallResult(
        case_id=case_id,
        call_id=call_id,
        status=status,
        reason=reason,
        corrected_malo=corrected_malo,
        vorgangsnummer=vorgangsnummer,
        meter_status=meter_status,
        next_action=next_action,
        confidence=0.9 if status == CallStatus.resolved else 0.5,
        note_de=note_de,
        note_en_gloss=note_en,
        transcript_ref=call_id,
        started_at=_parse_dt(live.get("started_at")),
        ended_at=datetime.now(timezone.utc),
    )
    _fire_triggers(case_id, result)

    report = reconcile(case, result)
    result.reconciliation = report.model_dump(mode="json")
    summary = build_email_summary(case, result, report)
    try:
        result.email_ref = send_summary_email(
            summary["subject"],
            summary["body_text"],
            summary.get("body_html"),
        )
        result.email_status = "verschickt"
    except Exception as exc:
        result.email_status = f"fehler: {exc.__class__.__name__}"

    save_result(result)
    return result


def _parse_dt(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
