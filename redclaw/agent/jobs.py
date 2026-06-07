from __future__ import annotations

import asyncio
import itertools
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Job:
    id: int
    kind: str
    command: list[str]
    status: str = "queued"
    output: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


class JobQueue:
    def __init__(self):
        self._ids = itertools.count(1)
        self.jobs: dict[int, Job] = {}
        self._tasks: dict[int, asyncio.Task[None]] = {}
        self._subscribers: list[Callable[[Job, str], None]] = []

    def subscribe(self, callback: Callable[[Job, str], None]) -> None:
        self._subscribers.append(callback)

    def start(self, kind: str, command: list[str]) -> Job:
        job = Job(id=next(self._ids), kind=kind, command=command)
        self.jobs[job.id] = job
        self._tasks[job.id] = asyncio.create_task(self._run(job))
        return job

    def stop_all(self) -> int:
        count = 0
        for task in self._tasks.values():
            if not task.done():
                task.cancel()
                count += 1
        for job in self.jobs.values():
            if job.status in {"queued", "running"}:
                job.status = "cancelled"
        return count

    async def _run(self, job: Job) -> None:
        job.status = "running"
        self._emit(job, f"Starte Job #{job.id}: {' '.join(job.command)}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *job.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert proc.stdout is not None
            async for line in self._read_lines(proc.stdout):
                job.output.append(line)
                self._emit(job, line)
            code = await proc.wait()
            job.status = "done" if code == 0 else "failed"
            self._emit(job, f"Job #{job.id} beendet mit Code {code}.")
        except asyncio.CancelledError:
            job.status = "cancelled"
            self._emit(job, f"Job #{job.id} wurde gestoppt.")
        except Exception as exc:
            job.status = "failed"
            self._emit(job, f"Job #{job.id} Fehler: {exc}")

    async def _read_lines(self, stream: asyncio.StreamReader) -> AsyncIterator[str]:
        while True:
            raw = await stream.readline()
            if not raw:
                break
            yield raw.decode(errors="replace").rstrip()

    def _emit(self, job: Job, text: str) -> None:
        for callback in self._subscribers:
            callback(job, text)
