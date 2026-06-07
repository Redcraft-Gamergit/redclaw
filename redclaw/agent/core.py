from __future__ import annotations

import ast
import operator
import re
import time

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
        self._last_messages: dict[str, tuple[str, float, int]] = {}

    async def handle_message(self, text: str, source: str = "web") -> str:
        self.logger.log("info", "chat", "Eingang", {"source": source, "text": text})
        repeat_count = self._track_repeat(text, source)
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
            result = await self._chat(text, context, repeat_count)
        elif intent.name == "memory_about_user":
            result = self._memory_about_user()
        elif intent.name == "forget_memory":
            result = self._forget(text)
        else:
            skill_name = {
                "search": "search",
                "files": "files",
                "skill_builder": "skill_builder",
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

    def _track_repeat(self, text: str, source: str) -> int:
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        now = time.monotonic()
        last_text, last_seen, count = self._last_messages.get(source, ("", 0.0, 0))
        if normalized and normalized == last_text and now - last_seen < 60:
            count += 1
        else:
            count = 1
        self._last_messages[source] = (normalized, now, count)
        return count

    async def _chat(self, text: str, context: SkillContext, repeat_count: int = 1) -> str:
        lowered = text.lower().strip()
        if lowered in {"hi", "hey", "hallo", "moin", "servus"}:
            if repeat_count > 1:
                return "Ich bin noch da. Sag mir einfach, was ich machen soll."
            return "Hey Redcrafter. RedClaw ist wach."
        calculation = self._try_calculate(text)
        if calculation is not None:
            return calculation
        if "wie geht" in lowered or "wie gehts" in lowered or "wie gehst" in lowered:
            return "Mir geht's gut. Ich bin online, Discord sitzt, Web-UI läuft. Was machen wir als Nächstes?"
        if self.settings.nvidia_nim_api_key and "nim" in self.skills.modules:
            return await self.skills.run("nim", text, context)
        return "Ich bin da. Stell mir einfach eine Frage, gib mir eine Aufgabe oder sag mir, welchen Skill ich nutzen soll."

    @staticmethod
    def _try_calculate(text: str) -> str | None:
        expression = text.lower().strip()
        expression = re.sub(r"^(was ist|wieviel ist|wie viel ist|rechne|berechne)\s+", "", expression)
        expression = expression.replace("geteilt durch", "/").replace("durch", "/")
        expression = expression.replace("plus", "+").replace("minus", "-").replace("mal", "*")
        expression = expression.replace("x", "*").replace(",", ".").strip(" ?!.")
        if not re.fullmatch(r"[0-9\s+\-*/().]+", expression):
            return None
        try:
            tree = ast.parse(expression, mode="eval")
            value = AgentCore._eval_math(tree.body)
        except Exception:
            return None
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return f"{expression} = {value}"

    @staticmethod
    def _eval_math(node: ast.AST) -> int | float:
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            return operators[type(node.op)](AgentCore._eval_math(node.left), AgentCore._eval_math(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in operators:
            return operators[type(node.op)](AgentCore._eval_math(node.operand))
        raise ValueError("unsupported expression")

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
