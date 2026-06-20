"""Backoffice-Mail aus CallResult und Verifikationsbericht erzeugen."""
from __future__ import annotations

import html
import json
from typing import Any

from .config import get_settings
from .notes import build_notes
from .schema import CallResult, ReconciliationReport


SYSTEM_PROMPT = """Du schreibst eine kurze, sachliche deutsche Backoffice-Mail an Nomos.
Du darfst ausschließlich vorhandene Fakten aus dem Grounding umformulieren.
Füge keine Namen, Daten, Nummern, Ursachen, Bewertungen oder nächsten Schritte hinzu.
Wenn ein Feld fehlt oder offen ist, schreibe es als offen. Erfinde niemals Werte.
Antworte ausschließlich als JSON mit den Schlüsseln subject, body_text und body_html."""


def build_email_summary(case: dict, result: CallResult, report: ReconciliationReport) -> dict:
    """Erzeuge immer eine Mail-Zusammenfassung, mit OpenAI oder Template-Fallback."""
    note_de = _note_de(case, result)
    settings = get_settings()
    if settings.openai_api_key:
        try:
            return _build_openai_summary(case, result, report, note_de, settings)
        except Exception:
            pass
    return _fallback_summary(case, result, report, note_de)


def _build_openai_summary(
    case: dict,
    result: CallResult,
    report: ReconciliationReport,
    note_de: str,
    settings,
) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key, timeout=8.0)
    response = client.chat.completions.create(
        model=settings.summary_model or "gpt-4o",
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    _grounding(case, result, report, note_de),
                    ensure_ascii=False,
                    indent=2,
                ),
            },
        ],
    )
    content = response.choices[0].message.content or ""
    data = json.loads(content)
    return _clean_summary(data) or _fallback_summary(case, result, report, note_de)


def _fallback_summary(
    case: dict,
    result: CallResult,
    report: ReconciliationReport,
    note_de: str,
) -> dict:
    case_id = case.get("id") or result.case_id
    title = case.get("case_title", "")
    subject = f"Nomos Fall {case_id}: {report.verification_status}"
    if title:
        subject += f" - {title}"

    lines = [
        f"Fall: {case_id}" + (f" - {title}" if title else ""),
        f"Verifikation: {report.verification_status}",
        f"Nächster Schritt: {_text(result.next_action) or 'offen'}",
        "",
        "Backoffice-Notiz:",
        note_de or "offen",
        "",
        "Prüfpunkte:",
    ]
    lines.extend(_item_line(item) for item in report.items)
    if report.summary_points:
        lines.extend(["", "Zusammenfassung:"])
        lines.extend(report.summary_points)

    body_text = "\n".join(lines)
    body_html = _html_from_lines(lines)
    return {"subject": subject, "body_text": body_text, "body_html": body_html}


def _grounding(
    case: dict,
    result: CallResult,
    report: ReconciliationReport,
    note_de: str,
) -> dict:
    return {
        "anweisung": "Nur diese Fakten verwenden; offene Felder nicht ergänzen.",
        "case": {
            "id": case.get("id", ""),
            "case_title": case.get("case_title", ""),
            "vnb_name": case.get("vnb_name", ""),
            "lieferstelle": case.get("lieferstelle", ""),
            "statustext": case.get("statustext", ""),
        },
        "call_result": {
            "status": _text(result.status),
            "reason": result.reason,
            "corrected_malo": result.corrected_malo or "",
            "vorgangsnummer": result.vorgangsnummer or "",
            "meter_status": _text(result.meter_status),
            "next_action": _text(result.next_action),
            "note_de": note_de,
        },
        "reconciliation_report": {
            "verification_status": report.verification_status,
            "confidence": report.confidence,
            "summary_points": report.summary_points,
            "items": [item.model_dump() for item in report.items],
        },
    }


def _note_de(case: dict, result: CallResult) -> str:
    if result.note_de:
        return result.note_de
    note_de, _ = build_notes(
        case,
        result.reason,
        result.next_action,
        result.corrected_malo,
        result.vorgangsnummer,
        result.meter_status,
    )
    return note_de


def _clean_summary(data: Any) -> dict:
    if not isinstance(data, dict):
        return {}
    subject = _text(data.get("subject"))
    body_text = _text(data.get("body_text"))
    body_html = _text(data.get("body_html"))
    if not subject or not body_text:
        return {}
    if not body_html:
        body_html = _html_from_lines(body_text.splitlines())
    return {"subject": subject, "body_text": body_text, "body_html": body_html}


def _item_line(item) -> str:
    old = item.old or "offen"
    new = item.new or "offen"
    return f"- {item.field}: {item.kind} (bekannt: {old}; neu: {new})"


def _html_from_lines(lines: list[str]) -> str:
    parts = []
    in_list = False
    for line in lines:
        if line.startswith("- "):
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{html.escape(line[2:])}</li>")
            continue
        if in_list:
            parts.append("</ul>")
            in_list = False
        if line:
            parts.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        parts.append("</ul>")
    return "\n".join(parts)


def _text(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value).strip()
