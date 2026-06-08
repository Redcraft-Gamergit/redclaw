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


ACTION_INTENTS = {"search", "files", "skill_builder", "shell", "codex", "ideas", "nim", "time", "system", "reminder"}


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
        self._remember_message("user", text, source)
        for category, key, value, confidence in extract_memories(text):
            self.memory.save(category, key, value, source=source, confidence=confidence)
        context = SkillContext(
            settings=self.settings,
            memory=self.memory,
            logger=self.logger,
            permissions=self.permissions,
            jobs=self.jobs,
            source=source,
        )
        plan = self._plan_steps(text)
        if len(plan) > 1:
            result = await self._run_plan(plan, context)
        else:
            result = await self._run_single(text, context, repeat_count)
        self._remember_message("assistant", result, source)
        self.logger.log("info", "chat", "Antwort", {"source": source, "text": result})
        return result

    def _plan_steps(self, text: str) -> list[str]:
        raw_steps = re.split(r"\s*(?:;|\bund dann\b|\bdanach\b|\banschliessend\b|\banschließend\b)\s*", text, flags=re.IGNORECASE)
        steps = [step.strip(" ,.") for step in raw_steps if step.strip(" ,.")]
        if len(steps) < 2:
            return [text]
        intents = [detect_intent(step).name for step in steps]
        actionable_count = sum(1 for name in intents if name in ACTION_INTENTS or name in {"memory_about_user", "forget_memory"})
        return steps[:6] if actionable_count >= 2 else [text]

    async def _run_plan(self, steps: list[str], context: SkillContext) -> str:
        self.logger.log("info", "agent", "Mehrschritt-Plan gestartet", {"steps": steps})
        lines = [f"Ich fuehre {len(steps)} Schritte aus:"]
        for index, step in enumerate(steps, 1):
            result = await self._run_single(step, context, repeat_count=1, allow_nim_fallback=False)
            self.memory.save(
                "tasks",
                f"agent-step:{int(time.time())}:{index}",
                f"Schritt {index}: {step} -> {result[:300]}",
                source=context.source,
                confidence=0.82,
            )
            lines.append(f"{index}. {step}\n   {self._compact_result(result)}")
        return "\n".join(lines)

    async def _run_single(self, text: str, context: SkillContext, repeat_count: int = 1, allow_nim_fallback: bool = True) -> str:
        intent = detect_intent(text)
        if intent.name == "chat":
            return await self._chat(text, context, repeat_count, allow_nim_fallback=allow_nim_fallback)
        if intent.name == "memory_about_user":
            return self._memory_about_user()
        if intent.name == "forget_memory":
            return self._forget(text)
        skill_name = {
            "search": "search",
            "files": "files",
            "skill_builder": "skill_builder",
            "shell": "shell",
            "codex": "codex",
            "ideas": "ideas",
            "nim": "nim",
            "time": "time",
            "system": "system",
            "reminder": "memory",
        }.get(intent.name, intent.name)
        return await self.skills.run(skill_name, intent.query, context)

    @staticmethod
    def _compact_result(result: str) -> str:
        clean = re.sub(r"\s+", " ", result).strip()
        return clean if len(clean) <= 360 else clean[:357] + "..."

    def _remember_message(self, role: str, text: str, source: str) -> None:
        clean = re.sub(r"\s+", " ", text).strip()
        if not clean:
            return
        snippet = clean[:700]
        key = f"{int(time.time())}:{role}:{source}"
        self.memory.save("conversation", key, f"{role}@{source}: {snippet}", source=source, confidence=0.9)

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

    async def _chat(self, text: str, context: SkillContext, repeat_count: int = 1, allow_nim_fallback: bool = True) -> str:
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
        if "mit wem" in lowered and ("chattest" in lowered or "redest" in lowered or "sprichst" in lowered):
            return self._conversation_sources()
        if ("worum" in lowered and ("ging" in lowered or "geht" in lowered)) or "was haben wir besprochen" in lowered:
            return self._recent_conversation_summary()
        if "was hast du zuletzt" in lowered or "letzte aktion" in lowered or "letzten schritte" in lowered:
            return self._recent_action_summary()
        if "was kannst du" in lowered or "faehigkeiten" in lowered or "fähigkeiten" in lowered:
            return self._capabilities_summary()
        if allow_nim_fallback and self.settings.nvidia_nim_api_key and "nim" in self.skills.modules:
            return await self.skills.run("nim", text, context)
        return "Ich bin da. Stell mir einfach eine Frage, gib mir eine Aufgabe oder sag mir, welchen Skill ich nutzen soll."

    def _conversation_sources(self) -> str:
        recent = self.memory.recent_conversation(limit=30)
        sources: list[str] = []
        for item in recent:
            label = {
                "discord": "Redcrafter per Discord-DM",
                "discord_testbot": "der Testbot per Discord-DM",
                "web": "du im Web-Chat",
                "web_voice": "du per Voice im Web",
            }.get(item.source or "", item.source or "unbekannte Quelle")
            if label not in sources:
                sources.append(label)
        if not sources:
            return "Gerade habe ich noch keinen gespeicherten Gesprächskontext."
        return "Ich habe zuletzt mit diesen Quellen gesprochen: " + ", ".join(sources) + "."

    def _capabilities_summary(self) -> str:
        skills = [skill for skill in self.skills.list() if skill["enabled"]]
        names = ", ".join(skill["name"] for skill in skills)
        return (
            "Ich kann chatten, rechnen, Memory nutzen, Erinnerungen setzen, Dateien in erlaubten Ordnern lesen/schreiben/senden, "
            "lokal oder per Web-API suchen, Systemwerte pruefen, Shell/Codex-Jobs ueberwacht starten, Ideen vorschlagen und Skills erweitern. "
            f"Aktive Skills: {names}."
        )

    def _recent_conversation_summary(self) -> str:
        recent = self.memory.recent_conversation(limit=12)
        if not recent:
            return "Ich habe noch keinen gespeicherten Gespraechskontext."
        lines = ["Zuletzt ging es um:"]
        for item in recent[-6:]:
            lines.append(f"- {item.value}")
        return "\n".join(lines)

    def _recent_action_summary(self) -> str:
        tasks = self.memory.list_by_category("tasks", limit=6)
        files = self.memory.list_by_category("files", limit=4)
        if not tasks and not files:
            return "Ich habe noch keine gespeicherten Aktionen."
        lines = ["Meine letzten Aktionen:"]
        for item in tasks[:4]:
            lines.append(f"- {item.value}")
        for item in files[:3]:
            lines.append(f"- {item.value}")
        return "\n".join(lines)

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
