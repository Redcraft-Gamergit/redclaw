from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import psutil

from redclaw.config import Settings


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


def run_systemcheck(settings: Settings) -> list[CheckResult]:
    settings.ensure_dirs()
    results = [
        CheckResult("Python", "ok", sys.version.split()[0]),
        CheckResult("SQLite-Datei", "ok", str(settings.db_path)),
        CheckResult("Workspace", "ok" if settings.workspace.exists() else "warn", str(settings.workspace)),
        CheckResult("Discord User-ID", "ok" if settings.discord_user_id else "warn", "gesetzt" if settings.discord_user_id else "fehlt"),
        CheckResult("Brave Search API", "ok" if settings.brave_search_api_key else "warn", "gesetzt" if settings.brave_search_api_key else "fehlt"),
        CheckResult("NVIDIA NIM API", "ok" if settings.nvidia_nim_api_key else "warn", "gesetzt" if settings.nvidia_nim_api_key else "fehlt"),
        CheckResult("Codex CLI", "ok" if shutil.which(settings.codex_command) else "warn", _codex_detail(settings)),
        CheckResult("Codex Auth", "ok" if Path("/root/.codex/auth.json").exists() else "warn", "/root/.codex/auth.json"),
        CheckResult("Docker", "ok" if shutil.which("docker") else "warn", "docker im PATH" if shutil.which("docker") else "nicht gefunden"),
        CheckResult("CPU", "ok", f"{psutil.cpu_count()} Kerne, Last {psutil.cpu_percent(interval=0.1)}%"),
        CheckResult("RAM", "ok", f"{round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 1)} GB"),
        CheckResult("Disk", "ok", f"{round(psutil.disk_usage(str(Path.cwd())).free / 1024 / 1024 / 1024, 1)} GB frei"),
    ]
    try:
        temp = settings.workspace / ".redclaw_write_test"
        temp.write_text("ok", encoding="utf-8")
        temp.unlink()
        results.append(CheckResult("Workspace Schreibrecht", "ok", str(settings.workspace)))
    except Exception as exc:
        results.append(CheckResult("Workspace Schreibrecht", "error", str(exc)))
    return results


def _codex_detail(settings: Settings) -> str:
    binary = shutil.which(settings.codex_command)
    if not binary:
        return settings.codex_command
    try:
        result = subprocess.run([settings.codex_command, "--version"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
    except Exception as exc:
        return f"{binary}, Version Fehler: {exc}"
    version = result.stdout.strip() or f"Exit {result.returncode}"
    return f"{binary}, {version}"
