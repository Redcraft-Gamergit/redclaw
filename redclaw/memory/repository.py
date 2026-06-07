from __future__ import annotations

import json
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
        cur = self.conn.execute(
            """
            INSERT INTO memory(category, key, value, source, confidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            (category.strip().lower(), key.strip().lower(), value.strip(), source, confidence),
        )
        self.conn.commit()
        return int(cur.lastrowid)

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

    def delete(self, memory_id: int) -> bool:
        cur = self.conn.execute("UPDATE memory SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?", (memory_id,))
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
