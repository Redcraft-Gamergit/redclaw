from __future__ import annotations

import asyncio
import subprocess

from redclaw.agent.jobs import JobQueue


def test_job_queue_closes_child_stdin(monkeypatch):
    captured = {}

    class FakeStream:
        async def readline(self):
            return b""

    class FakeProc:
        stdout = FakeStream()

        async def wait(self):
            return 0

    async def fake_create_subprocess_exec(*command, **kwargs):
        captured["command"] = command
        captured["stdin"] = kwargs.get("stdin")
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    async def run_job():
        queue = JobQueue()
        job = queue.start("test", ["codex", "exec", "hello"])
        for _ in range(10):
            if job.status == "done":
                return job
            await asyncio.sleep(0)
        return job

    job = asyncio.run(run_job())

    assert captured["command"] == ("codex", "exec", "hello")
    assert captured["stdin"] is subprocess.DEVNULL
    assert job.status == "done"


def test_job_queue_passes_cwd_and_env(monkeypatch, tmp_path):
    captured = {}

    class FakeStream:
        async def readline(self):
            return b""

    class FakeProc:
        stdout = FakeStream()

        async def wait(self):
            return 0

    async def fake_create_subprocess_exec(*command, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        captured["env"] = kwargs.get("env")
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    async def run_job():
        queue = JobQueue()
        job = queue.start("test", ["python", "--version"], cwd=str(tmp_path), env={"REDCLAW_TEST": "1"})
        for _ in range(10):
            if job.status == "done":
                return job
            await asyncio.sleep(0)
        return job

    job = asyncio.run(run_job())

    assert captured["cwd"] == str(tmp_path)
    assert captured["env"]["REDCLAW_TEST"] == "1"
    assert job.status == "done"
