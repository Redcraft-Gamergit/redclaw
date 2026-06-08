from __future__ import annotations

from redclaw.agent.intents import detect_intent


def test_reminder_intent():
    assert detect_intent("Erinnere mich in 10 Minuten an Tee").name == "reminder"


def test_nim_intent():
    assert detect_intent("Frag NVIDIA NIM nach einer Zusammenfassung").name == "nim"


def test_skill_builder_intent():
    assert detect_intent("Skill erstellen für Kalender").name == "skill_builder"


def test_natural_file_intent():
    assert detect_intent("erstelle datei /tmp/a.txt :: hi").name == "files"
    assert detect_intent("sende datei /tmp/a.txt").name == "files"
    assert detect_intent("liste dateien /tmp").name == "files"
    assert detect_intent("datei info /tmp/a.txt").name == "files"
    assert detect_intent("Suche lokal nach langchat im Workspace").name == "files"


def test_time_intent():
    assert detect_intent("Wie spaet ist es?").name == "time"
    assert detect_intent("Wie spät ist es?").name == "time"
