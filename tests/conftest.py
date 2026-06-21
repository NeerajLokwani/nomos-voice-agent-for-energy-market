"""Test environment defaults — keep the suite deterministic and offline.

These run before any app module imports load .env (app.config calls load_dotenv with
override=False, so values set here win). We disable the optional LLM refine pass and the
webhook signature check so tests never depend on network or secrets.
"""
import os

os.environ["NOMOS_LLM_PROVIDER"] = ""        # no live OpenAI calls during tests
os.environ["ELEVENLABS_WEBHOOK_SECRET"] = ""  # skip HMAC verification in tests
