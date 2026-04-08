"""
layers.py — 4-Layer Memory Stack for OpenClaw Memory System
=============================================================

Load only what you need, when you need it.

    Layer 0: Identity       (~100 tokens)   — Always loaded. "Who am I?"
    Layer 1: Essential Story (~500 tokens)  — Always loaded. Top moments from the palace.
    Layer 2: On-Demand      (~500 each)      — Loaded when a topic/wing comes up.
    Layer 3: Deep Search    (unlimited)      — Full semantic search via ChromaDB.

Wake-up cost: ~600 tokens (L0+L1). Leaves 95%+ of context free.

Reads from the palace store (~/.openclaw-memory/palace/) and
~/.openclaw-memory/identity.txt.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

DEFAULT_MEMORY_ROOT = Path.home() / ".openclaw-memory"
DEFAULT_IDENTITY_PATH = DEFAULT_MEMORY_ROOT / "identity.txt"
DEFAULT_PALACE_PATH = DEFAULT_MEMORY_ROOT / "palace"
DEFAULT_DB_PATH = DEFAULT_MEMORY_ROOT / "chroma_db"


# ---------------------------------------------------------------------------
# Layer 0 — Identity
# ---------------------------------------------------------------------------


@dataclass
class Layer0:
    """
    ~100 tokens. Always loaded.
    Reads from ~/.openclaw-memory/identity.txt — a plain-text file.

    Example identity.txt:
        I am Matilda, a personal AI assistant for Matt.
        Traits: trustworthy, helpful, sharp.
        People: Matt (creator).
        Projects: ClaudeRE, openclaw-memory-system.
    """

    identity_path: Path = field(default=DEFAULT_IDENTITY_PATH)

    def __post_init__(self):
        self._text: Optional[str] = None

    def render(self) -> str:
        if self._text is not None:
            return self._text

        if self.identity_path.exists():
            self._text = self.identity_path.read_text().strip()
        else:
            self._text = self._default_identity()

        return self._text

    def _default_identity(self) -> str:
        return (
            "I am an AI assistant.\n"
            "No identity has been set yet.\n"
            "Run: openclaw-memory init"
        )

    def save(self, text: str) -> None:
        self.identity_path.parent.mkdir(parents=True, exist_ok=True)
        self.identity_path.write_text(text)
        self._text = text

    def token_count(self) -> int:
        """Approximate token count (4 chars per token)."""
        return len(self.render()) // 4


# ---------------------------------------------------------------------------
# Layer 1 — Essential Story
# ---------------------------------------------------------------------------


@dataclass
class Layer1:
    """
    ~500 tokens. Always loaded.
    Contains the top N most important memories across all wings.
    Computed from room importance scores.

    Stored in: ~/.openclaw-memory/essential.md
    """

    palace_path: Path = field(default=DEFAULT_PALACE_PATH)
    essential_path: Path = field(default=DEFAULT_MEMORY_ROOT / "essential.md")
    max_rooms: int = 20  # ~500 tokens worth of rooms

    def render(self) -> str:
        if not self.essential_path.exists():
            return self._build_essential()

        return self.essential_path.read_text().strip()

    def _build_essential(self) -> str:
        """Rebuild essential story from palace rooms."""
        if not self.palace_path.exists():
            return ""

        rooms = []
        for wing_path in self.palace_path.iterdir():
            if not wing_path.is_dir():
                continue
            for hall_path in wing_path.iterdir():
                if not hall_path.is_dir():
                    continue
                for room_file in hall_path.iterdir():
                    if room_file.suffix == ".md":
                        rooms.append(room_file)

        # Sort by mtime (most recent first), take top N
        rooms.sort(key=lambda r: r.stat().st_mtime, reverse=True)
        rooms = rooms[: self.max_rooms]

        lines = ["# Essential Story\n"]
        for room_file in rooms:
            lines.append(f"\n## {room_file.stem}\n")
            lines.append(room_file.read_text().strip()[:500])  # truncate per room

        return "\n".join(lines)

    def rebuild(self) -> None:
        content = self._build_essential()
        self.essential_path.parent.mkdir(parents=True, exist_ok=True)
        self.essential_path.write_text(content)

    def token_count(self) -> int:
        return len(self.render()) // 4


# ---------------------------------------------------------------------------
# Layer 2 — On-Demand
# ---------------------------------------------------------------------------


@dataclass
class Layer2:
    """
    ~500 tokens each. Loaded when a wing or hall is referenced.
    Returns all rooms in a given wing (or hall).

    Example: "tell me about ClaudeRE" → loads all rooms in the ClaudeRE wing.
    """

    palace_path: Path = field(default=DEFAULT_PALACE_PATH)

    def render_wing(self, wing_name: str) -> str:
        wing_path = self.palace_path / wing_name
        if not wing_path.exists():
            return f"No wing found: {wing_name}"

        lines = [f"# Wing: {wing_name}\n"]
        for hall_path in sorted(wing_path.iterdir()):
            if not hall_path.is_dir():
                continue
            lines.append(f"\n## Hall: {hall_path.name}\n")
            for room_file in sorted(hall_path.iterdir()):
                if room_file.suffix == ".md":
                    lines.append(f"\n### {room_file.stem}\n")
                    lines.append(room_file.read_text().strip()[:500])

        return "\n".join(lines)

    def render_hall(self, wing_name: str, hall_name: str) -> str:
        hall_path = self.palace_path / wing_name / hall_name
        if not hall_path.exists():
            return f"No hall found: {wing_name}/{hall_name}"

        lines = [f"# Hall: {wing_name}/{hall_name}\n"]
        for room_file in sorted(hall_path.iterdir()):
            if room_file.suffix == ".md":
                lines.append(f"\n## {room_file.stem}\n")
                lines.append(room_file.read_text().strip())

        return "\n".join(lines)

    def render_room(self, wing_name: str, hall_name: str, room_name: str) -> str:
        room_path = self.palace_path / wing_name / hall_name / f"{room_name}.md"
        if not room_path.exists():
            return f"No room found: {wing_name}/{hall_name}/{room_name}"

        return room_path.read_text()

    def list_wings(self) -> list[str]:
        if not self.palace_path.exists():
            return []
        return [p.name for p in self.palace_path.iterdir() if p.is_dir()]

    def list_halls(self, wing_name: str) -> list[str]:
        wing_path = self.palace_path / wing_name
        if not wing_path.exists():
            return []
        return [p.name for p in wing_path.iterdir() if p.is_dir()]

    def list_rooms(self, wing_name: str, hall_name: str) -> list[str]:
        hall_path = self.palace_path / wing_name / hall_name
        if not hall_path.exists():
            return []
        return [p.stem for p in hall_path.iterdir() if p.suffix == ".md"]


# ---------------------------------------------------------------------------
# Layer 3 — Deep Search
# ---------------------------------------------------------------------------


@dataclass
class Layer3:
    """
    Unlimited. Full semantic search via ChromaDB.
    Use when keyword/structure search isn't enough.
    """

    db_path: Path = field(default=DEFAULT_DB_PATH)
    collection_name: str = "openclaw_memory"

    def __post_init__(self):
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection: Optional[chromadb.Collection] = None

    def _get_collection(self) -> chromadb.Collection:
        if self._collection is not None:
            return self._collection

        self._client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "OpenClaw Memory System collection"},
        )
        return self._collection

    def add_memory(
        self,
        text: str,
        wing: str,
        hall: str,
        room: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Add a memory to the deep search index."""
        import uuid

        collection = self._get_collection()
        doc_id = str(uuid.uuid4())

        collection.add(
            documents=[text],
            ids=[doc_id],
            metadatas=[
                metadata
                or {
                    "wing": wing,
                    "hall": hall,
                    "room": room,
                }
            ],
        )
        return doc_id

    def search(
        self, query: str, n_results: int = 5, wing_filter: Optional[str] = None
    ) -> list[dict]:
        """Semantic search across all memories."""
        collection = self._get_collection()

        where_clause: Optional[dict] = None
        if wing_filter:
            where_clause = {"wing": wing_filter}

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause,
        )

        memories = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                memories.append(
                    {
                        "text": doc,
                        "id": results["ids"][0][i],
                        "distance": results["distances"][0][i]
                        if results["distances"]
                        else None,
                        "metadata": results["metadatas"][0][i]
                        if results["metadatas"]
                        else {},
                    }
                )
        return memories

    def delete(self, doc_id: str) -> None:
        """Delete a memory by ID."""
        collection = self._get_collection()
        collection.delete(ids=[doc_id])

    def count(self) -> int:
        """Total number of indexed memories."""
        try:
            return len(self._get_collection().get()["ids"])
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# Memory Stack — All Layers Together
# ---------------------------------------------------------------------------


@dataclass
class MemoryStack:
    """
    Unified 4-layer memory stack.
    Use wake_up() to get L0+L1 context.
    Use load_wing/hall/room() for on-demand loading.
    Use search() for deep search.
    """

    root: Path = field(default=DEFAULT_MEMORY_ROOT)

    def __post_init__(self):
        self.l0 = Layer0()
        self.l1 = Layer1()
        self.l2 = Layer2()
        self.l3 = Layer3()

    def wake_up(self) -> str:
        """
        Render L0 (Identity) + L1 (Essential Story).
        ~600 tokens total. Put this at the top of your system prompt.
        """
        return f"{self.l0.render()}\n\n---\n\n{self.l1.render()}"

    def load_wing(self, wing_name: str) -> str:
        return self.l2.render_wing(wing_name)

    def load_hall(self, wing_name: str, hall_name: str) -> str:
        return self.l2.render_hall(wing_name, hall_name)

    def load_room(self, wing_name: str, hall_name: str, room_name: str) -> str:
        return self.l2.render_room(wing_name, hall_name, room_name)

    def list_wings(self) -> list[str]:
        return self.l2.list_wings()

    def list_halls(self, wing_name: str) -> list[str]:
        return self.l2.list_halls(wing_name)

    def list_rooms(self, wing_name: str, hall_name: str) -> list[str]:
        return self.l2.list_rooms(wing_name, hall_name)

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        return self.l3.search(query, n_results)

    def add_memory(
        self,
        text: str,
        wing: str,
        hall: str,
        room: str,
        metadata: Optional[dict] = None,
    ) -> str:
        return self.l3.add_memory(text, wing, hall, room, metadata)

    def stats(self) -> dict:
        """Return memory system statistics."""
        return {
            "l0_tokens": self.l0.token_count(),
            "l1_tokens": self.l1.token_count(),
            "wings": len(self.l2.list_wings()),
            "l3_count": self.l3.count(),
            "root": str(self.root),
        }
