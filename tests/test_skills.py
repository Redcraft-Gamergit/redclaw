from __future__ import annotations

from redclaw.skills import SkillRegistry


def test_skill_registry_loads_examples():
    registry = SkillRegistry()
    registry.load()
    names = {skill["name"] for skill in registry.list()}
    assert {"time", "system", "search", "files", "shell", "codex", "memory", "nim", "skill_builder"}.issubset(names)
