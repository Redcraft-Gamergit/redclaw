from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    name: str
    query: str
    confidence: float = 1.0


def detect_intent(text: str) -> Intent:
    lowered = text.lower().strip()
    if re.search(r"\berinnere mich\b|\breminder\b", lowered):
        return Intent("reminder", text)
    if lowered.startswith("vergiss ") or "vergiss, dass" in lowered:
        return Intent("forget_memory", text)
    if "was weißt du über mich" in lowered or "was weisst du ueber mich" in lowered or "was weisst du über mich" in lowered:
        return Intent("memory_about_user", text)
    if lowered.startswith("suche ") or "websuche" in lowered:
        return Intent("search", text)
    if (
        lowered.startswith("datei ")
        or "lies datei" in lowered
        or "durchsuche" in lowered
        or "erstelle datei" in lowered
        or "schreibe datei" in lowered
        or "sende datei" in lowered
        or "schick datei" in lowered
    ):
        return Intent("files", text)
    if lowered.startswith("shell ") or lowered.startswith("cmd "):
        return Intent("shell", text)
    if "skill bauen" in lowered or "skill erstellen" in lowered or "neuen skill" in lowered:
        return Intent("skill_builder", text)
    if "codex" in lowered:
        return Intent("codex", text)
    if "nvidia" in lowered or "nim" in lowered:
        return Intent("nim", text)
    if "uhrzeit" in lowered or "datum" in lowered:
        return Intent("time", text)
    if "cpu" in lowered or "ram" in lowered or "temperatur" in lowered or "system" in lowered:
        return Intent("system", text)
    return Intent("chat", text, 0.55)
