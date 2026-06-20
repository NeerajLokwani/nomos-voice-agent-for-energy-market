"""Local validation of energy-market identifiers.

Runs on our side (no network) so the agent never stalls mid-call. The MaLo check-digit
is computed best-effort and returned as ADVISORY only: the fixtures are synthetic and may
not carry a valid Prüfziffer, so we never hard-reject on it — we only flag.
"""
from __future__ import annotations

from typing import Optional

from .digits import spell_id


def malo_check_digit(first10: str) -> Optional[int]:
    """BDEW-style check digit for an 11-digit MaLo from its first 10 digits.

    odd-position digits *1 + even-position digits *2, summed; check = (10 - sum%10) % 10.
    Returns None if input isn't 10 digits.
    """
    if len(first10) != 10 or not first10.isdigit():
        return None
    total = 0
    for i, ch in enumerate(first10):  # i=0 is position 1 (odd)
        d = int(ch)
        total += d if i % 2 == 0 else d * 2
    return (10 - total % 10) % 10


def validate_malo(value: str) -> dict:
    digits = "".join(ch for ch in value if ch.isdigit())
    format_ok = len(digits) == 11
    check_ok = None
    if format_ok:
        expected = malo_check_digit(digits[:10])
        check_ok = expected is not None and expected == int(digits[10])
    return {
        "id_type": "malo",
        "normalized": digits,
        "format_ok": format_ok,
        "check_digit_ok": check_ok,  # advisory; synthetic IDs may be None/False
        "spoken": spell_id(digits) if digits else "",
    }


def validate_vorgangsnummer(value: str) -> dict:
    normalized = value.strip().replace(" ", "")
    return {
        "id_type": "vorgangsnummer",
        "normalized": normalized,
        "format_ok": len(normalized) >= 4,  # loose: VNB formats vary
        "check_digit_ok": None,
        "spoken": spell_id(normalized) if normalized else "",
    }


def validate(id_type: str, value: str) -> dict:
    if id_type == "malo":
        return validate_malo(value)
    return validate_vorgangsnummer(value)
