from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_memory_category ON memory(category);
CREATE INDEX IF NOT EXISTS idx_memory_key ON memory(key);

CREATE TABLE IF NOT EXISTS conversation_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER,
    role TEXT NOT NULL,
    source TEXT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY(memory_id) REFERENCES memory(id)
);

CREATE INDEX IF NOT EXISTS idx_conversation_memory_source_created ON conversation_memory(source, created_at);

CREATE TABLE IF NOT EXISTS fact_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER,
    fact_key TEXT NOT NULL,
    fact_value TEXT NOT NULL,
    source TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY(memory_id) REFERENCES memory(id)
);

CREATE INDEX IF NOT EXISTS idx_fact_memory_key ON fact_memory(fact_key);

CREATE TABLE IF NOT EXISTS preference_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER,
    preference_key TEXT NOT NULL,
    preference_value TEXT NOT NULL,
    source TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY(memory_id) REFERENCES memory(id)
);

CREATE INDEX IF NOT EXISTS idx_preference_memory_key ON preference_memory(preference_key);

CREATE TABLE IF NOT EXISTS task_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER,
    task_key TEXT NOT NULL,
    task_value TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    source TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY(memory_id) REFERENCES memory(id)
);

CREATE INDEX IF NOT EXISTS idx_task_memory_status ON task_memory(status);

CREATE TABLE IF NOT EXISTS file_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER,
    path TEXT NOT NULL,
    action TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    source TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY(memory_id) REFERENCES memory(id)
);

CREATE INDEX IF NOT EXISTS idx_file_memory_path ON file_memory(path);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    meta TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_logs_kind_created ON logs(kind, created_at);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    due_at TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'discord',
    done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
