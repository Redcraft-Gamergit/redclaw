from __future__ import annotations

from redclaw.memory.db import connect, init_db
from redclaw.memory.repository import MemoryRepository


def test_memory_save_search_delete(tmp_path):
    db = tmp_path / "redclaw.db"
    init_db(db)
    repo = MemoryRepository(connect(db))
    memory_id = repo.save("preferences", "farbe", "Rot ist gut", source="test")
    assert repo.get("preferences", "farbe").value == "Rot ist gut"
    assert repo.search("rot")[0].id == memory_id
    assert repo.delete(memory_id)
    assert repo.search("rot") == []
