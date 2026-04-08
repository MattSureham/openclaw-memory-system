"""
cli.py — CLI for OpenClaw Memory System
========================================

Usage:
    openclaw-memory init [--path PATH]
    openclaw-memory mine [--path PATH]
    openclaw-memory search QUERY [--limit N]
    openclaw-memory save WING HALL ROOM CONTENT
    openclaw-memory list [--wing WING] [--hall HALL]
    openclaw-memory stats
    openclaw-memory delete WING HALL ROOM
    openclaw-memory wake-up
    openclaw-memory mcp
"""

from __future__ import annotations

import argparse
import sys
import json
from pathlib import Path

from .layers import MemoryStack, DEFAULT_MEMORY_ROOT
from .palace import Palace
from .storage import Storage
from .searcher import Searcher
from .miner import OpenClawMiner


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize the memory system."""
    root = Path(args.path) if args.path else DEFAULT_MEMORY_ROOT
    root.mkdir(parents=True, exist_ok=True)

    # Create default identity file
    identity_path = root / "identity.txt"
    if not identity_path.exists():
        identity_path.write_text(
            "I am an AI assistant.\n"
            "No identity has been set yet.\n"
            "Run: openclaw-memory identity set \"I am ...\"\n"
        )
        print(f"Created: {identity_path}")

    # Create palace structure
    palace = Palace(root / "palace")
    palace._ensure_root()

    # Create default wings
    for wing_name in ["Matt", "Matilda", "OpenClaw"]:
        if not palace.has_wing(wing_name):
            palace.create_wing(wing_name)
            print(f"Created wing: {wing_name}")

    # Create essential story
    from .layers import Layer1
    l1 = Layer1()
    l1.essential_path = root / "essential.md"
    l1.rebuild()

    print(f"\nInitialized at: {root}")
    print("Run 'openclaw-memory mine' to import your existing memory files.")
    return 0


def cmd_mine(args: argparse.Namespace) -> int:
    """Mine memories from OpenClaw workspace files."""
    workspace_path = Path(args.path) if args.path else None
    miner = OpenClawMiner()

    if workspace_path:
        result = miner.mine_workspace(workspace_path)
    else:
        result = miner.mine_all()

    print(f"Files processed: {result.files_processed}")
    print(f"Memories created: {result.memories_created}")
    print(f"Wings: {result.wings_created}")
    if result.errors:
        print(f"Errors: {result.errors}")

    # Rebuild essential story
    from .layers import Layer1
    l1 = Layer1()
    l1.rebuild()

    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Search memories."""
    searcher = Searcher()
    results = searcher.search(args.query, limit=args.limit)

    if not results:
        print("No results found.")
        return 0

    for i, r in enumerate(results, 1):
        print(f"\n--- Result {i} [{r.source}] ---")
        print(f"Wing: {r.wing} | Hall: {r.hall} | Room: {r.room}")
        print(f"Score: {r.score:.2f}")
        print(f"\n{r.text[:500]}")

    return 0


def cmd_save(args: argparse.Namespace) -> int:
    """Save a memory."""
    palace = Palace()
    room = palace.save_memory(args.wing, args.hall, args.room, args.content)
    print(f"Saved: {room.path}")

    # Index in storage
    storage = Storage()
    storage.insert(args.wing, args.hall, args.room, args.content)

    # Index in ChromaDB
    stack = MemoryStack()
    stack.l3.add_memory(args.content, args.wing, args.hall, args.room)

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List wings, halls, or rooms."""
    palace = Palace()

    if args.wing is None:
        wings = palace.list_wings()
        print(f"Wings ({len(wings)}):")
        for w in wings:
            print(f"  - {w}")
    elif args.hall is None:
        halls = palace.list_halls(args.wing)
        print(f"Halls in '{args.wing}' ({len(halls)}):")
        for h in halls:
            print(f"  - {h}")
    else:
        rooms = palace.list_rooms(args.wing, args.hall)
        print(f"Rooms in '{args.wing}/{args.hall}' ({len(rooms)}):")
        for r in rooms:
            print(f"  - {r}")

    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show memory system statistics."""
    stack = MemoryStack()
    stats = stack.stats()
    print(json.dumps(stats, indent=2))
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    """Delete a memory room."""
    palace = Palace()
    deleted = palace.delete_memory(args.wing, args.hall, args.room)
    if deleted:
        print(f"Deleted: {args.wing}/{args.hall}/{args.room}")
    else:
        print(f"Room not found: {args.wing}/{args.hall}/{args.room}")
    return 0


def cmd_wake_up(args: argparse.Namespace) -> int:
    """Print wake-up context (L0 + L1)."""
    stack = MemoryStack()
    print(stack.wake_up())
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    """Start the MCP server."""
    from .mcp_server import run_server
    import asyncio
    print("Starting MCP server...", file=sys.stderr)
    asyncio.run(run_server())
    return 0


def cmd_identity(args: argparse.Namespace) -> int:
    """Manage identity."""
    from .layers import Layer0

    l0 = Layer0()
    if args.identity_text:
        l0.save(args.identity_text)
        print(f"Identity saved ({l0.token_count()} tokens).")
    else:
        print(l0.render())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OpenClaw Memory System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="Initialize the memory system")
    p_init.add_argument("--path", help="Custom root path")
    p_init.set_defaults(func=cmd_init)

    # mine
    p_mine = sub.add_parser("mine", help="Mine memories from OpenClaw files")
    p_mine.add_argument("--path", help="OpenClaw workspace path")
    p_mine.set_defaults(func=cmd_mine)

    # search
    p_search = sub.add_parser("search", help="Search memories")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=5)
    p_search.set_defaults(func=cmd_search)

    # save
    p_save = sub.add_parser("save", help="Save a memory")
    p_save.add_argument("wing", help="Wing name")
    p_save.add_argument("hall", help="Hall name")
    p_save.add_argument("room", help="Room name")
    p_save.add_argument("content", help="Memory content")
    p_save.set_defaults(func=cmd_save)

    # list
    p_list = sub.add_parser("list", help="List wings/halls/rooms")
    p_list.add_argument("--wing", help="Wing name")
    p_list.add_argument("--hall", help="Hall name")
    p_list.set_defaults(func=cmd_list)

    # stats
    sub.add_parser("stats", help="Show statistics").set_defaults(func=cmd_stats)

    # delete
    p_delete = sub.add_parser("delete", help="Delete a memory room")
    p_delete.add_argument("wing", help="Wing name")
    p_delete.add_argument("hall", help="Hall name")
    p_delete.add_argument("room", help="Room name")
    p_delete.set_defaults(func=cmd_delete)

    # wake-up
    sub.add_parser("wake-up", help="Print wake-up context").set_defaults(func=cmd_wake_up)

    # mcp
    sub.add_parser("mcp", help="Start MCP server").set_defaults(func=cmd_mcp)

    # identity
    p_id = sub.add_parser("identity", help="Manage identity")
    p_id.add_argument("identity_text", nargs="...", help="Set identity text")
    p_id.set_defaults(func=cmd_identity)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
