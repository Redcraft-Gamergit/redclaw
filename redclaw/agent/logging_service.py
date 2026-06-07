from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from redclaw.memory.repository import MemoryRepository


class LoggingService:
    def __init__(self, repo: MemoryRepository, log_dir: Path):
        self.repo = repo
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, level: str, kind: str, message: str, meta: dict[str, Any] | None = None) -> int:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "kind": kind,
            "message": message,
            "meta": meta or {},
        }
        with (self.log_dir / f"{kind}.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return self.repo.log(level, kind, message, meta)
