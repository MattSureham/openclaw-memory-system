"""
mcp_server.py — MCP Tools Server for OpenClaw Memory System
============================================================

Provides MCP tools for AI agents to interact with the memory system.

Tools available:
- memory_wake_up          — Get L0 + L1 context (~600 tokens)
- memory_load_wing        — Load all rooms in a wing (L2)
- memory_load_hall        — Load all rooms in a hall (L2)
- memory_save             — Save a memory to the palace
- memory_search           — Semantic + keyword search
- memory_list_wings        — List all wings
- memory_list_halls       — List halls in a wing
- memory_list_rooms       — List rooms in a wing/hall
- memory_stats            — Get memory system stats
- memory_mine             — Mine from OpenClaw workspace files
- memory_delete           — Delete a room
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Optional

from .layers import MemoryStack
from .palace import Palace
from .storage import Storage
from .searcher import Searcher
from .miner import OpenClawMiner

# ---------------------------------------------------------------------------
# MCP Server bootstrap
# ---------------------------------------------------------------------------

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from mcp.server.stdio import stdio_server
    import mcp.server.stdio
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


class MemoryTools:
    """Memory system tools for MCP."""

    def __init__(self):
        self.stack = MemoryStack()
        self.palace = Palace()
        self.storage = Storage()
        self.searcher = Searcher(self.palace, self.storage, self.stack.l3)
        self.miner = OpenClawMiner(self.palace)

    def wake_up(self) -> str:
        """Render L0 (Identity) + L1 (Essential Story). ~600 tokens."""
        return self.stack.wake_up()

    def load_wing(self, wing_name: str) -> str:
        """Load all rooms in a wing."""
        return self.stack.load_wing(wing_name)

    def load_hall(self, wing_name: str, hall_name: str) -> str:
        """Load all rooms in a hall."""
        return self.stack.load_hall(wing_name, hall_name)

    def save_memory(
        self, wing: str, hall: str, room: str, content: str
    ) -> dict:
        """Save a memory to the palace."""
        room_obj = self.palace.save_memory(wing, hall, room, content)
        # Also index in storage
        self.storage.insert(wing, hall, room, content)
        # Also add to ChromaDB
        self.stack.l3.add_memory(content, wing, hall, room)
        return {
            "success": True,
            "wing": wing,
            "hall": hall,
            "room": room,
            "path": str(room_obj.path),
        }

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search across all memory layers."""
        results = self.searcher.search(query, limit=limit)
        return [
            {
                "text": r.text,
                "source": r.source,
                "wing": r.wing,
                "hall": r.hall,
                "room": r.room,
                "score": r.score,
            }
            for r in results
        ]

    def list_wings(self) -> list[str]:
        """List all wings."""
        return self.palace.list_wings()

    def list_halls(self, wing_name: str) -> list[str]:
        """List halls in a wing."""
        return self.palace.list_halls(wing_name)

    def list_rooms(self, wing_name: str, hall_name: str) -> list[str]:
        """List rooms in a wing/hall."""
        return self.palace.list_rooms(wing_name, hall_name)

    def stats(self) -> dict:
        """Get memory system statistics."""
        palace_stats = self.palace.stats()
        stack_stats = self.stack.stats()
        return {
            **palace_stats,
            **stack_stats,
            "storage_count": self.storage.count(),
        }

    def mine(
        self, workspace_path: Optional[str] = None
    ) -> dict:
        """Mine from OpenClaw workspace files."""
        if workspace_path:
            result = self.miner.mine_workspace(Path(workspace_path))
        else:
            result = self.miner.mine_all()

        return {
            "files_processed": result.files_processed,
            "memories_created": result.memories_created,
            "wings_created": result.wings_created,
            "errors": result.errors,
        }

    def delete_memory(self, wing: str, hall: str, room: str) -> dict:
        """Delete a memory room."""
        deleted = self.palace.delete_memory(wing, hall, room)
        return {"success": deleted, "wing": wing, "hall": hall, "room": room}

    def read_room(self, wing: str, hall: str, room: str) -> str:
        """Read a specific room's content."""
        return self.stack.load_room(wing, hall, room)


# ---------------------------------------------------------------------------
# MCP Server runner
# ---------------------------------------------------------------------------


def create_server() -> "Server":
    """Create and configure the MCP server."""
    if not HAS_MCP:
        raise ImportError("mcp package not installed. Run: pip install mcp")

    server = Server("openclaw-memory")
    tools = MemoryTools()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="memory_wake_up",
                description="Get L0 (Identity) + L1 (Essential Story) context. ~600 tokens. Put this at the top of your system prompt.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="memory_load_wing",
                description="Load all rooms in a wing (Layer 2 on-demand memory).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "wing_name": {
                            "type": "string",
                            "description": "Name of the wing to load",
                        }
                    },
                    "required": ["wing_name"],
                },
            ),
            Tool(
                name="memory_load_hall",
                description="Load all rooms in a specific hall.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "wing_name": {"type": "string"},
                        "hall_name": {"type": "string"},
                    },
                    "required": ["wing_name", "hall_name"],
                },
            ),
            Tool(
                name="memory_save",
                description="Save a memory to the palace. Creates wing/hall/room structure if needed.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "wing": {"type": "string", "description": "Wing name (person or project)"},
                        "hall": {"type": "string", "description": "Hall name (decisions, preferences, milestones, problems, context, facts)"},
                        "room": {"type": "string", "description": "Room name (specific idea or topic)"},
                        "content": {"type": "string", "description": "The memory content to save"},
                    },
                    "required": ["wing", "hall", "room", "content"],
                },
            ),
            Tool(
                name="memory_search",
                description="Search across all memory layers (palace structure, keyword, semantic).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Max results", "default": 5},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="memory_list_wings",
                description="List all wings in the palace.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="memory_list_halls",
                description="List halls in a wing.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "wing_name": {"type": "string"},
                    },
                    "required": ["wing_name"],
                },
            ),
            Tool(
                name="memory_list_rooms",
                description="List rooms in a wing/hall.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "wing_name": {"type": "string"},
                        "hall_name": {"type": "string"},
                    },
                    "required": ["wing_name", "hall_name"],
                },
            ),
            Tool(
                name="memory_stats",
                description="Get memory system statistics.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="memory_mine",
                description="Mine memories from OpenClaw workspace files.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace_path": {
                            "type": "string",
                            "description": "Path to OpenClaw workspace (default: ~/.openclaw/workspace)",
                        }
                    },
                },
            ),
            Tool(
                name="memory_delete",
                description="Delete a memory room.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "wing": {"type": "string"},
                        "hall": {"type": "string"},
                        "room": {"type": "string"},
                    },
                    "required": ["wing", "hall", "room"],
                },
            ),
            Tool(
                name="memory_read_room",
                description="Read a specific room's full content.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "wing": {"type": "string"},
                        "hall": {"type": "string"},
                        "room": {"type": "string"},
                    },
                    "required": ["wing", "hall", "room"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[TextContent]:
        try:
            if name == "memory_wake_up":
                result = tools.wake_up()
            elif name == "memory_load_wing":
                result = tools.load_wing(arguments["wing_name"])
            elif name == "memory_load_hall":
                result = tools.load_hall(arguments["wing_name"], arguments["hall_name"])
            elif name == "memory_save":
                result = tools.save_memory(
                    arguments["wing"],
                    arguments["hall"],
                    arguments["room"],
                    arguments["content"],
                )
            elif name == "memory_search":
                result = tools.search(
                    arguments["query"], arguments.get("limit", 5)
                )
            elif name == "memory_list_wings":
                result = {"wings": tools.list_wings()}
            elif name == "memory_list_halls":
                result = {"halls": tools.list_halls(arguments["wing_name"])}
            elif name == "memory_list_rooms":
                result = {"rooms": tools.list_rooms(arguments["wing_name"], arguments["hall_name"])}
            elif name == "memory_stats":
                result = tools.stats()
            elif name == "memory_mine":
                result = tools.mine(arguments.get("workspace_path"))
            elif name == "memory_delete":
                result = tools.delete_memory(arguments["wing"], arguments["hall"], arguments["room"])
            elif name == "memory_read_room":
                result = tools.read_room(arguments["wing"], arguments["hall"], arguments["room"])
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


async def run_server():
    """Run the MCP server."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """CLI entry point."""
    import asyncio
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
