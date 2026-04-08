#!/bin/bash
# openclaw_save_hook.sh — Auto-save hook for OpenClaw
# 
# Add to your OpenClaw config or call after sessions:
#   source /path/to/hooks/openclaw_save_hook.sh
#
# This hook saves the current memory state to the palace.

set -e

PALACE_ROOT="${OPENCLAW_MEMORY_ROOT:-$HOME/.openclaw-memory}"
PALACE_PATH="$PALACE_ROOT/palace"

save_to_palace() {
    local wing="${1:-Matt}"
    local hall="${2:-context}"
    local room="${3:-last-session}"
    local content="$4"

    local room_path="$PALACE_PATH/$wing/$hall/${room}.md"
    mkdir -p "$(dirname "$room_path")"
    echo "$content" > "$room_path"
    echo "[openclaw-memory] Saved: $wing/$hall/$room"
}

wake_up_context() {
    local identity_file="$PALACE_ROOT/identity.txt"
    local essential_file="$PALACE_ROOT/essential.md"
    
    if [ -f "$identity_file" ]; then
        cat "$identity_file"
    fi
    
    if [ -f "$essential_file" ]; then
        echo ""
        echo "---"
        cat "$essential_file"
    fi
}

export -f save_to_palace
export -f wake_up_context
