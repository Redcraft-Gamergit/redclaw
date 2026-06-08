from __future__ import annotations

import asyncio

import pytest

from redclaw.agent.core import AgentCore
from redclaw.agent.jobs import JobQueue
from redclaw.agent.logging_service import LoggingService
from redclaw.agent.permissions import PermissionService
from redclaw.config import Settings
from redclaw.memory.db import connect, init_db
from redclaw.memory.repository import MemoryRepository
from redclaw.skills import SkillRegistry


@pytest.fixture()
def agent(tmp_path):
    settings = Settings(
        db_path=tmp_path / "redclaw.db",
        log_dir=tmp_path / "logs",
        workspace=tmp_path / "workspace",
        allowed_paths=[tmp_path / "workspace"],
    )
    settings.ensure_dirs()
    init_db(settings.db_path)
    memory = MemoryRepository(connect(settings.db_path))
    skills = SkillRegistry()
    skills.load()
    return AgentCore(
        settings=settings,
        memory=memory,
        logger=LoggingService(memory, settings.log_dir),
        permissions=PermissionService(settings.allowed_paths),
        jobs=JobQueue(),
        skills=skills,
    )


def test_chat_greeting(agent):
    answer = asyncio.run(agent.handle_message("Hey", source="discord"))
    assert answer == "Hey Redcrafter. RedClaw ist wach."


def test_chat_repeated_greeting(agent):
    asyncio.run(agent.handle_message("HEy", source="web"))
    answer = asyncio.run(agent.handle_message("HEy", source="web"))
    assert answer == "Ich bin noch da. Sag mir einfach, was ich machen soll."


def test_chat_smalltalk(agent):
    answer = asyncio.run(agent.handle_message("wie gehst so", source="discord"))
    assert "Mir geht's gut" in answer


def test_chat_calculates_simple_math(agent):
    answer = asyncio.run(agent.handle_message("was ist 1 + 1", source="discord"))
    assert answer == "1 + 1 = 2"


def test_chat_messages_are_remembered(agent):
    asyncio.run(agent.handle_message("was ist 1 + 1", source="discord"))
    remembered = agent.memory.recent_conversation(limit=4)
    values = [item.value for item in remembered]
    assert any("user@discord: was ist 1 + 1" in value for value in values)
    assert any("assistant@discord: 1 + 1 = 2" in value for value in values)


def test_chat_reports_recent_sources(agent):
    asyncio.run(agent.handle_message("hey", source="discord_testbot"))
    answer = asyncio.run(agent.handle_message("mit wem chattest du gerade", source="discord"))
    assert "Testbot" in answer
    assert "Redcrafter" in answer


def test_chat_reports_capabilities(agent):
    answer = asyncio.run(agent.handle_message("was kannst du?", source="web"))
    assert "Memory" in answer
    assert "Dateien" in answer
    assert "Codex" in answer


def test_chat_runs_multi_step_plan(agent, tmp_path):
    target = tmp_path / "workspace" / "plan-test.txt"

    answer = asyncio.run(
        agent.handle_message(
            f"erstelle datei {target} :: Hallo Plan und dann datei info {target}",
            source="web",
        )
    )

    assert "Ich fuehre 2 Schritte aus" in answer
    assert "Datei geschrieben" in answer
    assert "Typ: Datei" in answer
    assert target.read_text(encoding="utf-8") == "Hallo Plan"


def test_chat_summarizes_recent_context(agent):
    asyncio.run(agent.handle_message("ich bin Redcrafter", source="web"))
    answer = asyncio.run(agent.handle_message("was haben wir besprochen?", source="web"))
    assert "Zuletzt ging es um" in answer
    assert "Redcrafter" in answer


def test_chat_reports_recent_actions(agent, tmp_path):
    target = tmp_path / "workspace" / "aktion.txt"
    asyncio.run(agent.handle_message(f"erstelle datei {target} :: Aktion", source="web"))

    answer = asyncio.run(agent.handle_message("was hast du zuletzt gemacht?", source="web"))

    assert "Meine letzten Aktionen" in answer
    assert "aktion.txt" in answer
