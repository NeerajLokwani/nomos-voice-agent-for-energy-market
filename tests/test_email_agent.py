import json
from email import policy
from email.parser import Parser

import pytest

from app.config import get_settings
from app.email_agent import RESEND_ENDPOINT, send_summary_email


@pytest.fixture(autouse=True)
def _settings_cache_leeren():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_send_summary_email_mock_schreibt_outbox_und_log(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EMAIL_MODE", "mock")
    monkeypatch.setenv("EMAIL_FROM", "Nomos <noreply@example.com>")
    monkeypatch.setenv("EMAIL_TO_TEST", "test@example.com")
    monkeypatch.setenv("STORE_PATH", str(tmp_path / "data" / "results.json"))
    get_settings.cache_clear()

    ref = send_summary_email(
        "Nomos Fall CASE-A: verifiziert",
        "Fall: CASE-A\nBackoffice-Notiz: Zähler ausgebaut",
        "<p>CASE-A</p>",
    )

    assert ref == "mock-CASE-A"
    eml = (tmp_path / "outbox" / "CASE-A.eml").read_text(encoding="utf-8")
    message = Parser(policy=policy.default).parsestr(eml)
    assert "To: test@example.com" in eml
    assert "Backoffice-Notiz" in message.get_body(preferencelist=("plain",)).get_content()
    assert (tmp_path / "outbox" / "CASE-A.html").read_text(encoding="utf-8") == "<p>CASE-A</p>"

    log = json.loads((tmp_path / "data" / "triggers.log.json").read_text(encoding="utf-8"))
    assert log[-1]["service"] == "email_agent"
    assert log[-1]["payload"]["id"] == "mock-CASE-A"
    assert log[-1]["payload"]["subject"] == "Nomos Fall CASE-A: verifiziert"


def test_send_summary_email_resend_postet_payload(monkeypatch):
    monkeypatch.setenv("EMAIL_MODE", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "resend-key")
    monkeypatch.setenv("EMAIL_FROM", "Nomos <noreply@example.com>")
    monkeypatch.setenv("EMAIL_TO_NOMOS", "nomos@example.com")
    get_settings.cache_clear()
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "resend-123"}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("app.email_agent.httpx.post", fake_post)

    ref = send_summary_email("Betreff", "Text", "<p>Text</p>")

    assert ref == "resend-123"
    assert captured["url"] == RESEND_ENDPOINT
    assert captured["headers"]["Authorization"] == "Bearer resend-key"
    assert captured["json"] == {
        "from": "Nomos <noreply@example.com>",
        "to": ["nomos@example.com"],
        "subject": "Betreff",
        "text": "Text",
        "html": "<p>Text</p>",
    }
