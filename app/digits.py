"""German digit / number / date formatting.

THE make-or-break feature of this challenge is reading long IDs back cleanly, one
digit at a time. We never trust the TTS engine to normalise a number correctly;
instead we pre-expand every ID into explicit German digit/letter words in code and
feed the agent that already-spelled string.

    "50312478901"  -> "fünf, null, drei, eins, zwei, vier, sieben, acht, neun, null, eins"
    "KL202644817"  -> "K, L, zwei, null, zwei, sechs, vier, vier, acht, eins, sieben"
"""
from __future__ import annotations

DIGIT_WORDS = {
    "0": "null",
    "1": "eins",
    "2": "zwei",
    "3": "drei",
    "4": "vier",
    "5": "fünf",
    "6": "sechs",
    "7": "sieben",
    "8": "acht",
    "9": "neun",
}

_MONTHS_DE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


def spell_id(value: str, separator: str = ", ") -> str:
    """Expand an identifier into spaced German digit/letter tokens.

    Digits become their German word; letters are upper-cased and read as the letter
    itself (the TTS pronounces a lone capital letter as a letter). Any other
    character (space, dash, slash) is dropped so the cadence stays clean.
    """
    tokens = []
    for ch in str(value):
        if ch.isdigit():
            tokens.append(DIGIT_WORDS[ch])
        elif ch.isalpha():
            tokens.append(ch.upper())
        # everything else (spaces, separators) is intentionally skipped
    return separator.join(tokens)


def spell_date(value: str) -> str:
    """Turn a DD.MM.YYYY (or DD.MM.) string into spoken German.

    "12.06.2026" -> "12. Juni 2026";  "18.05." -> "18. Mai".
    Falls back to the raw string if it doesn't parse.
    """
    if not value:
        return ""
    parts = value.strip(". ").split(".")
    try:
        day = int(parts[0])
        month = int(parts[1])
        month_name = _MONTHS_DE[month - 1]
    except (ValueError, IndexError):
        return value
    out = f"{day}. {month_name}"
    if len(parts) >= 3 and parts[2].strip():
        out += f" {int(parts[2])}"
    return out
