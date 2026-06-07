from __future__ import annotations

from redclaw.agent.intents import detect_intent


def test_reminder_intent():
    assert detect_intent("Erinnere mich in 10 Minuten an Tee").name == "reminder"


def test_nim_intent():
    assert detect_intent("Frag NVIDIA NIM nach einer Zusammenfassung").name == "nim"


def test_skill_builder_intent():
    assert detect_intent("Skill erstellen für Kalender").name == "skill_builder"
