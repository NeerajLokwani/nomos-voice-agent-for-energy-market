"""Abgleich zwischen bekannten Falldaten und strukturiertem Anrufergebnis."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from .schema import (
    CallResult,
    CallStatus,
    MeterStatus,
    NextAction,
    ReconciliationItem,
    ReconciliationReport,
)
from .validation import validate_malo, validate_vorgangsnummer


def reconcile(case: dict, result: CallResult) -> ReconciliationReport:
    """Vergleiche Fixture-Falldaten mit einem CallResult und fasse den Befund zusammen."""
    items: list[ReconciliationItem] = []

    _add_malo_compare(items, case, result.corrected_malo)
    _add_malo_validation(items, result.corrected_malo)

    expected_meter = _expected_meter_status(case)
    _add_compare(items, "meter_status", expected_meter, result.meter_status)

    _add_compare(items, "vorgangsnummer", case.get("vorgangsnummer"), result.vorgangsnummer)
    _add_vorgangsnummer_validation(items, result.vorgangsnummer)

    _add_reason_check(items, case.get("statustext"), result.reason)

    expected_next_action = _expected_next_action(case)
    _add_compare(items, "next_action", expected_next_action, result.next_action)

    _add_date_check(items, "anmeldung_datum", case.get("anmeldung_datum"), result)
    _add_date_check(items, "lieferbeginn", case.get("lieferbeginn"), result)
    _add_timestamp_check(items, "started_at", result.started_at)
    _add_timestamp_check(items, "ended_at", result.ended_at)

    verification_status = _verification_status(result, items)
    summary_points = _summary_points(items, verification_status)
    confidence = _confidence(result, items, verification_status)

    return ReconciliationReport(
        case_id=case.get("id") or result.case_id,
        items=items,
        verification_status=verification_status,
        summary_points=summary_points,
        confidence=confidence,
    )


def _add_compare(items: list[ReconciliationItem], field: str, old, new) -> None:
    old_s = _as_text(old)
    new_s = _as_text(new)
    if not old_s and not new_s:
        kind = "offen"
    elif not new_s:
        kind = "offen"
    elif not old_s:
        kind = "neu"
    elif _normalize(old_s) == _normalize(new_s):
        kind = "verifiziert"
    else:
        kind = "abweichung"
    items.append(ReconciliationItem(field=field, old=old_s, new=new_s, kind=kind))


def _add_malo_compare(items: list[ReconciliationItem], case: dict, corrected_malo: Optional[str]) -> None:
    old_s = _as_text(case.get("malo_id"))
    new_s = _as_text(corrected_malo)
    if not old_s and not new_s:
        kind = "offen"
    elif not new_s:
        kind = "offen"
    elif not old_s:
        kind = "neu"
    elif _normalize(old_s) == _normalize(new_s):
        kind = "verifiziert"
    elif _expected_next_action(case) == NextAction.trigger_signup_step.value:
        kind = "geaendert"
    else:
        kind = "abweichung"
    items.append(ReconciliationItem(field="malo_id<->corrected_malo", old=old_s, new=new_s, kind=kind))


def _add_malo_validation(items: list[ReconciliationItem], value: Optional[str]) -> None:
    if not value:
        items.append(ReconciliationItem(field="corrected_malo_format", old="", new="", kind="offen"))
        items.append(ReconciliationItem(field="corrected_malo_checksum", old="", new="", kind="offen"))
        return

    validation = validate_malo(value)
    items.append(
        ReconciliationItem(
            field="corrected_malo_format",
            old="11-stellig",
            new=validation["normalized"],
            kind="verifiziert" if validation["format_ok"] else "ungueltig",
        )
    )
    check_digit_ok = validation["check_digit_ok"]
    if check_digit_ok is True:
        kind = "verifiziert"
        new = "ok"
    elif check_digit_ok is False:
        kind = "hinweis"
        new = "nicht_ok"
    else:
        kind = "offen"
        new = ""
    items.append(
        ReconciliationItem(field="corrected_malo_checksum", old="", new=new, kind=kind)
    )


def _add_vorgangsnummer_validation(items: list[ReconciliationItem], value: Optional[str]) -> None:
    if not value:
        items.append(ReconciliationItem(field="vorgangsnummer_format", old="", new="", kind="offen"))
        return

    validation = validate_vorgangsnummer(value)
    items.append(
        ReconciliationItem(
            field="vorgangsnummer_format",
            old="mindestens 4 Zeichen",
            new=validation["normalized"],
            kind="verifiziert" if validation["format_ok"] else "ungueltig",
        )
    )


def _add_reason_check(items: list[ReconciliationItem], statustext, reason) -> None:
    old_s = _as_text(statustext)
    new_s = _as_text(reason)
    if not old_s and not new_s:
        kind = "offen"
    elif not new_s:
        kind = "offen"
    elif not old_s:
        kind = "neu"
    elif _has_text_overlap(old_s, new_s):
        kind = "verifiziert"
    else:
        kind = "geklaert"
    items.append(ReconciliationItem(field="reason/statustext", old=old_s, new=new_s, kind=kind))


def _add_date_check(
    items: list[ReconciliationItem],
    field: str,
    expected_date,
    result: CallResult,
) -> None:
    old_s = _as_text(expected_date)
    if not old_s:
        items.append(ReconciliationItem(field=field, old="", new="", kind="offen"))
        return

    haystack = " ".join(
        part
        for part in (result.reason, result.note_de, result.note_en_gloss)
        if part
    )
    new_s = old_s if old_s in haystack else ""
    kind = "verifiziert" if new_s else "offen"
    items.append(ReconciliationItem(field=field, old=old_s, new=new_s, kind=kind))


def _add_timestamp_check(
    items: list[ReconciliationItem],
    field: str,
    value: Optional[datetime],
) -> None:
    items.append(
        ReconciliationItem(
            field=field,
            old="",
            new=_as_text(value),
            kind="neu" if value else "offen",
        )
    )


def _verification_status(result: CallResult, items: list[ReconciliationItem]) -> str:
    if result.status == CallStatus.needs_human or result.next_action == NextAction.needs_human_followup:
        return "mensch_noetig"
    if any(item.field.startswith("corrected_malo") and item.kind == "ungueltig" for item in items):
        return "mensch_noetig"
    if any(item.kind in {"abweichung", "ungueltig"} for item in items):
        return "abweichung"
    return "verifiziert"


def _summary_points(items: list[ReconciliationItem], verification_status: str) -> list[str]:
    points: list[str] = []
    if verification_status == "mensch_noetig":
        points.append("Manuelle Prüfung nötig.")
    elif verification_status == "abweichung":
        points.append("Abweichungen zwischen Falldaten und Anrufergebnis gefunden.")
    else:
        points.append("Anrufergebnis gegen vorhandene Falldaten verifiziert.")

    for item in items:
        if item.kind == "abweichung":
            points.append(f"{item.field}: bekannt '{item.old}', neu '{item.new}'.")
        elif item.kind == "geaendert":
            points.append(f"{item.field}: geändert von '{item.old}' auf '{item.new}'.")
        elif item.kind == "ungueltig":
            points.append(f"{item.field}: Formatprüfung fehlgeschlagen ('{item.new}').")
        elif item.kind == "offen":
            points.append(f"{item.field}: offen.")
    return points


def _confidence(
    result: CallResult,
    items: list[ReconciliationItem],
    verification_status: str,
) -> float:
    score = result.confidence
    score -= 0.20 * sum(1 for item in items if item.kind == "abweichung")
    score -= 0.25 * sum(1 for item in items if item.kind == "ungueltig")
    score -= 0.03 * sum(1 for item in items if item.kind == "offen")
    if verification_status == "mensch_noetig":
        score = min(score, 0.4)
    return round(max(0.0, min(1.0, score)), 2)


def _expected_meter_status(case: dict) -> str:
    explicit = _as_text(case.get("meter_status"))
    if explicit:
        return explicit
    text = _case_text(case)
    if "ausgebaut" in text or "removed" in text:
        return MeterStatus.removed.value
    if "aktiv" in text or "active" in text:
        return MeterStatus.active.value
    return ""


def _expected_next_action(case: dict) -> str:
    explicit = _as_text(case.get("next_action"))
    if explicit:
        return explicit
    text = _case_text(case)
    if "neue anlage" in text or "new anlage" in text or "new connection" in text:
        return NextAction.create_new_anlage.value
    if "vorgangsnummer" in text or "in process" in text or "bearbeitet" in text:
        return NextAction.await_processing.value
    if "correct malo" in text or "korrigierte malo" in text or "get the correct malo" in text:
        return NextAction.trigger_signup_step.value
    return ""


def _case_text(case: dict) -> str:
    return " ".join(
        _as_text(case.get(key)).lower()
        for key in ("case_title", "statustext", "symptom", "goal")
        if case.get(key)
    )


def _has_text_overlap(left: str, right: str) -> bool:
    left_tokens = _meaningful_tokens(left)
    right_tokens = _meaningful_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    return bool(left_tokens & right_tokens)


def _meaningful_tokens(value: str) -> set[str]:
    tokens = {
        token.strip(".,;:'\"()[]!?").lower()
        for token in value.replace("/", " ").replace("-", " ").split()
    }
    return {token for token in tokens if len(token) >= 5}


def _normalize(value: str) -> str:
    return "".join(value.lower().split())


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value).strip()
