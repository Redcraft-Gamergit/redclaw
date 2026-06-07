from __future__ import annotations

import shutil

import psutil

SKILL = {
    "name": "system",
    "description": "Zeigt CPU, RAM, Disk, Temperatur und Docker/Codex-Status.",
    "permissions": ["system_read"],
    "enabled": True,
}


def _temperature() -> str:
    try:
        temps = psutil.sensors_temperatures()
        for values in temps.values():
            if values:
                return f"{values[0].current:.1f} C"
    except Exception:
        pass
    return "nicht verfügbar"


def run(query, context):
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(context.settings.project_root))
    lines = [
        "Systemstatus:",
        f"- CPU: {psutil.cpu_percent(interval=0.2):.1f}% auf {psutil.cpu_count()} Kernen",
        f"- RAM: {mem.percent:.1f}% genutzt ({mem.used // 1024 // 1024} MB / {mem.total // 1024 // 1024} MB)",
        f"- Disk: {disk.percent:.1f}% genutzt, {disk.free // 1024 // 1024 // 1024} GB frei",
        f"- Temperatur: {_temperature()}",
        f"- Docker: {'gefunden' if shutil.which('docker') else 'nicht gefunden'}",
        f"- Codex CLI: {'gefunden' if shutil.which(context.settings.codex_command) else 'nicht gefunden'}",
    ]
    return "\n".join(lines)
