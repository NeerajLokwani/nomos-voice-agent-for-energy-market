"""Render the opener + a digit-readback line in candidate German voices, so you can
pick the warmest one for the first 10 seconds (and confirm digit-by-digit reading).

Saves mp3s to ./data/voice_ab/<voice_id>.mp3. Needs ELEVENLABS_API_KEY.

    python -m scripts.voice_ab <voice_id_1> <voice_id_2> ...

Pick German-native voices from your ElevenLabs library and pass their IDs. Eyeball
(ear-ball) the result and wire the winner via `python -m scripts.sync_agent <voice_id>`.
"""
import sys
from pathlib import Path

import httpx

from app.config import get_settings
from app.digits import spell_id

# A representative line: warm AI-disclosure opener + an 11-digit MaLo read digit by digit.
SAMPLE_TEXT = (
    "Guten Tag, hier spricht ein KI-Assistent im Auftrag des Stromlieferanten Nomos. "
    "Darf ich Ihnen die Marktlokation ansagen? Das wäre die "
    + spell_id("50312478901")
    + "."
)

MODEL_ID = "eleven_multilingual_v2"


def render(voice_id: str, out_dir: Path) -> Path:
    s = get_settings()
    if not s.elevenlabs_api_key:
        sys.exit("set ELEVENLABS_API_KEY")
    resp = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": s.elevenlabs_api_key, "Content-Type": "application/json"},
        json={
            "text": SAMPLE_TEXT,
            "model_id": MODEL_ID,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=60,
    )
    resp.raise_for_status()
    out = out_dir / f"{voice_id}.mp3"
    out.write_bytes(resp.content)
    return out


if __name__ == "__main__":
    voice_ids = sys.argv[1:]
    if not voice_ids:
        sys.exit("usage: python -m scripts.voice_ab <voice_id> [<voice_id> ...]")
    out_dir = Path("./data/voice_ab")
    out_dir.mkdir(parents=True, exist_ok=True)
    print("Sample:", SAMPLE_TEXT, "\n")
    for vid in voice_ids:
        path = render(vid, out_dir)
        print("wrote", path)
