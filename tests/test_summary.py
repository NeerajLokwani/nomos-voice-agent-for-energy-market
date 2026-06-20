import pytest

from app.config import get_settings
from app.fixtures import get_case
from app.reconcile import reconcile
from app.summary import build_email_summary
from app.schema import CallResult, CallStatus, MeterStatus, NextAction


@pytest.fixture(autouse=True)
def _settings_cache_leeren():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _case_a_result():
    return CallResult(
        case_id="CASE-A",
        status=CallStatus.resolved,
        reason="Baustromzähler am 18.05. ausgebaut, alte MaLo tot, neue Anlage nötig",
        meter_status=MeterStatus.removed,
        next_action=NextAction.create_new_anlage,
        confidence=0.9,
    )


def test_build_email_summary_nutzt_template_ohne_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    case = get_case("CASE-A")
    result = _case_a_result()
    report = reconcile(case, result)

    summary = build_email_summary(case, result, report)

    assert summary["subject"].startswith("Nomos Fall CASE-A")
    assert "Backoffice-Notiz" in summary["body_text"]
    assert "Baustromzähler" in summary["body_text"]
    assert "meter_status" in summary["body_text"]
    assert "<p>" in summary["body_html"]


def test_build_email_summary_faellt_bei_openai_fehler_zurueck(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()
    case = get_case("CASE-A")
    result = _case_a_result()
    report = reconcile(case, result)

    def fail(*args, **kwargs):
        raise TimeoutError("timeout")

    monkeypatch.setattr("app.summary._build_openai_summary", fail)

    summary = build_email_summary(case, result, report)

    assert summary["subject"].startswith("Nomos Fall CASE-A")
    assert "Verifikation: verifiziert" in summary["body_text"]
