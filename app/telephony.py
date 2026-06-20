"""Twilio telephony: place the outbound call and navigate the IVR before bridging
to the ElevenLabs Conversational-AI agent.

Flow (Twilio-layer IVR handling, per the plan):
  1. We originate the call via Twilio REST — but ONLY ever to the configured practice
     number (assert_dialable, a hard compliance gate).
  2. Twilio fetches TwiML from our /voice/{call_id} endpoint.
  3. The TwiML waits briefly, sends the menu digit as DTMF (deterministic — no relying
     on the LLM to "hear" a menu), then <Connect><Stream>s the media to the ElevenLabs
     agent, passing the call_id + dynamic variables as custom parameters.

Dynamic variables (incl. pre-spelled digit tokens) are handed to ElevenLabs so the agent
speaks the right, already-digit-by-digit numbers.
"""
from __future__ import annotations

from typing import Dict, Optional
from xml.sax.saxutils import escape, quoteattr

from .config import get_settings


def elevenlabs_stream_url() -> str:
    s = get_settings()
    return f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={s.elevenlabs_agent_id}"


def build_call_twiml(
    call_id: str,
    dynamic_variables: Dict[str, str],
    ivr_digit: Optional[str] = None,
) -> str:
    """Return TwiML that navigates the menu then bridges to the ElevenLabs agent.

    `ivr_digit` defaults to the configured practice digit; pass an override when the
    agent is pointed at the per-case Helga simulator (e.g. "2" for CASE-C).
    """
    s = get_settings()
    digit = ivr_digit or s.practice_ivr_digit
    # 'ww' = two ~0.5s pauses so the menu has started before we press the key.
    play_digits = f"ww{digit}" if digit else ""

    params = {"call_id": call_id, **dynamic_variables}
    param_xml = "\n      ".join(
        f"<Parameter name={quoteattr(k)} value={quoteattr(str(v))}/>"
        for k, v in params.items()
    )

    play_el = f'  <Play digits="{escape(play_digits)}"/>\n' if play_digits else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        f"{play_el}"
        "  <Connect>\n"
        f"    <Stream url={quoteattr(elevenlabs_stream_url())}>\n"
        f"      {param_xml}\n"
        "    </Stream>\n"
        "  </Connect>\n"
        "</Response>\n"
    )


def place_call(call_id: str, ivr_digit: Optional[str] = None) -> str:
    """Originate the outbound call via Twilio. Returns the Twilio call SID.

    Hard compliance gate: assert_dialable refuses any number but the practice clerk.
    """
    s = get_settings()
    to_number = s.assert_dialable(s.practice_clerk_number)  # never anything else

    from twilio.rest import Client  # imported lazily so tests don't need creds

    client = Client(s.twilio_account_sid, s.twilio_auth_token)
    voice_url = f"{s.public_base_url}/voice/{call_id}"
    if ivr_digit:
        voice_url += f"?ivr_digit={ivr_digit}"

    call = client.calls.create(
        to=to_number,
        from_=s.twilio_from_number,
        url=voice_url,
        status_callback=f"{s.public_base_url}/twilio/status/{call_id}",
        status_callback_event=["initiated", "ringing", "answered", "completed"],
    )
    return call.sid
