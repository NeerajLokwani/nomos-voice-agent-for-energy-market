"""End-to-end (API-level) pipeline tests for all three cases:
record findings via the live tools -> end_call -> finalize -> assert structured result,
German note, and the correct mock trigger fired.
"""
from fastapi.testclient import TestClient
import pytest

from app.config import get_settings
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _mock_mail_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EMAIL_MODE", "mock")
    monkeypatch.setenv("STORE_PATH", str(tmp_path / "data" / "results.json"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _start(case_id):
    return client.post("/calls", json={"case_id": case_id, "dry_run": True}).json()["call_id"]


def test_case_a_meter_removed_triggers_email_agent():
    cid = _start("CASE-A")
    client.post("/tools/record_finding", json={
        "call_id": cid,
        "meter_status": "removed",
        "reason": "Baustromzähler am 18.05. ausgebaut, alte MaLo tot, neue Anlage nötig",
    })
    client.post("/tools/end_call", json={"call_id": cid, "status": "resolved"})
    r = client.post(f"/calls/{cid}/finalize").json()

    assert r["status"] == "resolved"
    assert r["meter_status"] == "removed"
    assert r["next_action"] == "create_new_anlage"
    assert "ausgebaut" in r["note_de"]
    assert any("email_agent" in t for t in r["triggered"])
    assert r["reconciliation"]["verification_status"] == "verifiziert"
    assert r["email_status"] == "verschickt"
    assert r["email_ref"] == "mock-CASE-A"


def test_case_c_corrected_malo_triggers_signup_step():
    cid = _start("CASE-C")
    client.post("/tools/record_finding", json={
        "call_id": cid, "corrected_malo": "71005523911",
    })
    client.post("/tools/end_call", json={"call_id": cid, "status": "resolved"})
    r = client.post(f"/calls/{cid}/finalize").json()

    assert r["corrected_malo"] == "71005523911"
    assert r["next_action"] == "trigger_signup_step"
    assert "71005523911" in r["note_de"]
    assert any("signup_workflow" in t for t in r["triggered"])
    assert r["reconciliation"]["case_id"] == "CASE-C"
    assert r["email_status"] == "verschickt"


def test_case_b_vorgangsnummer_triggers_tracking():
    cid = _start("CASE-B")
    client.post("/tools/record_finding", json={
        "call_id": cid,
        "vorgangsnummer": "KL202644817",
        "reason": "Anmeldung lag korrekt vor, war nur nicht bearbeitet",
    })
    client.post("/tools/end_call", json={"call_id": cid, "status": "resolved"})
    r = client.post(f"/calls/{cid}/finalize").json()

    assert r["vorgangsnummer"] == "KL202644817"
    assert r["next_action"] == "await_processing"
    assert any("case_tracker" in t for t in r["triggered"])


def test_needs_human_path_flags_followup_no_fabrication():
    cid = _start("CASE-A")
    # nothing recorded (clerk couldn't help)
    client.post("/tools/end_call", json={"call_id": cid, "status": "needs_human"})
    r = client.post(f"/calls/{cid}/finalize").json()

    assert r["status"] == "needs_human"
    assert r["next_action"] == "needs_human_followup"
    assert r["corrected_malo"] is None  # never invented
    assert r["meter_status"] == "unknown"
    assert r["reconciliation"]["verification_status"] == "mensch_noetig"


def test_post_call_webhook_finalizes_via_dynamic_call_id():
    cid = _start("CASE-C")
    client.post("/tools/record_finding", json={"call_id": cid, "corrected_malo": "71005523911"})
    client.post("/tools/end_call", json={"call_id": cid, "status": "resolved"})
    payload = {
        "data": {
            "conversation_initiation_client_data": {"dynamic_variables": {"call_id": cid}},
            "transcript": [{"role": "agent", "message": "Guten Tag, hier spricht ein KI-Assistent"}],
        }
    }
    r = client.post("/elevenlabs/post-call", json=payload)
    assert r.status_code == 200
    assert r.json()["result"]["next_action"] == "trigger_signup_step"


def test_finalize_faengt_mailfehler_ab(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("mail kaputt")

    monkeypatch.setattr("app.finalize.send_summary_email", fail)
    cid = _start("CASE-B")
    client.post("/tools/record_finding", json={
        "call_id": cid,
        "vorgangsnummer": "KL202644817",
        "reason": "Anmeldung lag korrekt vor, war nur nicht bearbeitet",
    })
    client.post("/tools/end_call", json={"call_id": cid, "status": "resolved"})

    r = client.post(f"/calls/{cid}/finalize")

    assert r.status_code == 200
    body = r.json()
    assert body["email_status"] == "fehler: RuntimeError"
    assert body["email_ref"] is None
    assert body["reconciliation"]["case_id"] == "CASE-B"
