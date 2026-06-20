import json
from pathlib import Path

import pytest

from app.config import get_settings
from app.verify import main


@pytest.fixture(autouse=True)
def _cli_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EMAIL_MODE", "mock")
    monkeypatch.setenv("EMAIL_FROM", "Nomos <noreply@example.com>")
    monkeypatch.setenv("EMAIL_TO_NOMOS", "nomos@example.com")
    monkeypatch.setenv("EMAIL_TO_TEST", "test@example.com")
    monkeypatch.setenv("STORE_PATH", str(tmp_path / "data" / "results.json"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_verify_cli_nutzt_synthetisches_callresult(capsys):
    code = main(["CASE-A"])

    output = capsys.readouterr().out
    assert code == 0
    assert "ReconciliationReport:" in output
    assert "Mail-Referenz: mock-CASE-A" in output
    assert "Mail-Pfad: outbox/CASE-A.eml" in output
    assert Path("outbox/CASE-A.eml").exists()


def test_verify_cli_from_file_sendet_an_testadresse(capsys, tmp_path):
    inbound = tmp_path / "inbound.json"
    inbound.write_text(
        json.dumps(
            {
                "case_id": "CASE-B",
                "status": "resolved",
                "reason": "Anmeldung ist im System und wird bearbeitet",
                "vorgangsnummer": "KL202644817",
                "next_action": "await_processing",
                "confidence": 0.9,
            }
        ),
        encoding="utf-8",
    )

    code = main(["CASE-B", "--from-file", str(inbound)])

    output = capsys.readouterr().out
    assert code == 0
    assert "CASE-B" in output
    eml = Path("outbox/CASE-B.eml").read_text(encoding="utf-8")
    assert "To: test@example.com" in eml
