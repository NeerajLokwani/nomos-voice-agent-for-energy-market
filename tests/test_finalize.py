"""End-to-end (API-level) pipeline tests for all three cases:
record findings via the live tools -> end_call -> finalize -> assert structured result,
German note, and the correct mock trigger fired.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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


def test_post_call_webhook_runs_closeloop_pipeline():
    """The EL post-call webhook now runs the close-the-loop pipeline: it grounds the
    corrected MaLo from the German spoken-digit readback and stores a record keyed by
    our call_id (passed as a dynamic variable)."""
    cid = _start("CASE-C")
    env = {
        "type": "post_call_transcription",
        "data": {
            "conversation_id": "conv_xyz",
            "transcript": [
                {"role": "agent", "message": "Guten Tag, hier spricht ein KI-Assistent von Nomos."},
                {"role": "user", "message": "Die hinterlegte Marktlokation war falsch, sie passte nicht zur Adresse. Die korrekte MaLo ist sieben eins null null fünf fünf zwei drei neun eins eins."},
                {"role": "agent", "message": "Verstanden, wir hinterlegen die korrigierte Marktlokation und senden die Anmeldung erneut."},
            ],
            "analysis": {"data_collection_results": {
                "malo_id": {"value": "71005523911"},
                "stuck_reason": {"value": "Falsche Marktlokation hinterlegt, passte nicht zur Adresse"},
                "next_step": {"value": "korrigierte Marktlokation hinterlegen und Anmeldung erneut senden"},
            }},
            "conversation_initiation_client_data": {"dynamic_variables": {"call_id": cid, "case_id": "CASE-C"}},
        },
    }
    r = client.post("/elevenlabs/post-call", json=env)
    assert r.status_code == 200
    rec = r.json()["record"]
    assert rec["facts"]["malo_id"] == "71005523911"      # grounded from readback
    assert rec["facts"]["needs_human"] is False
    assert any(a["type"] == "write_malo" for a in rec["actions"])
    # stored + retrievable by our call_id
    assert client.get(f"/api/conversations/{cid}").json()["facts"]["malo_id"] == "71005523911"
