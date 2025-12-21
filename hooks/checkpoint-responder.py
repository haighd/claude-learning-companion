#!/usr/bin/env python3
"""
Checkpoint Responder Hook - Reads blackboard for checkpoint triggers.

This PostToolUse hook runs after each tool use and checks if the watcher
has requested a checkpoint via the blackboard messaging system.

When a checkpoint_trigger message is found:
1. Returns additionalContext with a checkpoint reminder
2. Marks the message as read to prevent duplicate reminders

Part of Phase 2: Proactive Context Management.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Use shared file locking utility
from utils.file_locking import acquire_lock, release_lock

BLACKBOARD_FILE = Path.home() / ".claude" / "clc" / ".coordination" / "blackboard.json"
LOCK_FILE = BLACKBOARD_FILE.with_suffix(".lock")


def get_hook_input() -> dict:
    """Read hook input from stdin."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, IOError):
        return {}


def output_result(result: dict):
    """Output hook result to stdout."""
    print(json.dumps(result))


def check_checkpoint_trigger() -> Optional[dict]:
    """Check blackboard for unread checkpoint_trigger messages.

    Uses file locking to prevent race conditions with concurrent writers.

    Returns:
        The first unread checkpoint_trigger message, or None if none found.
    """
    if not BLACKBOARD_FILE.exists():
        return None

    lock_fd = None
    try:
        # Acquire exclusive lock to prevent race with concurrent writes
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = open(LOCK_FILE, "w")
        acquire_lock(lock_fd)

        bb = json.loads(BLACKBOARD_FILE.read_text())
        messages = bb.get("messages", [])

        for msg in messages:
            if (msg.get("type") == "checkpoint_trigger"
                and msg.get("to") == "claude-main"
                and not msg.get("read", False)):
                return msg
    except (json.JSONDecodeError, IOError, RuntimeError) as e:
        # RuntimeError: File locking not supported on this platform
        sys.stderr.write(f"[checkpoint-responder] Error reading blackboard: {e}\n")
    finally:
        if lock_fd:
            release_lock(lock_fd)
            lock_fd.close()

    return None


def mark_message_read(msg_id: str):
    """Mark a blackboard message as read.

    Uses file locking to prevent race conditions with concurrent writers.

    Args:
        msg_id: The ID of the message to mark as read.
    """
    if not BLACKBOARD_FILE.exists():
        return

    lock_fd = None
    try:
        # Acquire exclusive lock to prevent race conditions
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = open(LOCK_FILE, "w")
        acquire_lock(lock_fd)

        # Re-read blackboard under lock (may have changed)
        bb = json.loads(BLACKBOARD_FILE.read_text())
        for msg in bb.get("messages", []):
            if msg.get("id") == msg_id:
                msg["read"] = True
                msg["read_at"] = datetime.now(timezone.utc).isoformat()
                break

        # Write atomically
        temp_file = BLACKBOARD_FILE.with_suffix(".tmp")
        temp_file.write_text(json.dumps(bb, indent=2))
        temp_file.rename(BLACKBOARD_FILE)

    except (json.JSONDecodeError, OSError, RuntimeError) as e:
        # RuntimeError: File locking not supported on this platform
        sys.stderr.write(f"[checkpoint-responder] Error marking message read: {e}\n")
    finally:
        if lock_fd:
            release_lock(lock_fd)
            lock_fd.close()


def main():
    """Main hook logic."""
    # Read hook input (we don't use it, but must consume stdin)
    get_hook_input()

    # Check for checkpoint trigger
    trigger = check_checkpoint_trigger()

    if trigger:
        # Mark as read so we don't repeat
        msg_id = trigger.get("id", "")
        mark_message_read(msg_id)

        content = trigger.get("content") or {}
        # Enforce standardized dict content format
        if not isinstance(content, dict):
            sys.stderr.write(
                "[checkpoint-responder] Unexpected non-dict content in checkpoint trigger; "
                "expected a dict. Ignoring content.\n"
            )
            content = {}
        reason = content.get("reason", "watcher request")
        usage = content.get("estimated_usage", 0)
        usage_pct = usage * 100

        sys.stderr.write(f"[checkpoint-responder] Checkpoint trigger detected: {reason}\n")

        # Return context to remind agent to checkpoint
        output_result({
            "additionalContext": f"""
---
## Checkpoint Reminder from Watcher

The context monitor has detected high context utilization ({usage_pct:.0f}%).

**Reason**: {reason}

Please run `/checkpoint` to save your progress before continuing.

This is a proactive checkpoint to preserve context quality.
---
"""
        })
    else:
        output_result({})


if __name__ == "__main__":
    main()
