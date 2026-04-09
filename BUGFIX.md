# Bugfix Report — 2026-04-09

## Bug 1: Wing Name Casing Not Preserved (palace.py)

**Severity:** Medium  
**File:** `openclaw_memory/palace.py`  
**Status:** ✅ Fixed

### Problem

`Palace.create_wing("TestWing")` created a wing with `Wing.name == "testwing"` instead of `"TestWing"`. The `_safe_name()` method lowercases all wing names, which was correct for filesystem paths but incorrect for the in-memory `Wing.name` field.

This caused:
- `list_wings()` returning `["matt", "claudere"]` instead of `["Matt", "ClaudeRE"]`
- Inconsistent behavior between `create_wing()` (caller-supplied name) and `wing()` (lowercased name)

### Root Cause

Both `wing()` and `create_wing()` used `_safe_name()` for both:
1. The filesystem path (where lowercasing/sanitization IS needed)
2. The `Wing.name` attribute (where original casing should be preserved)

### Fix

Store original casing in a `.wingmeta` file inside each wing directory:

- **`wing()`**: On first access, writes `.wingmeta` with original `wing_name` if not already present. Returns `Wing` with original name.
- **`create_wing()`**: Explicitly writes `.wingmeta` with original name after creating directory.
- **`wings()`** (iterator): Reads `.wingmeta` to get original name; falls back to directory name for wings created before this fix.
- **`has_wing()`**: Uses `_safe_name()` for path check (correct).

### Files Changed

- `openclaw_memory/palace.py` — wing name casing preservation

---

## Bug 2: NameError in `_search_palace` (searcher.py)

**Severity:** High (runtime crash)  
**File:** `openclaw_memory/searcher.py`  
**Status:** ✅ Fixed

### Problem

When searching palace rooms, if the query didn't match a room's name but did match its content, a `NameError: name 'content' is not defined` was raised.

### Root Cause

```python
for room in self.palace.all_rooms():
    room_name_lower = room.name.lower()
    if query_lower in room_name_lower:
        content = room.read()  # ← content only defined here
        results.append(...)
    elif query_lower in content.lower():  # ← NameError if query doesn't match name
        ...
```

The `content` variable was assigned only inside the first `if` branch but referenced in the `elif` condition.

### Fix

Moved `content = room.read()` before the conditional so it's always defined:

```python
for room in self.palace.all_rooms():
    room_name_lower = room.name.lower()
    content = room.read()  # ← always defined
    if query_lower in room_name_lower:
        ...
    elif query_lower in content.lower():
        ...
```

### Files Changed

- `openclaw_memory/searcher.py` — moved content read before conditional

---

## Test Results

All 16 tests pass after fixes:

```
tests/test_memory_system.py::TestPalace::test_create_wing PASSED
tests/test_memory_system.py::TestPalace::test_wing_persistence PASSED
tests/test_memory_system.py::TestPalace::test_save_and_load_memory PASSED
tests/test_memory_system.py::TestPalace::test_delete_memory PASSED
tests/test_memory_system.py::TestPalace::test_list_wings_halls_rooms PASSED
tests/test_memory_system.py::TestPalace::test_safe_name PASSED
tests/test_memory_system.py::TestLayers::test_layer0_identity PASSED
tests/test_memory_system.py::TestLayers::test_layer1_essential PASSED
tests/test_memory_system.py::TestLayers::test_layer2_on_demand PASSED
tests/test_memory_system.py::TestLayers::test_layer3_chroma PASSED
tests/test_memory_system.py::TestLayers::test_memory_stack_wake_up PASSED
tests/test_memory_system.py::TestStorage::test_insert_and_get PASSED
tests/test_memory_system.py::TestStorage::test_search_text PASSED
tests/test_memory_system.py::TestStorage::test_by_wing PASSED
tests/test_memory_system.py::TestSearcher::test_search_palace PASSED
tests/test_memory_system.py::TestMiner::test_mine_workspace PASSED
```

**Commit:** `023674e` — `fix: preserve wing name casing + fix searcher NameError`
