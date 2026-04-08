"""
palace.py — Palace Structure for OpenClaw Memory System
==========================================================

Manages the hierarchical memory palace:
    Wing → Hall → Room

Example:
    Wing: "Matt" (a person)
      Hall: "preferences"
        Room: "likes-brief-responses"
        Room: "timezone-asia-shanghai"
    Wing: "ClaudeRE" (a project)
      Hall: "decisions"
        Room: "chose-postgres-over-mysql"
      Hall: "status"
        Room: "module-3-complete"
"""

from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Iterator

DEFAULT_PALACE_PATH = Path.home() / ".openclaw-memory" / "palace"


# ---------------------------------------------------------------------------
# Hall Types (categories within a wing)
# ---------------------------------------------------------------------------

DEFAULT_HALLS = [
    "decisions",     # Choices made, why, alternatives considered
    "preferences",   # Likes, dislikes, habits, communication style
    "milestones",    # Achievements, completed work, breakthroughs
    "problems",      # Issues encountered, bugs, solutions found
    "context",       # Background info, project history, relationships
    "facts",         # Hard facts, data, specifications
]


@dataclass
class Room:
    """A single memory room."""

    wing: str
    hall: str
    name: str
    path: Path

    def read(self) -> str:
        if self.path.exists():
            return self.path.read_text()
        return ""

    def write(self, content: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(content)

    def delete(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def touch(self) -> None:
        """Update mtime without changing content."""
        if self.path.exists():
            self.path.touch()

    @property
    def mtime(self) -> Optional[datetime]:
        if self.path.exists():
            return datetime.fromtimestamp(self.path.stat().st_mtime)
        return None

    @property
    def ctime(self) -> Optional[datetime]:
        if self.path.exists():
            return datetime.fromtimestamp(self.path.stat().st_ctime)
        return None


@dataclass
class Hall:
    """A category within a wing."""

    wing: str
    name: str
    path: Path

    def rooms(self) -> Iterator[Room]:
        if not self.path.exists():
            return
        for room_file in self.path.iterdir():
            if room_file.suffix == ".md":
                yield Room(
                    wing=self.wing,
                    hall=self.name,
                    name=room_file.stem,
                    path=room_file,
                )

    def room(self, room_name: str) -> Room:
        return Room(
            wing=self.wing,
            hall=self.name,
            name=room_name,
            path=self.path / f"{room_name}.md",
        )

    def create_room(self, room_name: str, content: str = "") -> Room:
        room = self.room(room_name)
        room.write(content)
        return room

    def delete(self) -> None:
        if self.path.exists():
            for room_file in self.path.iterdir():
                if room_file.suffix == ".md":
                    room_file.unlink()
            self.path.rmdir()

    @property
    def room_count(self) -> int:
        if not self.path.exists():
            return 0
        return sum(1 for f in self.path.iterdir() if f.suffix == ".md")


@dataclass
class Wing:
    """A person or project."""

    name: str
    path: Path

    def halls(self) -> Iterator[Hall]:
        if not self.path.exists():
            return
        for hall_path in self.path.iterdir():
            if hall_path.is_dir():
                yield Hall(wing=self.name, name=hall_path.name, path=hall_path)

    def hall(self, hall_name: str) -> Hall:
        return Hall(
            wing=self.name,
            name=hall_name,
            path=self.path / hall_name,
        )

    def create_hall(self, hall_name: str) -> Hall:
        hall = self.hall(hall_name)
        hall.path.mkdir(parents=True, exist_ok=True)
        return hall

    def delete(self) -> None:
        if self.path.exists():
            for hall_path in self.path.iterdir():
                if hall_path.is_dir():
                    for room_file in hall_path.iterdir():
                        if room_file.suffix == ".md":
                            room_file.unlink()
                    hall_path.rmdir()
            self.path.rmdir()

    def all_rooms(self) -> list[Room]:
        rooms = []
        for hall in self.halls():
            rooms.extend(hall.rooms())
        return rooms

    @property
    def hall_count(self) -> int:
        if not self.path.exists():
            return 0
        return sum(1 for d in self.path.iterdir() if d.is_dir())

    @property
    def room_count(self) -> int:
        return sum(hall.room_count for hall in self.halls())


@dataclass
class Palace:
    """
    The full memory palace.

    palace/
      Matt/
        preferences/
          likes-brief-responses.md
          timezone-asia-shanghai.md
        decisions/
          uses-openclaw.md
        milestones/
          first-session.md
        problems/
          memory-wiped-incident.md
      ClaudeRE/
        decisions/
          chosen-postgres.md
        status/
          module-3-complete.md
    """

    root: Path = field(default=DEFAULT_PALACE_PATH)

    def __post_init__(self):
        self._ensure_root()

    def _ensure_root(self) -> None:
        if not self.root.exists():
            self.root.mkdir(parents=True, exist_ok=True)

    def wings(self) -> Iterator[Wing]:
        for wing_path in self.root.iterdir():
            if wing_path.is_dir():
                yield Wing(name=wing_path.name, path=wing_path)

    def wing(self, wing_name: str) -> Wing:
        """Get or create a wing by name."""
        safe_name = self._safe_name(wing_name)
        return Wing(name=safe_name, path=self.root / safe_name)

    def has_wing(self, wing_name: str) -> bool:
        return (self.root / wing_name).exists()

    def create_wing(self, wing_name: str, halls: Optional[list[str]] = None) -> Wing:
        """Create a wing with default halls."""
        wing = self.wing(wing_name)
        wing.path.mkdir(parents=True, exist_ok=True)
        for hall_name in (halls or DEFAULT_HALLS):
            wing.create_hall(hall_name)
        return wing

    def delete_wing(self, wing_name: str) -> None:
        wing = self.wing(wing_name)
        wing.delete()

    def all_rooms(self) -> list[Room]:
        """Get all rooms in the palace, sorted by mtime (newest first)."""
        rooms = []
        for wing in self.wings():
            rooms.extend(wing.all_rooms())
        rooms.sort(key=lambda r: r.mtime or datetime.min, reverse=True)
        return rooms

    def find_room(self, wing_name: str, hall_name: str, room_name: str) -> Optional[Room]:
        """Find a specific room."""
        room_path = self.root / wing_name / hall_name / f"{room_name}.md"
        if room_path.exists():
            return Room(wing=wing_name, hall=hall_name, name=room_name, path=room_path)
        return None

    def get_or_create_room(
        self, wing_name: str, hall_name: str, room_name: str, content: str = ""
    ) -> Room:
        """Get a room, creating the wing/hall structure if needed."""
        wing = self.wing(wing_name)
        wing.path.mkdir(parents=True, exist_ok=True)
        hall = wing.create_hall(hall_name)
        return hall.create_room(room_name, content)

    def save_memory(
        self, wing_name: str, hall_name: str, room_name: str, content: str
    ) -> Room:
        """
        Save a memory to the palace.
        Creates wing/hall/room structure if it doesn't exist.
        """
        room = self.get_or_create_room(wing_name, hall_name, room_name)
        room.write(content)
        return room

    def delete_memory(self, wing_name: str, hall_name: str, room_name: str) -> bool:
        """Delete a memory room."""
        room = self.find_room(wing_name, hall_name, room_name)
        if room:
            room.delete()
            return True
        return False

    def list_wings(self) -> list[str]:
        return [w.name for w in self.wings()]

    def list_halls(self, wing_name: str) -> list[str]:
        wing = self.wing(wing_name)
        return [h.name for h in wing.halls()]

    def list_rooms(self, wing_name: str, hall_name: str) -> list[str]:
        wing = self.wing(wing_name)
        hall = wing.hall(hall_name)
        return [r.name for r in hall.rooms()]

    def stats(self) -> dict:
        """Palace statistics."""
        wings = list(self.wings())
        total_rooms = sum(w.room_count for w in wings)
        halls_total = sum(w.hall_count for w in wings)
        return {
            "wing_count": len(wings),
            "hall_count": halls_total,
            "room_count": total_rooms,
            "wings": [w.name for w in wings],
        }

    @staticmethod
    def _safe_name(name: str) -> str:
        """Make a name safe for use as a directory/file name."""
        name = name.lower().strip()
        name = re.sub(r"[^\w\s-]", "", name)
        name = re.sub(r"[_\s]+", "-", name)
        return name
