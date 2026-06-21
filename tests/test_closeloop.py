"""Tests for the ported close-the-loop pipeline (transcript-grounded extraction)."""
import json
from pathlib import Path

from app.closeloop.pipeline import process_call
from app.closeloop.schema import WebhookPayload

SAMPLES = json.loads(
    (Path(__file__).resolve().parent.parent / "app" / "closeloop" / "sample_payloads.json").read_text(encoding="utf-8")
)


def _record(case):
    return process_call(WebhookPayload.model_validate(SAMPLES[case]["payload"]))


def test_case_a_grounds_facts_and_fires_actions():
    r = _record("CASE-A")
    assert r.facts.malo_id == "50312478901"
    assert r.facts.needs_human is False
    assert "Baustrom" in (r.facts.stuck_reason or "")
    types = {a.type for a in r.actions}
    assert "write_malo" in types and "start_email_agent" in types
    assert r.facts.vorgang_nr and r.facts.vorgang_nr.startswith("NOM-2026-")


def test_case_c_corrected_malo_from_readback():
    r = _record("CASE-C")
    assert r.facts.malo_id == "88765432103"  # last 11-digit run = corrected value
    assert "88765432103" in r.note


def test_gap_case_never_fabricates():
    r = _record("CASE-GAP")
    assert r.facts.malo_id is None
    assert r.facts.stuck_reason is None
    assert r.facts.needs_human is True
    assert any(a.type == "flag_human_review" for a in r.actions)


def test_empty_transcript_needs_human():
    r = process_call(WebhookPayload(conversation_id="empty"))
    assert r.facts.needs_human is True
    assert r.facts.analysis_confidence == 0.0


def test_malo_candidate_not_in_transcript_is_dropped():
    # analysis claims a MaLo never spoken on the call -> dropped, not trusted.
    p = WebhookPayload.model_validate({
        "conversation_id": "c1",
        "transcript": [{"role": "user", "message": "Ich kann das gerade nicht sehen."}],
        "analysis": {"malo_id": "12345678901"},
    })
    r = process_call(p)
    assert r.facts.malo_id is None
    assert any("verworfen" in n for n in r.facts.grounding_notes)


def test_note_reads_malo_digit_by_digit():
    r = _record("CASE-A")
    assert "5 0 3 1 2 4 7 8 9 0 1" in r.note
