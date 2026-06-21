"""ElevenLabs Conversational-AI helpers.

Two jobs:
  1. `sync_agent()` — push our system prompt, first message (the AI-disclosure opener),
     language (de) and tools into the configured EL agent. Run once during setup and
     whenever the prompt changes.
  2. `place_call_via_elevenlabs()` — the native EL outbound path (alternative to the
     Twilio-layer flow in telephony.py). Simpler, but leaves IVR navigation to the
     agent's DTMF tool; we default to the Twilio-layer path for deterministic IVR.

All network calls are lazy and guarded so the rest of the app/tests run without creds.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import httpx

from .agent_prompt import AGENT_SYSTEM_PROMPT, FIRST_MESSAGE
from .config import get_settings

BASE = "https://api.elevenlabs.io"


def _headers() -> Dict[str, str]:
    s = get_settings()
    if not s.elevenlabs_api_key:
        raise ValueError("ELEVENLABS_API_KEY not configured")
    return {"xi-api-key": s.elevenlabs_api_key, "Content-Type": "application/json"}


def build_tools_spec(base_url: str) -> List[dict]:
    """Webhook tool_config definitions the EL agent calls mid-conversation.

    Kept tiny and fast (latency = the thing that makes Helga hang up). validate_id is a
    local checksum on our side; the others record/transition state. Shapes follow the
    standalone ElevenLabs Tools API (/v1/convai/tools).
    """
    def tool(name: str, description: str, props: dict, required: List[str]) -> dict:
        return {
            "type": "webhook",
            "name": name,
            "description": description,
            "response_timeout_secs": 10,
            "api_schema": {
                "url": f"{base_url}/tools/{name}",
                "method": "POST",
                "request_body_schema": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                },
            },
        }

    return [
        tool(
            "validate_id",
            "Prüfe/formatiere eine MaLo oder Vorgangsnummer und erhalte sie Ziffer für "
            "Ziffer zum Zurücklesen.",
            {
                "call_id": {"type": "string", "description": "Die ID dieses Anrufs."},
                "id_type": {"type": "string", "description": "malo oder vorgangsnummer."},
                "value": {"type": "string", "description": "Die genannte Nummer."},
            },
            ["call_id", "id_type", "value"],
        ),
        tool(
            "record_finding",
            "Halte einen bestätigten Befund fest (Grund, korrigierte MaLo, "
            "Vorgangsnummer, Zählerstatus).",
            {
                "call_id": {"type": "string", "description": "Die ID dieses Anrufs."},
                "reason": {"type": "string", "description": "Der echte Grund/Befund."},
                "corrected_malo": {"type": "string", "description": "Korrigierte MaLo, falls genannt."},
                "vorgangsnummer": {"type": "string", "description": "Vorgangsnummer, falls genannt."},
                "meter_status": {"type": "string", "description": "active, removed oder unknown."},
            },
            ["call_id"],
        ),
        tool(
            "end_call",
            "Beende den Vorgang mit Status und nächster Aktion.",
            {
                "call_id": {"type": "string", "description": "Die ID dieses Anrufs."},
                "status": {"type": "string", "description": "resolved, partial oder needs_human."},
                "next_action": {"type": "string", "description": "Der nächste Schritt."},
                "summary": {"type": "string", "description": "Kurze Zusammenfassung."},
            },
            ["call_id", "status"],
        ),
        tool(
            "get_case_context",
            "NUR als Notfall, falls eine Fallinformation fehlt: hole die Falldaten.",
            {"call_id": {"type": "string", "description": "Die ID dieses Anrufs."}},
            ["call_id"],
        ),
    ]


def sync_tools(base_url: str) -> List[str]:
    """Create-or-update the webhook tools via /v1/convai/tools; return their tool_ids.

    Idempotent by name: an existing tool with the same name is updated, not duplicated.
    """
    headers = _headers()
    existing = httpx.get(f"{BASE}/v1/convai/tools", headers=headers, timeout=30)
    existing.raise_for_status()
    payload = existing.json()
    items = payload.get("tools", payload if isinstance(payload, list) else [])
    by_name = {}
    for it in items:
        name = (it.get("tool_config") or {}).get("name") or it.get("name")
        if name:
            by_name[name] = it.get("id") or it.get("tool_id")

    tool_ids: List[str] = []
    for cfg in build_tools_spec(base_url):
        body = {"tool_config": cfg}
        tid = by_name.get(cfg["name"])
        if tid:
            r = httpx.patch(f"{BASE}/v1/convai/tools/{tid}", headers=headers, json=body, timeout=30)
        else:
            r = httpx.post(f"{BASE}/v1/convai/tools", headers=headers, json=body, timeout=30)
        r.raise_for_status()
        tool_ids.append(r.json().get("id") or tid)
    return tool_ids


def sync_agent(voice_id: Optional[str] = None) -> dict:
    """Update the EL agent with our prompt, first message, language, voice, and tools."""
    s = get_settings()
    if not s.elevenlabs_agent_id:
        raise ValueError("ELEVENLABS_AGENT_ID not configured")

    tool_ids = sync_tools(s.public_base_url)

    agent_cfg: dict = {
        "first_message": FIRST_MESSAGE,
        "language": "de",
        "prompt": {"prompt": AGENT_SYSTEM_PROMPT, "tool_ids": tool_ids},
    }
    tts_cfg = {"voice_id": voice_id} if voice_id else {}
    body = {"conversation_config": {"agent": agent_cfg, "tts": tts_cfg}}

    resp = httpx.patch(
        f"{BASE}/v1/convai/agents/{s.elevenlabs_agent_id}",
        headers=_headers(),
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    return {"tool_ids": tool_ids, **resp.json()}


def place_call_via_elevenlabs(to_number: str, dynamic_variables: Dict[str, str]) -> dict:
    """Native EL outbound call (alternative path). Compliance gate applies."""
    s = get_settings()
    to_number = s.assert_dialable(to_number)
    if not s.elevenlabs_phone_number_id:
        raise ValueError("ELEVENLABS_PHONE_NUMBER_ID not configured")

    body = {
        "agent_id": s.elevenlabs_agent_id,
        "agent_phone_number_id": s.elevenlabs_phone_number_id,
        "to_number": to_number,
        "conversation_initiation_client_data": {
            "dynamic_variables": dynamic_variables,
        },
    }
    resp = httpx.post(
        f"{BASE}/v1/convai/twilio/outbound-call",
        headers=_headers(),
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
