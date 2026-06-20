"""Central configuration. Loaded once from the environment.

The single most important value here is PRACTICE_CLERK_NUMBER: a hard compliance
guardrail. The agent may ONLY ever dial this number (the Nomos practice clerk),
never a real grid operator. `assert_dialable()` enforces it in code.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _clean(num: str) -> str:
    """Normalise a phone number for comparison (strip spaces, dashes, parens)."""
    return "".join(ch for ch in (num or "") if ch.isdigit() or ch == "+")


class Settings:
    def __init__(self) -> None:
        self.practice_clerk_number = _clean(os.getenv("PRACTICE_CLERK_NUMBER", ""))

        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_from_number = _clean(os.getenv("TWILIO_FROM_NUMBER", ""))

        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "")
        self.elevenlabs_agent_id = os.getenv("ELEVENLABS_AGENT_ID", "")
        self.elevenlabs_phone_number_id = os.getenv("ELEVENLABS_PHONE_NUMBER_ID", "")

        self.public_base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
        self.store_path = os.getenv("STORE_PATH", "./data/results.json")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.summary_model = os.getenv("SUMMARY_MODEL", "gpt-4o")
        self.email_mode = os.getenv("EMAIL_MODE", "mock")
        self.resend_api_key = os.getenv("RESEND_API_KEY", "")
        self.email_from = os.getenv("EMAIL_FROM", "Nomos Voice Agent <noreply@example.com>")
        self.email_to_nomos = os.getenv("EMAIL_TO_NOMOS", "")
        self.email_to_test = os.getenv("EMAIL_TO_TEST", "")

        # The keypad digit that reaches a human on the practice line's menu.
        # For the real practice clerk there is ONE menu; per-call overrides are used
        # only when pointing the agent at the (per-case) Helga simulator.
        self.practice_ivr_digit = os.getenv("PRACTICE_IVR_DIGIT", "1")

    def assert_dialable(self, number: str) -> str:
        """Compliance gate: refuse to dial anything but the configured practice number.

        Returns the normalised number on success, raises ValueError otherwise.
        """
        target = _clean(number)
        if not self.practice_clerk_number:
            raise ValueError(
                "PRACTICE_CLERK_NUMBER is not configured. Refusing to place any call."
            )
        if target != self.practice_clerk_number:
            raise ValueError(
                "Refusing to dial a number other than the configured practice clerk. "
                "Synthetic-data / practice-number-only rule is enforced in code."
            )
        return target


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
