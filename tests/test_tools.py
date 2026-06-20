from fastapi.testclient import TestClient

from app.main import app
from app.validation import malo_check_digit, validate_malo

client = TestClient(app)


def _new_call(case_id="CASE-A"):
    return client.post("/calls", json={"case_id": case_id, "dry_run": True}).json()["call_id"]


def test_validate_malo_format_and_spoken():
    r = validate_malo("71005523911")
    assert r["format_ok"] is True
    assert r["spoken"] == "sieben, eins, null, null, fünf, fünf, zwei, drei, neun, eins, eins"


def test_validate_malo_rejects_wrong_length():
    assert validate_malo("123")["format_ok"] is False


def test_malo_check_digit_is_advisory_not_blocking():
    # Synthetic IDs may not satisfy the check digit; we still accept on format.
    cd = malo_check_digit("5031247890")
    assert cd is None or 0 <= cd <= 9


def test_validate_id_endpoint_returns_spoken_for_readback():
    call_id = _new_call("CASE-C")
    r = client.post(
        "/tools/validate_id",
        json={"call_id": call_id, "id_type": "malo", "value": "71005523911"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["spoken"].startswith("sieben, eins, null")
    assert "Ziffer für Ziffer" in body["hint"]


def test_record_finding_accumulates():
    call_id = _new_call()
    client.post(
        "/tools/record_finding",
        json={"call_id": call_id, "meter_status": "removed", "reason": "Baustromzähler ausgebaut"},
    )
    r = client.post(
        "/tools/record_finding",
        json={"call_id": call_id, "reason": "Baustromzähler ausgebaut am 18.05."},
    )
    recorded = r.json()["recorded"]
    assert recorded["meter_status"] == "removed"
    assert "18.05" in recorded["reason"]


def test_end_call_sets_status():
    call_id = _new_call()
    r = client.post(
        "/tools/end_call",
        json={"call_id": call_id, "status": "resolved", "next_action": "contact_customer"},
    )
    assert r.json() == {"ok": True, "status": "resolved"}


def test_get_case_context_safety_net():
    call_id = _new_call("CASE-A")
    r = client.post("/tools/get_case_context", json={"call_id": call_id})
    assert r.json()["dynamic_variables"]["malo_id"] == "50312478901"


def test_tools_404_on_unknown_call():
    r = client.post("/tools/record_finding", json={"call_id": "nope", "reason": "x"})
    assert r.status_code == 404
