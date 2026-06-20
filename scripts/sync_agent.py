"""Push our prompt, first message, language and tools into the ElevenLabs agent.

Run once during setup and after changing app/agent_prompt.py.

    python -m scripts.sync_agent                # keep current voice
    python -m scripts.sync_agent <voice_id>     # also set the voice
"""
import sys

from app.elevenlabs_client import sync_agent

if __name__ == "__main__":
    voice_id = sys.argv[1] if len(sys.argv) > 1 else None
    result = sync_agent(voice_id=voice_id)
    print("Agent synced.", "voice:", voice_id or "(unchanged)")
    print("agent_id:", result.get("agent_id", "?"))
