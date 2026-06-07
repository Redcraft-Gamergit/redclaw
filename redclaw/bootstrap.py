from __future__ import annotations

from functools import lru_cache

from redclaw.agent import AgentCore
from redclaw.agent.jobs import JobQueue
from redclaw.agent.logging_service import LoggingService
from redclaw.agent.permissions import PermissionService
from redclaw.config import Settings, get_settings
from redclaw.memory.db import connect, init_db
from redclaw.memory.repository import MemoryRepository
from redclaw.skills import SkillRegistry


class Runtime:
    def __init__(self, settings: Settings):
        settings.ensure_dirs()
        init_db(settings.db_path)
        self.settings = settings
        self.conn = connect(settings.db_path)
        self.memory = MemoryRepository(self.conn)
        self.logger = LoggingService(self.memory, settings.log_dir)
        self.permissions = PermissionService(settings.allowed_paths)
        self.jobs = JobQueue()
        self.skills = SkillRegistry()
        self.skills.load()
        self.agent = AgentCore(settings, self.memory, self.logger, self.permissions, self.jobs, self.skills)


@lru_cache(maxsize=1)
def get_runtime() -> Runtime:
    return Runtime(get_settings())
