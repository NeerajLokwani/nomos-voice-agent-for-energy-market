"""Load synthetic cases from fixtures.json and build the per-call dynamic variables.

Compliance: these are the ONLY case facts the agent ever uses. Everything the agent
speaks comes from here (or is read back from the clerk live) — never invented.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from .digits import spell_date, spell_id

FIXTURES_PATH = Path(__file__).resolve().parent.parent / "fixtures.json"


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    with open(FIXTURES_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def list_cases() -> List[dict]:
    return _load_raw().get("cases", [])


def get_case(case_id: str) -> Optional[dict]:
    for case in list_cases():
        if case.get("id") == case_id:
            return case
    return None


def build_dynamic_variables(case: dict) -> Dict[str, str]:
    """Build the dynamic-variable payload handed to the ElevenLabs agent at call start.

    Includes pre-spelled digit tokens for any ID/date the agent must speak, so the
    TTS never compresses a number. Keys are referenced by name in the agent prompt.
    """
    malo = case.get("malo_id", "")
    return {
        "case_id": case.get("id", ""),
        "case_title": case.get("case_title", ""),
        "lieferant": case.get("lieferant", ""),
        "vnb_name": case.get("vnb_name", ""),
        "lieferstelle": case.get("lieferstelle", ""),
        "zaehlernummer": case.get("zaehlernummer", ""),
        "malo_id": malo,
        # pre-spelled, digit-by-digit, German — the agent reads THIS, not the raw number
        "malo_id_spoken": spell_id(malo),
        "zaehlernummer_spoken": spell_id(case.get("zaehlernummer", "")),
        "anmeldung_datum": case.get("anmeldung_datum", ""),
        "anmeldung_datum_spoken": spell_date(case.get("anmeldung_datum", "")),
        "lieferbeginn": case.get("lieferbeginn", ""),
        "lieferbeginn_spoken": spell_date(case.get("lieferbeginn", "")),
        "statustext": case.get("statustext", ""),
        "symptom": case.get("symptom", ""),
        "goal": case.get("goal", ""),
    }
