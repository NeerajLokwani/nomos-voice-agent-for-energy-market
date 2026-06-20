"""Tiny JSON-file store for call results and live call status.

Keyed by call_id. Good enough for a hackathon demo; swap for SQLite if needed.
Also keeps a lightweight in-memory live-status map for the dashboard's polling.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

from .config import get_settings
from .schema import CallResult

_lock = threading.Lock()

# call_id -> {status, case_id, transcript: [...], updated_at}
_live: Dict[str, dict] = {}


def _path() -> Path:
    p = Path(get_settings().store_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _read_all() -> Dict[str, dict]:
    p = _path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_result(result: CallResult) -> None:
    with _lock:
        data = _read_all()
        key = result.call_id or result.case_id
        data[key] = json.loads(result.model_dump_json())
        _path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_result(key: str) -> Optional[dict]:
    return _read_all().get(key)


def list_results() -> List[dict]:
    return list(_read_all().values())


# --- live status (in-memory, for the dashboard) ---

def set_live(call_id: str, **fields) -> None:
    with _lock:
        entry = _live.setdefault(call_id, {"call_id": call_id, "transcript": []})
        entry.update(fields)


def append_transcript(call_id: str, role: str, text: str) -> None:
    with _lock:
        entry = _live.setdefault(call_id, {"call_id": call_id, "transcript": []})
        entry["transcript"].append({"role": role, "text": text})


def get_live(call_id: str) -> Optional[dict]:
    return _live.get(call_id)
