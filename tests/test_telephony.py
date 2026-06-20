import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.fixtures import build_dynamic_variables, get_case
from app.main import app
from app.telephony import build_call_twiml

client = TestClient(app)


def test_twiml_sends_correct_ivr_digit_and_bridges():
    dv = build_dynamic_variables(get_case("CASE-C"))
    twiml = build_call_twiml("abc123", dv, ivr_digit="2")
    # navigates the menu with the case's digit (CASE-C -> 2)
    assert 'digits="ww2"' in twiml
    # bridges to the ElevenLabs media stream
    assert "<Connect>" in twiml and "<Stream" in twiml
    # passes the pre-spelled MaLo as a custom parameter (agent speaks THIS)
    assert "malo_id_spoken" in twiml
    assert "call_id" in twiml


def test_twiml_is_well_formed_xml():
    import xml.dom.minidom as minidom

    dv = build_dynamic_variables(get_case("CASE-A"))
    twiml = build_call_twiml("xyz", dv)
    minidom.parseString(twiml)  # raises if malformed


def test_dial_guard_refuses_non_practice_number():
    s = get_settings()
    s.practice_clerk_number = "+49301112222"
    with pytest.raises(ValueError):
        s.assert_dialable("+49309998888")
    assert s.assert_dialable("+49 30 111 2222") == "+49301112222"


def test_dial_guard_refuses_when_unconfigured():
    s = get_settings()
    s.practice_clerk_number = ""
    with pytest.raises(ValueError):
        s.assert_dialable("+49301112222")


def test_start_call_dry_run_returns_dynamic_variables():
    r = client.post("/calls", json={"case_id": "CASE-A", "dry_run": True})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "dry_run"
    dv = body["dynamic_variables"]
    assert dv["malo_id_spoken"].startswith("fünf, null, drei")


def test_voice_endpoint_serves_twiml_for_prepared_call():
    call_id = client.post("/calls", json={"case_id": "CASE-C", "dry_run": True}).json()["call_id"]
    r = client.get(f"/voice/{call_id}?ivr_digit=2")
    assert r.status_code == 200
    assert "application/xml" in r.headers["content-type"]
    assert 'digits="ww2"' in r.text


def test_start_call_unknown_case_404():
    assert client.post("/calls", json={"case_id": "NOPE", "dry_run": True}).status_code == 404
