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


def test_memory_saves_structured_tables(tmp_path):
    db = tmp_path / "redclaw.db"
    init_db(db)
    repo = MemoryRepository(connect(db))

    conversation_id = repo.save("conversation", "1:user:web", "user@web: Hallo RedClaw", source="web")
    fact_id = repo.save("facts", "bin:test", "Tester", source="test", confidence=0.8)
    preference_id = repo.save("preferences", "mag:rot", "Rot", source="test", confidence=0.9)
    task_id = repo.save("tasks", "todo:check", "Dashboard pruefen", source="test")
    file_id = repo.save("files", "written:/tmp/redclaw.txt", "Erstellte Datei: /tmp/redclaw.txt", source="test")

    conn = repo.conn
    assert conn.execute("SELECT message FROM conversation_memory WHERE memory_id = ?", (conversation_id,)).fetchone()["message"] == "Hallo RedClaw"
    assert conn.execute("SELECT fact_value FROM fact_memory WHERE memory_id = ?", (fact_id,)).fetchone()["fact_value"] == "Tester"
    assert conn.execute("SELECT preference_value FROM preference_memory WHERE memory_id = ?", (preference_id,)).fetchone()["preference_value"] == "Rot"
    assert conn.execute("SELECT task_value FROM task_memory WHERE memory_id = ?", (task_id,)).fetchone()["task_value"] == "Dashboard pruefen"
    assert conn.execute("SELECT path FROM file_memory WHERE memory_id = ?", (file_id,)).fetchone()["path"] == "/tmp/redclaw.txt"


def test_memory_grouped_and_stats(tmp_path):
    db = tmp_path / "redclaw.db"
    init_db(db)
    repo = MemoryRepository(connect(db))
    repo.save("conversation", "1:user:web", "user@web: Hallo", source="web")
    repo.save("facts", "name", "Redcrafter", source="test")
    repo.save("files", "written:/tmp/a.txt", "Erstellte Datei: /tmp/a.txt", source="test")

    groups = repo.grouped()
    stats = repo.stats()

    assert len(groups["conversation"]) == 1
    assert len(groups["facts"]) == 1
    assert len(groups["files"]) == 1
    assert stats["total"] == 3
