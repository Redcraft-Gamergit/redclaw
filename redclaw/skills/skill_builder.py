from __future__ import annotations

SKILL = {
    "name": "skill_builder",
    "description": "Lässt Codex CLI einen neuen RedClaw-Skill erstellen und Tests ausführen.",
    "permissions": ["codex", "file_write", "shell"],
    "enabled": True,
}


def run(query, context):
    prompt = f"""
Erstelle oder verbessere einen RedClaw-Skill passend zu dieser Anfrage:

{query}

Arbeite im bestehenden Projekt. Schreibe den Skill direkt nach redclaw/skills/.
Jeder Skill braucht ein SKILL-Manifest und run(query, context). Füge passende
Tests unter tests/ hinzu und führe pytest aus. Halte die Änderung klein und
kompatibel mit dem bestehenden SkillRegistry-System.
""".strip()
    job = context.jobs.start(
        "codex",
        [
            context.settings.codex_command,
            "exec",
            "--json",
            "--sandbox",
            "workspace-write",
            "--skip-git-repo-check",
            prompt,
        ],
    )
    context.logger.log("info", "codex", "Skill-Builder gestartet", {"job_id": job.id, "query": query})
    return f"Skill-Builder Job #{job.id} gestartet. Codex schreibt den Skill und führt Tests aus."
