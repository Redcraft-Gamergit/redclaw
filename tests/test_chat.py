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
