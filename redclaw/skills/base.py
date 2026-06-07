from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from redclaw.agent.jobs import JobQueue
from redclaw.agent.logging_service import LoggingService
from redclaw.agent.permissions import PermissionService
from redclaw.config import Settings
from redclaw.memory.repository import MemoryRepository


@dataclass
class SkillContext:
    settings: Settings
    memory: MemoryRepository
    logger: LoggingService
    permissions: PermissionService
    jobs: JobQueue
    source: str = "web"


class SkillRegistry:
    def __init__(self, package: str = "redclaw.skills"):
        self.package = package
        self.modules: dict[str, ModuleType] = {}

    def load(self) -> None:
        package_module = importlib.import_module(self.package)
        package_path = Path(package_module.__file__).parent
        for module_info in pkgutil.iter_modules([str(package_path)]):
            if not module_info.name.startswith("skill_"):
                continue
            module = importlib.import_module(f"{self.package}.{module_info.name}")
            meta = getattr(module, "SKILL", {})
            name = meta.get("name", module_info.name.replace("skill_", ""))
            self.modules[name] = module

    def list(self) -> list[dict[str, Any]]:
        skills: list[dict[str, Any]] = []
        for name, module in sorted(self.modules.items()):
            meta = getattr(module, "SKILL", {})
            skills.append(
                {
                    "name": name,
                    "description": meta.get("description", ""),
                    "permissions": meta.get("permissions", []),
                    "enabled": meta.get("enabled", True),
                }
            )
        return skills

    async def run(self, name: str, query: str, context: SkillContext) -> str:
        module = self.modules.get(name)
        if not module:
            context.logger.log("warn", "skill", "Skill nicht gefunden", {"skill": name})
            return f"Ich finde den Skill `{name}` nicht."
        meta = getattr(module, "SKILL", {})
        if meta.get("enabled", True) is False:
            return f"Der Skill `{name}` ist deaktiviert."
        context.logger.log("info", "skill", "Skill gestartet", {"skill": name, "query": query})
        run = getattr(module, "run")
        if inspect.iscoroutinefunction(run):
            result = await run(query, context)
        else:
            result = run(query, context)
        context.logger.log("info", "skill", "Skill beendet", {"skill": name})
        return str(result)
