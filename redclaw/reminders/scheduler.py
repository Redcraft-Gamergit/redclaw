from __future__ import annotations

from datetime import datetime
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from redclaw.memory.repository import MemoryRepository


class ReminderScheduler:
    def __init__(self, memory: MemoryRepository, send: Callable[[str], None]):
        self.memory = memory
        self.send = send
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        rows = self.memory.conn.execute("SELECT * FROM reminders WHERE done = 0").fetchall()
        for row in rows:
            due = datetime.fromisoformat(row["due_at"])
            self.scheduler.add_job(self._fire, "date", run_date=due, args=[row["id"], row["text"]])
        self.scheduler.start()

    def _fire(self, reminder_id: int, text: str) -> None:
        self.send(f"Reminder: {text}")
        self.memory.conn.execute("UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,))
        self.memory.conn.commit()
