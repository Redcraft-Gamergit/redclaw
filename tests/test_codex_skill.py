from __future__ import annotations

from types import SimpleNamespace

from redclaw.agent.jobs import JobQueue
from redclaw.agent.logging_service import LoggingService
from redclaw.agent.permissions import PermissionService
from redclaw.memory.db import connect, init_db
from redclaw.memory.repository import MemoryRepository
from redclaw.skills import skill_codex


def test_codex_command_uses_project_and_workspace(tmp_path):
    context = SimpleNamespace(
        settings=SimpleNamespace(codex_command="codex", project_root=tmp_path / "project", workspace=tmp_path / "workspace"),
    )

    command = skill_codex._codex_command(context, "mach was")

    assert command[:4] == ["codex", "exec", "--json", "--sandbox"]
    assert "danger-full-access" in command
    assert "--cd" in command
    assert str(tmp_path / "project") in command
    assert "--add-dir" in command
    assert str(tmp_path / "workspace") in command
    assert command[-1] == "mach was"


def test_codex_run_starts_job_with_cwd_and_env(tmp_path):
    db = tmp_path / "redclaw.db"
    init_db(db)
    memory = MemoryRepository(connect(db))
    jobs = JobQueue()
    captured = {}

    def fake_start(kind, command, cwd=None, env=None):
        captured.update({"kind": kind, "command": command, "cwd": cwd, "env": env})
        return SimpleNamespace(id=7)

    jobs.start = fake_start
    context = SimpleNamespace(
        settings=SimpleNamespace(codex_command="codex", project_root=tmp_path / "project", workspace=tmp_path / "workspace"),
        jobs=jobs,
        logger=LoggingService(memory, tmp_path / "logs"),
        memory=memory,
        permissions=PermissionService([tmp_path]),
        source="test",
    )

    result = skill_codex.run("codex verbessere dashboard", context)

    assert "Codex-Job #7 gestartet" in result
    assert captured["kind"] == "codex"
    assert captured["cwd"] == str(tmp_path / "project")
    assert captured["env"] == {"CODEX_HOME": "/root/.codex"}
    assert captured["command"][-1] == "verbessere dashboard"
