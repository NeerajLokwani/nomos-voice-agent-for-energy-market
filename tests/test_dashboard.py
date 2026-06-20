from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dashboard_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "Clearing Calls" in r.text


def test_triggers_endpoint_returns_list():
    assert isinstance(client.get("/triggers").json(), list)


def test_full_demo_flow_visible_via_api():
    # Mirrors what the dashboard does: start -> record -> finalize -> result has note + trigger
    cid = client.post("/calls", json={"case_id": "CASE-A", "dry_run": True}).json()["call_id"]
    client.post("/tools/record_finding", json={"call_id": cid, "meter_status": "removed",
                                               "reason": "Baustromzähler ausgebaut"})
    client.post("/tools/end_call", json={"call_id": cid, "status": "resolved"})
    r = client.post(f"/calls/{cid}/finalize").json()
    assert r["note_de"]
    assert r["triggered"]
    # and it shows up in /results
    assert any(x["call_id"] == cid for x in client.get("/results").json())
