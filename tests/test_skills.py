from __future__ import annotations

from types import SimpleNamespace

from redclaw.agent.logging_service import LoggingService
from redclaw.agent.permissions import PermissionService
from redclaw.memory.db import connect, init_db
from redclaw.memory.repository import MemoryRepository
from redclaw.skills import SkillRegistry
from redclaw.skills import skill_files


def test_skill_registry_loads_examples():
    registry = SkillRegistry()
    registry.load()
    names = {skill["name"] for skill in registry.list()}
    assert {"time", "system", "search", "files", "shell", "codex", "memory", "nim", "skill_builder"}.issubset(names)


def test_file_write_is_remembered(tmp_path):
    db = tmp_path / "redclaw.db"
    init_db(db)
    memory = MemoryRepository(connect(db))
    context = SimpleNamespace(
        settings=SimpleNamespace(allowed_paths=[tmp_path]),
        permissions=PermissionService([tmp_path]),
        memory=memory,
        logger=LoggingService(memory, tmp_path / "logs"),
        source="test",
    )
    target = tmp_path / "notes" / "redclaw.txt"

    result = skill_files.run(f"datei schreibe {target} :: Hallo", context)

    assert "Datei geschrieben" in result
    assert memory.search("redclaw.txt", category="files")[0].value == f"Erstellte/geschriebene Datei: {target}"


def test_file_send_returns_attachment_marker(tmp_path):
    db = tmp_path / "redclaw.db"
    init_db(db)
    memory = MemoryRepository(connect(db))
    context = SimpleNamespace(
        settings=SimpleNamespace(allowed_paths=[tmp_path]),
        permissions=PermissionService([tmp_path]),
        memory=memory,
        logger=LoggingService(memory, tmp_path / "logs"),
        source="test",
    )
    target = tmp_path / "send.txt"
    target.write_text("Hallo", encoding="utf-8")

    result = skill_files.run(f"sende datei {target}", context)

    assert "Datei wird gesendet" in result
    assert f"__REDCLAW_ATTACH__:{target}" in result
    assert memory.search("send.txt", category="files")[0].value == f"Gesendete Datei: {target}"


def test_file_list_and_info(tmp_path):
    db = tmp_path / "redclaw.db"
    init_db(db)
    memory = MemoryRepository(connect(db))
    context = SimpleNamespace(
        settings=SimpleNamespace(allowed_paths=[tmp_path]),
        permissions=PermissionService([tmp_path]),
        memory=memory,
        logger=LoggingService(memory, tmp_path / "logs"),
        source="test",
    )
    target = tmp_path / "listed.txt"
    target.write_text("Hallo", encoding="utf-8")

    listing = skill_files.run(f"liste dateien {tmp_path}", context)
    info = skill_files.run(f"datei info {target}", context)

    assert "listed.txt" in listing
    assert "Typ: Datei" in info
    assert memory.search("listed.txt", category="files")
