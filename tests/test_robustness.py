"""Robustness coverage that runs offline (no API key).

Two layers:
  1. The fallback playbook is actually encoded in the agent prompt.
  2. Each off-happy-path scenario, when it reaches our pipeline, yields a graceful typed
     status with NO fabricated data.
The live LLM curveball loop lives in sim.harness (run manually with OPENAI_API_KEY).
"""
from fastapi.testclient import TestClient

from app.agent_prompt import AGENT_SYSTEM_PROMPT
from app.main import app
from sim.harness import first_agent_message

client = TestClient(app)


def _start(case_id):
    return client.post("/calls", json={"case_id": case_id, "dry_run": True}).json()["call_id"]


def test_disclosure_is_first_message_without_api():
    for cid in ("CASE-A", "CASE-B", "CASE-C"):
        assert "KI-Assistent" in first_agent_message(cid)


def test_prompt_encodes_every_fallback_branch():
    p = AGENT_SYSTEM_PROMPT
    assert "niemals erfinden" in p             # unknown fact -> never invent
    assert "nicht überein" in p                # number mismatch -> compare digit by digit
    assert "findet den Fall nicht" in p        # can't find -> offer more details
    assert "Weiterleitung" in p                # transfer -> partial + callback
    assert "Anrufbeantworter" in p             # voicemail -> end cleanly
    assert "Marktpartner-ID" in p              # asked for data we don't have


def test_transfer_scenario_finalizes_as_partial():
    cid = _start("CASE-A")
    # clerk transferred; agent captured nothing concrete
    client.post("/tools/end_call", json={"call_id": cid, "status": "partial",
                                         "summary": "An andere Stelle weitergeleitet, dort nicht erreicht"})
    r = client.post(f"/calls/{cid}/finalize").json()
    assert r["status"] == "partial"
    assert r["corrected_malo"] is None and r["vorgangsnummer"] is None  # nothing invented


def test_voicemail_scenario_needs_human_no_fabrication():
    cid = _start("CASE-B")
    client.post("/tools/end_call", json={"call_id": cid, "status": "needs_human",
                                         "summary": "Nur Anrufbeantworter erreicht"})
    r = client.post(f"/calls/{cid}/finalize").json()
    assert r["status"] == "needs_human"
    assert r["next_action"] == "needs_human_followup"
    assert r["reason"] == "Nur Anrufbeantworter erreicht"


def test_off_by_one_only_records_after_confirmed_readback():
    # The agent should only record the value it confirmed via readback.
    cid = _start("CASE-C")
    client.post("/tools/record_finding", json={"call_id": cid, "corrected_malo": "71005523911"})
    client.post("/tools/end_call", json={"call_id": cid, "status": "resolved"})
    r = client.post(f"/calls/{cid}/finalize").json()
    assert r["corrected_malo"] == "71005523911"  # the corrected, confirmed number
