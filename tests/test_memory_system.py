"""
tests/test_memory_system.py — Tests for OpenClaw Memory System
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from openclaw_memory.layers import MemoryStack, Layer0, Layer1, Layer2, Layer3
from openclaw_memory.palace import Palace, Wing, Hall, Room
from openclaw_memory.storage import Storage
from openclaw_memory.searcher import Searcher
from openclaw_memory.miner import OpenClawMiner


@pytest.fixture
def temp_root():
    """Create a temporary root for memory storage."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def palace(temp_root):
    return Palace(root=temp_root / "palace")


@pytest.fixture
def storage(temp_root):
    return Storage(data_path=temp_root / "data")


@pytest.fixture
def layer3(temp_root):
    return Layer3(db_path=temp_root / "chroma")


class TestPalace:
    """Test the palace structure."""

    def test_create_wing(self, palace):
        wing = palace.create_wing("TestWing")
        assert palace.has_wing("TestWing")
        assert wing.name == "TestWing"

    def test_wing_persistence(self, temp_root):
        p1 = Palace(root=temp_root / "palace")
        p1.create_wing("PersistenceWing")
        del p1

        p2 = Palace(root=temp_root / "palace")
        assert p2.has_wing("PersistenceWing")

    def test_save_and_load_memory(self, palace):
        room = palace.save_memory("Matt", "preferences", "likes-coffee", "Matt likes coffee in the morning.")
        assert room.path.exists()
        assert "coffee" in room.read()

    def test_delete_memory(self, palace):
        palace.save_memory("Matt", "preferences", "temp-note", "A temporary note.")
        assert palace.delete_memory("Matt", "preferences", "temp-note")
        assert palace.find_room("Matt", "preferences", "temp-note") is None

    def test_list_wings_halls_rooms(self, palace):
        palace.save_memory("Matt", "preferences", "likes-brief", "Prefers brief responses.")
        palace.save_memory("Matt", "decisions", "uses-openclaw", "Chose OpenClaw as assistant.")
        palace.save_memory("ClaudeRE", "status", "module-3", "Module 3 is complete.")

        assert set(palace.list_wings()) == {"Matt", "ClaudeRE"}
        assert set(palace.list_halls("Matt")) == {"preferences", "decisions"}
        assert palace.list_rooms("Matt", "preferences") == ["likes-brief"]

    def test_safe_name(self, palace):
        """Names should be sanitized for filesystem use."""
        assert Palace._safe_name("My Project!") == "my-project"
        assert Palace._safe_name("  spaces  ") == "spaces"


class TestLayers:
    """Test the 4-layer memory stack."""

    def test_layer0_identity(self, temp_root):
        identity_path = temp_root / "identity.txt"
        identity_path.write_text("I am a test assistant.")
        l0 = Layer0(identity_path=identity_path)
        assert "test assistant" in l0.render()
        assert l0.token_count() > 0

    def test_layer1_essential(self, temp_root):
        palace_root = temp_root / "palace"
        essential_path = temp_root / "essential.md"

        # Create some rooms
        p = Palace(root=palace_root)
        p.save_memory("Matt", "decisions", "first-decision", "First decision content.")
        p.save_memory("Matt", "preferences", "first-pref", "Pref content.")

        l1 = Layer1(palace_path=palace_root, essential_path=essential_path)
        l1.rebuild()
        assert essential_path.exists()
        assert "first-decision" in l1.render()

    def test_layer2_on_demand(self, temp_root):
        palace_root = temp_root / "palace"
        p = Palace(root=palace_root)
        p.save_memory("Matt", "preferences", "likes-python", "Matt likes Python.")

        l2 = Layer2(palace_path=palace_root)
        content = l2.render_wing("Matt")
        assert "likes-python" in content

        content = l2.render_hall("Matt", "preferences")
        assert "likes-python" in content

    def test_layer3_chroma(self, temp_root):
        l3 = Layer3(db_path=temp_root / "chroma")
        doc_id = l3.add_memory("Test content", "Matt", "preferences", "test-room")
        assert l3.count() == 1

        results = l3.search("Test content", n_results=1)
        assert len(results) == 1
        assert "Test content" in results[0]["text"]

        l3.delete(doc_id)
        assert l3.count() == 0

    def test_memory_stack_wake_up(self, temp_root):
        identity_path = temp_root / "identity.txt"
        identity_path.write_text("I am Matilda, sharp and helpful.")
        palace_root = temp_root / "palace"

        p = Palace(root=palace_root)
        p.save_memory("Matt", "context", "github-info", "GitHub: MattSureham")

        l1 = Layer1(palace_path=palace_root, essential_path=temp_root / "essential.md")
        l1.rebuild()

        stack = MemoryStack(root=temp_root)
        wake = stack.wake_up()
        assert "Matilda" in wake or "identity" in wake.lower()


class TestStorage:
    """Test SQLite storage."""

    def test_insert_and_get(self, storage):
        id = storage.insert("Matt", "preferences", "likes-python", "Matt likes Python.", tags=["python", "preferences"])
        entry = storage.get(id)
        assert entry is not None
        assert entry.wing == "Matt"
        assert "Python" in entry.content

    def test_search_text(self, storage):
        storage.insert("Matt", "preferences", "coffee", "Morning coffee habit.")
        storage.insert("Matt", "decisions", "postgres", "Chose Postgres.")

        results = storage.search_text("postgres")
        assert len(results) == 1
        assert results[0].hall == "decisions"

    def test_by_wing(self, storage):
        storage.insert("Matt", "preferences", "a", "Content A.")
        storage.insert("Matt", "decisions", "b", "Content B.")
        storage.insert("ClaudeRE", "status", "c", "Content C.")

        matt_entries = storage.by_wing("Matt")
        assert len(matt_entries) == 2


class TestSearcher:
    """Test the searcher."""

    def test_search_palace(self, temp_root):
        palace_root = temp_root / "palace"
        p = Palace(root=palace_root)
        p.save_memory("Matt", "decisions", "postgresql-choice", "Chose Postgres over MySQL for reliability.")

        storage = Storage(data_path=temp_root / "data")
        layer3 = Layer3(db_path=temp_root / "chroma")
        searcher = Searcher(p, storage, layer3)

        results = searcher.search("postgres", mode="palace")
        assert len(results) >= 1


class TestMiner:
    """Test the OpenClaw miner."""

    def test_mine_workspace(self, temp_root, monkeypatch):
        # Create a fake OpenClaw workspace structure
        workspace = temp_root / "workspace"
        workspace.mkdir()

        memory_md = workspace / "MEMORY.md"
        memory_md.write_text("""# MEMORY.md - Long-term Memory

## About Matt
- **Name:** Matthew "Matt"
- **GitHub:** @MattSureham

## Projects
- **ClaudeRE** — Claude Code clone project
""")

        memory_dir = workspace / "memory"
        memory_dir.mkdir()
        daily = memory_dir / "2026-04-01.md"
        daily.write_text("""# Memory - 2026-04-01

## Session Summary
- Worked on ClaudeRE module 3
- Fixed bug in QueryEngine
""")

        palace = Palace(root=temp_root / "palace")
        miner = OpenClawMiner(palace)
        result = miner.mine_workspace(workspace)

        assert result.files_processed == 2
        assert result.memories_created >= 2
        assert "Matt" in result.wings_created
