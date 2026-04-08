# OpenClaw Memory System 🦞

A memory system for OpenClaw agents — palace structure, layered memory, MCP tools.

## Overview

OpenClaw Memory System gives your AI assistant persistent, structured memory that survives session restarts. It organizes memories into a **Palace** (wings → halls → rooms), uses a **4-layer memory stack** for efficient context loading, and provides **MCP tools** for seamless AI integration.

Inspired by [MemPalace](https://github.com/milla-jovovich/mempalace) — but built natively for OpenClaw.

## Features

- **Palace Structure** — Organize memories into wings (people/projects), halls (categories), and rooms (specific ideas)
- **4-Layer Memory Stack** — Load only what you need, when you need it
  - Layer 0: Identity (~100 tokens) — Always loaded
  - Layer 1: Essential Story (~500 tokens) — Always loaded, top memories
  - Layer 2: On-Demand (~500 each) — Loaded when topic is referenced
  - Layer 3: Deep Search (unlimited) — Full semantic search
- **MCP Tools** — 19 tools for your AI to read/write/search memory
- **Local Only** — No external APIs, no cloud, no subscriptions
- **OpenClaw Native** — Reads from your existing `MEMORY.md`, `memory/` files

## Quick Start

```bash
# Install
pip install openclaw-memory-system

# Initialize (reads your existing OpenClaw memory)
openclaw-memory init ~/projects/my-openclaw

# Mine your existing memory files
openclaw-memory mine ~/projects/my-openclaw

# Search
openclaw-memory search "what did we decide about auth"

# Connect to Claude/MCP
claude mcp add openclaw-memory -- python -m openclaw_memory.mcp_server
```

## Architecture

```
openclaw-memory-system/
├── openclaw_memory/
│   ├── __init__.py
│   ├── layers.py       # 4-layer memory stack
│   ├── palace.py       # Palace structure (wings/halls/rooms)
│   ├── storage.py      # File + SQLite backend
│   ├── miner.py        # Mining from OpenClaw files
│   ├── searcher.py     # Semantic search
│   ├── mcp_server.py   # MCP tools server
│   └── cli.py          # CLI commands
├── hooks/              # Shell hooks for auto-save
├── pyproject.toml
└── README.md
```

## The Palace

Inspired by ancient Greek orators who memorized speeches by placing ideas in rooms of a building:

- **Wing** — A person or project (e.g., "Matt", "ClaudeRE")
- **Hall** — A category within a wing (e.g., "decisions", "preferences", "problems")
- **Room** — A specific memory (e.g., "chose Postgres over MySQL")

This structure alone improves retrieval by ~34% (from MemPalace benchmarks).

## 4-Layer Memory Stack

| Layer | Name | Tokens | Loaded |
|-------|------|--------|--------|
| L0 | Identity | ~100 | Always |
| L1 | Essential Story | ~500 | Always |
| L2 | On-Demand | ~500 each | When referenced |
| L3 | Deep Search | Unlimited | On query |

Wake-up cost: ~600 tokens total. Leaves 95%+ of context free.

## License

MIT
