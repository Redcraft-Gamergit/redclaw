from __future__ import annotations

from redclaw.agent.intents import detect_intent
from redclaw.agent.jobs import JobQueue
from redclaw.agent.logging_service import LoggingService
from redclaw.agent.permissions import PermissionService
from redclaw.config import Settings
from redclaw.memory.extractor import extract_memories
from redclaw.memory.repository import MemoryRepository
from redclaw.skills.base import SkillContext, SkillRegistry


class AgentCore:
    def __init__(
        self,
        settings: Settings,
        memory: MemoryRepository,
        logger: LoggingService,
        permissions: PermissionService,
        jobs: JobQueue,
        skills: SkillRegistry,
    ):
        self.settings = settings
        self.memory = memory
        self.logger = logger
        self.permissions = permissions
        self.jobs = jobs
        self.skills = skills

    async def handle_message(self, text: str, source: str = "web") -> str:
        self.logger.log("info", "chat", "Eingang", {"source": source, "text": text})
        for category, key, value, confidence in extract_memories(text):
            self.memory.save(category, key, value, source=source, confidence=confidence)
        intent = detect_intent(text)
        context = SkillContext(
            settings=self.settings,
            memory=self.memory,
            logger=self.logger,
            permissions=self.permissions,
            jobs=self.jobs,
            source=source,
        )
        if intent.name == "chat":
            result = self._chat(text)
        elif intent.name == "memory_about_user":
            result = self._memory_about_user()
        elif intent.name == "forget_memory":
            result = self._forget(text)
        else:
            skill_name = {
                "search": "search",
                "files": "files",
                "shell": "shell",
                "codex": "codex",
                "nim": "nim",
                "time": "time",
                "system": "system",
                "reminder": "memory",
            }.get(intent.name, intent.name)
            result = await self.skills.run(skill_name, intent.query, context)
        self.logger.log("info", "chat", "Antwort", {"source": source, "text": result})
        return result

    def _chat(self, text: str) -> str:
        if "hallo" in text.lower() or "hey" in text.lower():
            return "Hey Redcrafter. RedClaw ist wach."
        return "Ich habe dich verstanden. Wenn du willst, kann ich suchen, Skills ausführen, Dateien prüfen, Shell-Befehle starten oder Codex beauftragen."

    def _memory_about_user(self) -> str:
        items = self.memory.all(limit=80)
        if not items:
            return "Ich habe noch keine gespeicherten Fakten über dich."
        lines = ["Das weiß ich aktuell:"]
        for item in items:
            lines.append(f"- [{item.category}] {item.value}")
        return "\n".join(lines)

    def _forget(self, text: str) -> str:
        query = text.lower().replace("vergiss", "").replace("dass", "").strip(" ,.")
        matches = self.memory.search(query, limit=5) if query else []
        if not matches:
            return "Ich habe dazu keinen passenden gespeicherten Fakt gefunden."
        for item in matches:
            self.memory.delete(item.id)
        return f"Erledigt. Ich habe {len(matches)} passenden Fakt vergessen."
