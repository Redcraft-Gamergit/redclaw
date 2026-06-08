from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


SKILL = {
    "name": "codex",
    "description": "Startet Codex CLI als überwachten Job.",
    "permissions": ["codex", "shell"],
    "enabled": True,
}


def run(query, context):
    prompt = query.strip()
    if not prompt:
        return "Bitte gib eine Codex-Aufgabe an. Beispiele: `codex status`, `codex verbessere den search skill`, `codex review`."
    lowered = prompt.lower()
    if lowered in {"status", "codex status", "test", "codex test", "selbsttest"}:
        return _status(context)
    if lowered.startswith("codex "):
        prompt = prompt[6:].strip()
    if not prompt:
        return "Bitte gib nach `codex` noch eine Aufgabe an."

    command = _codex_command(context, prompt)
    workdir = str(context.settings.project_root)
    env = {"CODEX_HOME": "/root/.codex"}
    context.logger.log("info", "codex", "Codex-Job gestartet", {"prompt": prompt, "cwd": workdir})
    job = context.jobs.start("codex", command, cwd=workdir, env=env)
    context.memory.save("tasks", f"codex-job:{job.id}", f"Codex-Job #{job.id}: {prompt}", source=context.source, confidence=0.9)
    return f"Codex-Job #{job.id} gestartet. Arbeitsordner: {workdir}. Ich streame die Ausgabe ins Web-UI."


def _codex_command(context, prompt: str) -> list[str]:
    return [
        context.settings.codex_command,
        "exec",
        "--json",
        "--sandbox",
        "danger-full-access",
        "--cd",
        str(Path(context.settings.project_root)),
        "--add-dir",
        str(Path(context.settings.workspace)),
        "--skip-git-repo-check",
        prompt,
    ]


def _status(context) -> str:
    binary = shutil.which(context.settings.codex_command)
    if not binary:
        return f"Codex CLI nicht gefunden: {context.settings.codex_command}"
    home = Path("/root/.codex")
    auth = home / "auth.json"
    config = home / "config.toml"
    lines = [
        "Codex Status:",
        f"- CLI: {binary}",
        f"- Version: {_version(context.settings.codex_command)}",
        f"- CODEX_HOME: {home} ({'ok' if home.exists() else 'fehlt'})",
        f"- Auth: {'ok' if auth.exists() else 'fehlt'}",
        f"- Config: {'ok' if config.exists() else 'fehlt'}",
        f"- Projekt: {context.settings.project_root}",
        f"- Workspace: {context.settings.workspace}",
        "- Sandbox: danger-full-access im Docker-Container, Ausgabe überwacht im Web-UI",
    ]
    return "\n".join(lines)


def _version(command: str) -> str:
    try:
        result = subprocess.run([command, "--version"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)
    except Exception as exc:
        return f"Fehler: {exc}"
    return result.stdout.strip() or f"Exit {result.returncode}"
