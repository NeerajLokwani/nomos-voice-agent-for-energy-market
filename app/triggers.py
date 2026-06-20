"""Mocked-but-real downstream services — the 'close the loop' part of the brief.

These do NOT contact the real market (compliance). They log a structured, visible
action so the dashboard can show that the case actually moved forward.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .config import get_settings

_lock = threading.Lock()


def _log_path() -> Path:
    p = Path(get_settings().store_path).parent / "triggers.log.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _emit(service: str, payload: dict) -> str:
    entry = {
        "service": service,
        "payload": payload,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        existing = []
        p = _log_path()
        if p.exists():
            try:
                existing = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = []
        existing.append(entry)
        p.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"{service}: {json.dumps(payload, ensure_ascii=False)}"


def mock_email_agent(case_id: str, reason: str) -> str:
    """Hand the case to the (mock) email agent for customer outreach."""
    return _emit("email_agent", {"case_id": case_id, "action": "contact_customer", "reason": reason})


def mock_signup_step(case_id: str, corrected_malo: str) -> str:
    """Write the corrected MaLo and advance the (mock) sign-up workflow."""
    return _emit(
        "signup_workflow",
        {"case_id": case_id, "action": "advance_signup", "corrected_malo": corrected_malo},
    )


def mock_track_vorgang(case_id: str, vorgangsnummer: str) -> str:
    """Record a Vorgangsnummer to track an in-process registration."""
    return _emit(
        "case_tracker",
        {"case_id": case_id, "action": "await_processing", "vorgangsnummer": vorgangsnummer},
    )


def list_triggers() -> List[dict]:
    p = _log_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
