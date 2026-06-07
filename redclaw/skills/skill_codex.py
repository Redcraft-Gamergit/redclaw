from __future__ import annotations

SKILL = {
    "name": "codex",
    "description": "Startet Codex CLI als ueberwachten Job.",
    "permissions": ["codex", "shell"],
    "enabled": True,
}


def run(query, context):
    prompt = query.strip()
    if not prompt:
        return "Bitte gib eine Codex-Aufgabe an."
    command = [
        context.settings.codex_command,
        "exec",
        "--json",
        "--sandbox",
        "workspace-write",
        "--skip-git-repo-check",
        prompt,
    ]
    context.logger.log("info", "codex", "Codex-Job gestartet", {"prompt": prompt})
    job = context.jobs.start("codex", command)
    return f"Codex-Job #{job.id} gestartet. Ich streame die Ausgabe ins Web-UI."
