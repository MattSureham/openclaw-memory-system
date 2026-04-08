"""
miner.py — Mining memories from OpenClaw files
===============================================

Mines existing OpenClaw memory files (MEMORY.md, memory/YYYY-MM-DD.md)
into the palace structure.

OpenClaw memory file format:
    # MEMORY.md - Long-term Memory
    ## About Matt
    - **Name:** Matthew "Matt"
    ...
"""

from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Iterator
from dataclasses import dataclass

from .palace import Palace, Room


@dataclass
class MiningResult:
    """Result of a mining operation."""

    files_processed: int
    memories_created: int
    wings_created: list[str]
    errors: list[str]


class OpenClawMiner:
    """
    Mines memories from OpenClaw's existing memory files:
    - ~/.openclaw/workspace/MEMORY.md
    - ~/.openclaw/workspace/memory/YYYY-MM-DD.md

    Parses the markdown structure and creates palace rooms.
    """

    KNOWN_WINGS = {
        "about": "Matt",
        "matt": "Matt",
        "about-me": "Matt",
        "me": "Matilda",
        "matilda": "Matilda",
        "openclaw": "OpenClaw",
        "projects": None,  # dynamic - use project name
        "tasks": None,
        "incomplete-tasks": None,
    }

    SECTION_TO_HALL = {
        "about": "context",
        "projects": "status",
        "active-projects": "status",
        "current-model": "facts",
        "github-token": "facts",
        "key-lessons": "facts",
        "incomplete-tasks": "problems",
        "pending-tasks": "problems",
        "lessons": "facts",
    }

    def __init__(self, palace: Optional[Palace] = None):
        self.palace = palace or Palace()

    def mine_file(
        self, path: Path, wing_hint: Optional[str] = None, tag: Optional[str] = None
    ) -> MiningResult:
        """Mine a single OpenClaw memory file into the palace."""
        result = MiningResult(
            files_processed=0, memories_created=0, wings_created=[], errors=[]
        )

        if not path.exists():
            result.errors.append(f"File not found: {path}")
            return result

        result.files_processed = 1
        content = path.read_text()

        # Determine the wing
        wing = wing_hint or self._detect_wing(content, path)

        # Parse sections
        sections = self._parse_sections(content)

        for section_name, section_content in sections.items():
            hall = self._section_to_hall(section_name, wing)

            if hall is None:
                continue

            room_name = self._make_room_name(section_name, section_content)

            # Store in palace
            self.palace.save_memory(wing, hall, room_name, section_content.strip())

            if wing not in result.wings_created:
                result.wings_created.append(wing)

            result.memories_created += 1

        return result

    def mine_workspace(
        self, workspace_path: Path, tag: Optional[str] = None
    ) -> MiningResult:
        """Mine all OpenClaw memory files from a workspace."""
        result = MiningResult(
            files_processed=0, memories_created=0, wings_created=[], errors=[]
        )

        memory_md = workspace_path / "MEMORY.md"
        if memory_md.exists():
            r = self.mine_file(memory_md, wing_hint="Matt", tag=tag)
            result.files_processed += r.files_processed
            result.memories_created += r.memories_created
            result.wings_created.extend(r.wings_created)
            result.errors.extend(r.errors)

        memory_dir = workspace_path / "memory"
        if memory_dir.exists():
            for md_file in sorted(memory_dir.iterdir()):
                if md_file.suffix == ".md" and md_file.stem.startswith(
                    "20"
                ):  # YYYY-MM-DD pattern
                    date_tag = md_file.stem  # e.g. "2026-04-01"
                    r = self.mine_file(md_file, wing_hint="Matt", tag=date_tag)
                    result.files_processed += r.files_processed
                    result.memories_created += r.memories_created
                    result.wings_created.extend(r.wings_created)
                    result.errors.extend(r.errors)

        return result

    def mine_all(self) -> MiningResult:
        """Mine from all standard OpenClaw locations."""
        paths_to_try = [
            Path.home() / ".openclaw" / "workspace",
            Path.home() / ".openclaw-workspace",
            Path.home() / "openclaw-workspace",
        ]

        result = MiningResult(
            files_processed=0, memories_created=0, wings_created=[], errors=[]
        )

        for workspace_path in paths_to_try:
            if workspace_path.exists():
                r = self.mine_workspace(workspace_path)
                result.files_processed += r.files_processed
                result.memories_created += r.memories_created
                result.wings_created.extend(r.wings_created)
                result.errors.extend(r.errors)

        return result

    def _detect_wing(self, content: str, path: Path) -> str:
        """Detect which wing a file belongs to based on content."""
        # Check for known wing markers
        for marker, wing in self.KNOWN_WINGS.items():
            if f"# {marker}" in content.lower() or f"## {marker}" in content.lower():
                if wing:
                    return wing

        # Default based on path
        if "memory" in str(path):
            return "Matt"

        return "OpenClaw"

    def _parse_sections(self, content: str) -> dict[str, str]:
        """Parse a markdown file into sections."""
        sections = {}

        # Split on ## headings (H2)
        parts = re.split(r"(?m)^## \s*", content)
        # parts[0] is before the first ##, typically the title

        for part in parts[1:]:  # Skip the first empty part
            lines = part.split("\n")
            title = lines[0].strip()
            body = "\n".join(lines[1:]).strip()

            if title:
                sections[title.lower().replace(" ", "-")] = body

        return sections

    def _section_to_hall(self, section_name: str, wing: str) -> Optional[str]:
        """Map a section name to a hall type."""
        # Direct mapping
        if section_name in self.SECTION_TO_HALL:
            return self.SECTION_TO_HALL[section_name]

        # Fuzzy matching
        section_lower = section_name.lower()
        for key, hall in self.SECTION_TO_HALL.items():
            if key in section_lower or section_lower in key:
                return hall

        # Default based on wing
        if wing == "Matt":
            return "context"
        elif wing == "Matilda":
            return "context"
        else:
            return "status"

    def _make_room_name(self, section_name: str, content: str) -> str:
        """Create a room name from a section."""
        # Clean up the section name
        name = re.sub(r"[^\w\s-]", "", section_name)
        name = re.sub(r"[_\s]+", "-", name)
        name = name.strip("-")

        # If the content starts with a bullet list, use the first bullet as hint
        bullet_match = re.search(r"[-*]\s+\*\*([^*]+)\*\*:", content)
        if bullet_match:
            hint = bullet_match.group(1).lower().replace(" ", "-")
            name = f"{name}-{hint}"

        return name
