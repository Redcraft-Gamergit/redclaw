from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass
class MemoryItem:
    id: int
    category: str
    key: str
    value: str
    source: str | None
    confidence: float
    created_at: str


class MemoryRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save(self, category: str, key: str, value: str, source: str | None = None, confidence: float = 1.0) -> int:
        clean_category = category.strip().lower()
        clean_key = key.strip().lower()
        clean_value = value.strip()
        cur = self.conn.execute(
            """
            INSERT INTO memory(category, key, value, source, confidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            (clean_category, clean_key, clean_value, source, confidence),
        )
        memory_id = int(cur.lastrowid)
        self._save_structured(memory_id, clean_category, clean_key, clean_value, source, confidence)
        self.conn.commit()
        return memory_id

    def get(self, category: str, key: str) -> MemoryItem | None:
        row = self.conn.execute(
            """
            SELECT * FROM memory
            WHERE category = ? AND key = ? AND deleted_at IS NULL
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (category.strip().lower(), key.strip().lower()),
        ).fetchone()
        return self._row_to_item(row) if row else None

    def search(self, query: str, category: str | None = None, limit: int = 20) -> list[MemoryItem]:
        pattern = f"%{query.strip().lower()}%"
        params: list[Any] = [pattern, pattern]
        category_clause = ""
        if category:
            category_clause = "AND category = ?"
            params.append(category.strip().lower())
        params.append(limit)
        rows = self.conn.execute(
            f"""
            SELECT * FROM memory
            WHERE deleted_at IS NULL
              AND (LOWER(key) LIKE ? OR LOWER(value) LIKE ?)
              {category_clause}
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [self._row_to_item(row) for row in rows]

    def list_by_category(self, category: str, limit: int = 100) -> list[MemoryItem]:
        rows = self.conn.execute(
            """
            SELECT * FROM memory
            WHERE category = ? AND deleted_at IS NULL
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (category.strip().lower(), limit),
        ).fetchall()
        return [self._row_to_item(row) for row in rows]

    def recent_conversation(self, limit: int = 12) -> list[MemoryItem]:
        rows = self.conn.execute(
            """
            SELECT * FROM memory
            WHERE category = 'conversation' AND deleted_at IS NULL
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_item(row) for row in reversed(rows)]

    def all(self, limit: int = 200) -> list[MemoryItem]:
        rows = self.conn.execute(
            """
            SELECT * FROM memory
            WHERE deleted_at IS NULL
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_item(row) for row in rows]

    def grouped(self, limit_per_group: int = 60) -> dict[str, list[MemoryItem]]:
        groups = {
            "conversation": self.list_by_category("conversation", limit_per_group),
            "facts": self.list_by_category("facts", limit_per_group),
            "preferences": self.list_by_category("preferences", limit_per_group),
            "tasks": self.list_by_category("tasks", limit_per_group),
            "files": self.list_by_category("files", limit_per_group),
            "projects": self.list_by_category("projects", limit_per_group),
        }
        other_rows = self.conn.execute(
            """
            SELECT * FROM memory
            WHERE deleted_at IS NULL
              AND category NOT IN ('conversation', 'facts', 'preferences', 'tasks', 'files', 'projects')
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit_per_group,),
        ).fetchall()
        groups["other"] = [self._row_to_item(row) for row in other_rows]
        return groups

    def stats(self) -> dict[str, int]:
        rows = self.conn.execute(
            """
            SELECT category, COUNT(*) AS count
            FROM memory
            WHERE deleted_at IS NULL
            GROUP BY category
            """
        ).fetchall()
        stats = {str(row["category"]): int(row["count"]) for row in rows}
        stats["total"] = sum(stats.values())
        return stats

    def delete(self, memory_id: int) -> bool:
        cur = self.conn.execute("UPDATE memory SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?", (memory_id,))
        for table in ("conversation_memory", "fact_memory", "preference_memory", "task_memory", "file_memory"):
            self.conn.execute(f"UPDATE {table} SET deleted_at = CURRENT_TIMESTAMP WHERE memory_id = ?", (memory_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def log(self, level: str, kind: str, message: str, meta: dict[str, Any] | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO logs(level, kind, message, meta) VALUES (?, ?, ?, ?)",
            (level, kind, message, json.dumps(meta or {}, ensure_ascii=False)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def logs(self, kind: str | None = None, limit: int = 200) -> list[sqlite3.Row]:
        if kind:
            return self.conn.execute(
                "SELECT * FROM logs WHERE kind = ? ORDER BY created_at DESC LIMIT ?",
                (kind, limit),
            ).fetchall()
        return self.conn.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()

    def cleanup_logs(self, retention_days: int) -> None:
        self.conn.execute(
            """
            DELETE FROM logs
            WHERE kind != 'security'
              AND created_at < datetime('now', ?)
            """,
            (f"-{retention_days} days",),
        )
        self.conn.commit()

    def _save_structured(
        self,
        memory_id: int,
        category: str,
        key: str,
        value: str,
        source: str | None,
        confidence: float,
    ) -> None:
        if category == "conversation":
            role, message = self._parse_conversation(value)
            self.conn.execute(
                """
                INSERT INTO conversation_memory(memory_id, role, source, message)
                VALUES (?, ?, ?, ?)
                """,
                (memory_id, role, source, message),
            )
            return
        if category == "facts":
            self.conn.execute(
                """
                INSERT INTO fact_memory(memory_id, fact_key, fact_value, source, confidence)
                VALUES (?, ?, ?, ?, ?)
                """,
                (memory_id, key, value, source, confidence),
            )
            return
        if category == "preferences":
            self.conn.execute(
                """
                INSERT INTO preference_memory(memory_id, preference_key, preference_value, source, confidence)
                VALUES (?, ?, ?, ?, ?)
                """,
                (memory_id, key, value, source, confidence),
            )
            return
        if category == "tasks":
            self.conn.execute(
                """
                INSERT INTO task_memory(memory_id, task_key, task_value, source, confidence)
                VALUES (?, ?, ?, ?, ?)
                """,
                (memory_id, key, value, source, confidence),
            )
            return
        if category == "files":
            action, path = self._parse_file_memory(key, value)
            self.conn.execute(
                """
                INSERT INTO file_memory(memory_id, path, action, note, source, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (memory_id, path, action, value, source, confidence),
            )

    @staticmethod
    def _parse_conversation(value: str) -> tuple[str, str]:
        match = re.match(r"^(user|assistant)@[^:]+:\s*(.*)$", value, flags=re.IGNORECASE)
        if not match:
            return "unknown", value
        return match.group(1).lower(), match.group(2).strip()

    @staticmethod
    def _parse_file_memory(key: str, value: str) -> tuple[str, str]:
        if ":" in key:
            action, path = key.split(":", 1)
            return action.strip() or "noted", path.strip() or value
        path_match = re.search(r"(/[^,\s]+|[A-Za-z]:\\[^\n]+)$", value)
        return "noted", path_match.group(1).strip() if path_match else value

    def _row_to_item(self, row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            id=int(row["id"]),
            category=str(row["category"]),
            key=str(row["key"]),
            value=str(row["value"]),
            source=row["source"],
            confidence=float(row["confidence"]),
            created_at=str(row["created_at"]),
        )
