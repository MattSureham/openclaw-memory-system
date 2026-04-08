"""
storage.py — Persistence layer for OpenClaw Memory System
==========================================================

Supports:
- File-based storage (MEMORY.md, memory/YYYY-MM-DD.md)
- SQLite for structured data
- ChromaDB for semantic search (via Layer3)
"""

from __future__ import annotations

import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Iterator
from dataclasses import dataclass

DEFAULT_DATA_PATH = Path.home() / ".openclaw-memory" / "data"


@dataclass
class MemoryEntry:
    """A single memory entry."""

    id: int
    wing: str
    hall: str
    room: str
    content: str
    created_at: datetime
    updated_at: datetime
    tags: list[str]


class Storage:
    """
    SQLite-backed storage for memory metadata and full-text content.
    The palace itself uses file-based storage (.md files in wing/hall/room structure).
    This class manages the SQLite index for fast querying.
    """

    def __init__(self, data_path: Path = DEFAULT_DATA_PATH):
        self.data_path = data_path
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.db_path = data_path / "memory.db"
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wing TEXT NOT NULL,
                hall TEXT NOT NULL,
                room TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_wing ON memory_entries(wing)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_wing_hall ON memory_entries(wing, hall)
        """)
        conn.commit()

    def insert(
        self,
        wing: str,
        hall: str,
        room: str,
        content: str,
        tags: Optional[list[str]] = None,
    ) -> int:
        """Insert a new memory entry. Returns the row ID."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        tags_json = json.dumps(tags or [])
        cursor = conn.execute(
            """
            INSERT INTO memory_entries (wing, hall, room, content, created_at, updated_at, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (wing, hall, room, content, now, now, tags_json),
        )
        conn.commit()
        return cursor.lastrowid

    def update(self, id: int, content: str, tags: Optional[list[str]] = None) -> bool:
        """Update an existing entry."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        tags_json = json.dumps(tags or [])
        cursor = conn.execute(
            """
            UPDATE memory_entries SET content = ?, updated_at = ?, tags = ?
            WHERE id = ?
            """,
            (content, now, tags_json, id),
        )
        conn.commit()
        return cursor.rowcount > 0

    def delete(self, id: int) -> bool:
        """Delete an entry by ID."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM memory_entries WHERE id = ?", (id,))
        conn.commit()
        return cursor.rowcount > 0

    def get(self, id: int) -> Optional[MemoryEntry]:
        """Get a single entry by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM memory_entries WHERE id = ?", (id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_entry(row)

    def search_text(self, query: str, limit: int = 20) -> list[MemoryEntry]:
        """Full-text search on content."""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT * FROM memory_entries
            WHERE content LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (f"%{query}%", limit),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def by_wing(self, wing: str) -> list[MemoryEntry]:
        """Get all entries for a wing."""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT * FROM memory_entries WHERE wing = ? ORDER BY updated_at DESC
            """,
            (wing,),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def by_room(self, wing: str, hall: str, room: str) -> Optional[MemoryEntry]:
        """Get a specific room entry."""
        conn = self._get_conn()
        row = conn.execute(
            """
            SELECT * FROM memory_entries
            WHERE wing = ? AND hall = ? AND room = ?
            ORDER BY updated_at DESC LIMIT 1
            """,
            (wing, hall, room),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_entry(row)

    def all(self, limit: int = 100) -> list[MemoryEntry]:
        """Get all entries, most recent first."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM memory_entries ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def count(self) -> int:
        """Total entry count."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) FROM memory_entries").fetchone()
        return row[0] if row else 0

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            wing=row["wing"],
            hall=row["hall"],
            room=row["room"],
            content=row["content"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            tags=json.loads(row["tags"]),
        )

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
