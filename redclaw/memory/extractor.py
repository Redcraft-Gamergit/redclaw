from __future__ import annotations

import re


PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("preferences", "mag", re.compile(r"\bich mag ([^.!\n]+)", re.IGNORECASE)),
    ("preferences", "mag_nicht", re.compile(r"\bich mag kein(?:e|en)? ([^.!\n]+)", re.IGNORECASE)),
    ("facts", "bin", re.compile(r"\bich bin ([^.!\n]+)", re.IGNORECASE)),
    ("projects", "projekt", re.compile(r"\bprojekt ([A-Za-z0-9_\- ]+)", re.IGNORECASE)),
    ("tasks", "aufgabe", re.compile(r"\b(?:ich muss|erinnere mich daran|todo) ([^.!\n]+)", re.IGNORECASE)),
]


def extract_memories(text: str) -> list[tuple[str, str, str, float]]:
    found: list[tuple[str, str, str, float]] = []
    for category, key_prefix, pattern in PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).strip()
            if len(value) >= 2:
                key = f"{key_prefix}:{value[:48].lower()}"
                found.append((category, key, value, 0.72))
    return found
