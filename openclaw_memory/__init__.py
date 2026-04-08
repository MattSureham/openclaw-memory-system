"""
OpenClaw Memory System
~~~~~~~~~~~~~~~~~~~~~~

A memory system for OpenClaw agents — palace structure, layered memory, MCP tools.

Example:
    from openclaw_memory import MemoryStack

    stack = MemoryStack()
    context = stack.wake_up()  # L0 + L1 ~600 tokens
    print(context)
"""

from .layers import MemoryStack, Layer0, Layer1, Layer2, Layer3
from .palace import Palace, Wing, Hall, Room
from .storage import Storage, MemoryEntry
from .searcher import Searcher, SearchResult
from .miner import OpenClawMiner, MiningResult
from .mcp_server import create_server, run_server
from .cli import main as cli_main

__version__ = "0.1.0"
__all__ = [
    "MemoryStack",
    "Layer0",
    "Layer1",
    "Layer2",
    "Layer3",
    "Palace",
    "Wing",
    "Hall",
    "Room",
    "Storage",
    "MemoryEntry",
    "Searcher",
    "SearchResult",
    "OpenClawMiner",
    "MiningResult",
    "create_server",
    "run_server",
    "cli_main",
]
