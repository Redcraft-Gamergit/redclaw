from __future__ import annotations

import sys

SKILL = {
    "name": "shell",
    "description": "Startet Shell-Befehle mit Sicherheitspruefung und Live-Ausgabe.",
    "permissions": ["shell"],
    "enabled": True,
}


def run(query, context):
    command = query.removeprefix("shell").removeprefix("cmd").strip()
    if not command:
        return "Bitte gib einen Shell-Befehl an."
    decision = context.permissions.check_command(command)
    context.logger.log("info", "shell", "Shell-Befehl bewertet", {"command": command, "level": decision.level, "reason": decision.reason})
    if decision.level == "blocked":
        return f"Blockiert: {decision.reason}"
    if decision.needs_confirmation:
        return f"Dafuer brauche ich deine Bestaetigung: {decision.reason}"
    runner = ["powershell", "-NoProfile", "-Command", command] if sys.platform.startswith("win") else ["/bin/bash", "-lc", command]
    job = context.jobs.start("shell", runner)
    return f"Shell-Job #{job.id} gestartet. Die Ausgabe erscheint live im Web-UI."
