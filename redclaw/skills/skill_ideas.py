from __future__ import annotations


SKILL = {
    "name": "ideas",
    "description": "Schlägt sinnvolle RedClaw-Erweiterungen vor.",
    "permissions": [],
    "enabled": True,
}


IDEAS = [
    ("Datei-Inbox", "Discord-Anhänge automatisch speichern, kategorisieren und im Memory verlinken."),
    ("Approval-Panel", "Gefährliche Aktionen als Webkarten anzeigen: erlauben, ablehnen, einmalig freigeben."),
    ("Skill-Market", "Skills im Web erstellen, testen, aktivieren und versionieren."),
    ("Long-Context-Chat", "Gespräche zusammenfassen und relevante Memorys vor jeder Antwort gezielt laden."),
    ("Pi-Monitor", "Temperatur, RAM, Docker-Container und Speicher als Live-Kacheln mit Warnungen."),
    ("Quellen-Archiv", "Websuchen mit Quellen, Datum, Kurzfassung und Tags dauerhaft speichern."),
    ("Codex-Werkstatt", "Codex-Jobs mit Diff-Ansicht, Teststatus und Button zum Übernehmen/Rückgängig machen."),
    ("Voice-Routine", "Edge-TTS Antworten plus Push-to-talk und Sprachbefehle für Skills."),
]


def run(query, context):
    lines = ["Sinnvolle nächste RedClaw-Upgrades:"]
    for index, (name, detail) in enumerate(IDEAS, 1):
        lines.append(f"{index}. {name}: {detail}")
    context.memory.save("projects", "redclaw:ideas:last", "RedClaw Upgrade-Ideen wurden angefragt.", source=context.source, confidence=0.75)
    return "\n".join(lines)
