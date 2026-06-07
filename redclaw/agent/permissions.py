from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PermissionDecision:
    level: str
    reason: str

    @property
    def allowed(self) -> bool:
        return self.level == "safe"

    @property
    def needs_confirmation(self) -> bool:
        return self.level == "needs_confirmation"


DANGEROUS_TOKENS = {
    "rm",
    "del",
    "erase",
    "rmdir",
    "format",
    "shutdown",
    "reboot",
    "mkfs",
    "dd",
    "systemctl",
    "service",
    "docker",
    "curl",
    "wget",
    "Invoke-WebRequest",
    "iwr",
}

INSTALL_TOKENS = {"apt", "apt-get", "pip", "pip3", "npm", "pnpm", "yarn"}


class PermissionService:
    def __init__(self, allowed_paths: list[Path]):
        self.allowed_paths = [p.expanduser().resolve() for p in allowed_paths]

    def check_path(self, path: Path) -> PermissionDecision:
        resolved = path.expanduser().resolve()
        for allowed in self.allowed_paths:
            if resolved == allowed or allowed in resolved.parents:
                return PermissionDecision("safe", f"Pfad liegt im erlaubten Bereich: {allowed}")
        return PermissionDecision("needs_confirmation", f"Pfad ist noch nicht freigegeben: {resolved}")

    def check_command(self, command: str) -> PermissionDecision:
        try:
            parts = shlex.split(command, posix=False)
        except ValueError:
            return PermissionDecision("blocked", "Befehl kann nicht sicher geparst werden.")
        lowered = [p.strip().lower() for p in parts]
        if not lowered:
            return PermissionDecision("blocked", "Leerer Befehl.")
        joined = " ".join(lowered)
        if ":(){:|:&};:" in joined or "format c:" in joined or "mkfs" in lowered:
            return PermissionDecision("blocked", "Befehl wirkt systemzerstoerend.")
        if any(token in lowered for token in INSTALL_TOKENS):
            return PermissionDecision("needs_confirmation", "Paketinstallation braucht Bestaetigung.")
        if any(token.lower() in lowered for token in DANGEROUS_TOKENS):
            return PermissionDecision("needs_confirmation", "Gefaehrlicher System-, Docker-, Download- oder Loeschbefehl.")
        if ">" in parts or ">>" in parts:
            return PermissionDecision("needs_confirmation", "Umleitung kann Dateien ueberschreiben.")
        return PermissionDecision("safe", "Befehl ist nach Regelwerk unkritisch.")
