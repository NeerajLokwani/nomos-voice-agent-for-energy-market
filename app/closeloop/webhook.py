"""ElevenLabs post-call webhook helpers: payload normalization + signature check.

ElevenLabs sends:
    {"type": "post_call_transcription", "data": {
        "conversation_id": "...", "agent_id": "...",
        "transcript": [{"role": "agent"|"user", "message": "..."}],
        "analysis": {"transcript_summary": "...",
                     "data_collection_results": {"malo_id": {"value": "..."}, ...}},
        "conversation_initiation_client_data": {"dynamic_variables": {"call_id": "..."}},
        "metadata": {...}}}

normalize_payload flattens both that real shape AND the simplified fixture shape into
the flat structure WebhookPayload expects, so the same endpoint serves live + demo.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any


def _flatten_data_collection(analysis: dict[str, Any]) -> dict[str, Any]:
    dcr = analysis.get("data_collection_results")
    if not isinstance(dcr, dict):
        return analysis
    flat: dict[str, Any] = {}
    for key, obj in dcr.items():
        flat[key] = obj.get("value") if isinstance(obj, dict) else obj
    if analysis.get("transcript_summary") and "transcript_summary" not in flat:
        flat["transcript_summary"] = analysis["transcript_summary"]
    return flat


def normalize_payload(body: dict[str, Any]) -> dict[str, Any]:
    """Accept the real ElevenLabs envelope or the simplified shape; return flat dict."""
    if not isinstance(body, dict):
        return body

    data = body
    if isinstance(body.get("data"), dict) and "conversation_id" in body["data"]:
        data = dict(body["data"])

    analysis = data.get("analysis")
    if isinstance(analysis, dict):
        data = {**data, "analysis": _flatten_data_collection(analysis)}

    # Surface our internal call_id (passed as a dynamic variable at call start) into
    # metadata so the record can be tied back to the dashboard's call.
    cicd = data.get("conversation_initiation_client_data")
    if isinstance(cicd, dict):
        dyn = cicd.get("dynamic_variables") or {}
        meta = dict(data.get("metadata") or {})
        if dyn.get("call_id") and "call_id" not in meta:
            meta["call_id"] = dyn["call_id"]
        if dyn.get("case_id") and "case" not in meta:
            meta["case"] = dyn["case_id"]
        data = {**data, "metadata": meta}

    return data


def verify_signature(raw_body: bytes, signature_header: str | None,
                     tolerance_secs: int = 1800) -> tuple[bool, str]:
    """Verify the ElevenLabs-Signature header. Skips if ELEVENLABS_WEBHOOK_SECRET unset."""
    secret = os.getenv("ELEVENLABS_WEBHOOK_SECRET")
    if not secret:
        return True, "skipped (kein ELEVENLABS_WEBHOOK_SECRET gesetzt)"
    if not signature_header:
        return False, "fehlender Signatur-Header"
    parts = dict(p.split("=", 1) for p in signature_header.split(",") if "=" in p)
    ts, sig = parts.get("t"), parts.get("v0")
    if not ts or not sig:
        return False, "ungueltiges Signatur-Format"
    try:
        if abs(time.time() - int(ts)) > tolerance_secs:
            return False, "Zeitstempel ausserhalb der Toleranz"
    except ValueError:
        return False, "ungueltiger Zeitstempel"
    signed = f"{ts}.{raw_body.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return (True, "ok") if hmac.compare_digest(expected, sig) else (False, "Signatur stimmt nicht")
