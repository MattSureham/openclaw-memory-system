"""
searcher.py — Search across OpenClaw memory
============================================

Provides search functionality across:
- Palace structure (file-based)
- SQLite index
- ChromaDB semantic search
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterator
from dataclasses import dataclass

from .palace import Palace
from .storage import Storage
from .layers import Layer3


@dataclass
class SearchResult:
    """A single search result."""

    text: str
    source: str  # "palace", "storage", "chroma"
    wing: Optional[str] = None
    hall: Optional[str] = None
    room: Optional[str] = None
    score: Optional[float] = None
    id: Optional[str] = None


class Searcher:
    """
    Unified search across all memory layers.

    Priority:
    1. Exact room match (palace structure)
    2. Keyword search (storage)
    3. Semantic search (ChromaDB Layer3)
    """

    def __init__(
        self,
        palace: Optional[Palace] = None,
        storage: Optional[Storage] = None,
        layer3: Optional[Layer3] = None,
    ):
        self.palace = palace or Palace()
        self.storage = storage or Storage()
        self.layer3 = layer3 or Layer3()

    def search(
        self, query: str, mode: str = "all", limit: int = 10
    ) -> list[SearchResult]:
        """
        Search memory.

        Modes:
        - "all" — search everywhere
        - "palace" — only palace structure
        - "semantic" — only ChromaDB semantic search
        - "text" — only keyword search in storage
        """
        if mode == "all":
            results = []
            results.extend(self._search_palace(query, limit))
            results.extend(self._search_text(query, limit))
            results.extend(self._search_semantic(query, limit))
            return self._deduplicate_and_rank(results, limit)

        elif mode == "palace":
            return self._search_palace(query, limit)

        elif mode == "semantic":
            return self._search_semantic(query, limit)

        elif mode == "text":
            return self._search_text(query, limit)

        return []

    def _search_palace(
        self, query: str, limit: int = 10
    ) -> list[SearchResult]:
        """Search palace rooms by name matching."""
        results = []
        query_lower = query.lower()

        for room in self.palace.all_rooms():
            room_name_lower = room.name.lower()
            if query_lower in room_name_lower:
                content = room.read()
                results.append(
                    SearchResult(
                        text=f"## {room.name}\n{content[:300]}",
                        source="palace",
                        wing=room.wing,
                        hall=room.hall,
                        room=room.name,
                        score=1.0 if query_lower == room_name_lower else 0.8,
                    )
                )
            elif query_lower in content.lower():
                results.append(
                    SearchResult(
                        text=f"## {room.name}\n{content[:300]}",
                        source="palace",
                        wing=room.wing,
                        hall=room.hall,
                        room=room.name,
                        score=0.6,
                    )
                )

        return results[:limit]

    def _search_text(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Full-text search via SQLite."""
        results = []
        for entry in self.storage.search_text(query, limit):
            results.append(
                SearchResult(
                    text=f"## {entry.room}\n{entry.content[:300]}",
                    source="storage",
                    wing=entry.wing,
                    hall=entry.hall,
                    room=entry.room,
                    score=0.7,
                    id=str(entry.id),
                )
            )
        return results

    def _search_semantic(
        self, query: str, limit: int = 10
    ) -> list[SearchResult]:
        """Semantic search via ChromaDB Layer3."""
        results = []
        for mem in self.layer3.search(query, n_results=limit):
            wing = mem.get("metadata", {}).get("wing", "")
            hall = mem.get("metadata", {}).get("hall", "")
            room = mem.get("metadata", {}).get("room", "")
            results.append(
                SearchResult(
                    text=mem["text"][:500],
                    source="chroma",
                    wing=wing,
                    hall=hall,
                    room=room,
                    score=1.0 - (mem.get("distance", 0.5) or 0.5),
                    id=mem.get("id"),
                )
            )
        return results

    def _deduplicate_and_rank(
        self, results: list[SearchResult], limit: int = 10
    ) -> list[SearchResult]:
        """Remove duplicates and sort by score."""
        seen = set()
        deduped = []
        for r in sorted(results, key=lambda x: x.score or 0, reverse=True):
            key = (r.wing, r.hall, r.room)
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        return deduped[:limit]

    def find_room(
        self, wing: str, hall: Optional[str] = None, room_name: Optional[str] = None
    ) -> list[SearchResult]:
        """Find rooms by wing/hall/room name with partial matching."""
        results = []

        if hall is None and room_name is None:
            # List all rooms in wing
            for h in self.palace.list_halls(wing):
                for r in self.palace.list_rooms(wing, h):
                    room = self.palace.find_room(wing, h, r)
                    if room:
                        results.append(
                            SearchResult(
                                text=room.read()[:300],
                                source="palace",
                                wing=wing,
                                hall=h,
                                room=r,
                            )
                        )
        elif room_name is None:
            # List all rooms in wing/hall
            for r in self.palace.list_rooms(wing, hall):
                room = self.palace.find_room(wing, hall, r)
                if room:
                    results.append(
                        SearchResult(
                            text=room.read()[:300],
                            source="palace",
                            wing=wing,
                            hall=hall,
                            room=r,
                        )
                    )
        else:
            # Specific room
            room = self.palace.find_room(wing, hall, room_name)
            if room:
                results.append(
                    SearchResult(
                        text=room.read(),
                        source="palace",
                        wing=wing,
                        hall=hall,
                        room=room_name,
                    )
                )

        return results
