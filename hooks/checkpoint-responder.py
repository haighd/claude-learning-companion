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
import traceback
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Use shared utilities
from utils.file_locking import acquire_lock, release_lock, LockingNotSupportedError
from utils.formatting import format_usage_percentage

BLACKBOARD_FILE = Path.home() / ".claude" / "clc" / ".coordination" / "blackboard.json"
LOCK_FILE = BLACKBOARD_FILE.with_suffix(".lock")

# Template for checkpoint reminder message shown to the agent
CHECKPOINT_REMINDER_TEMPLATE = """
---
## Checkpoint Reminder from Watcher

The context monitor has detected high context usage ({usage_str}).

**Reason**: {reason}

Please run `/checkpoint` to save your progress before continuing.

This is a proactive checkpoint to preserve context quality.
---
"""


def get_hook_input() -> dict:
    """Read hook input from stdin."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
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
    lock_acquired = False
    try:
        # Acquire exclusive lock to prevent race with concurrent writes
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = open(LOCK_FILE, "w")
        acquire_lock(lock_fd)
        lock_acquired = True

        bb = json.loads(BLACKBOARD_FILE.read_text())
        messages = bb.get("messages", [])

        for msg in messages:
            msg_type = msg.get("type")
            # Supported message format:
            # - Current format: type="checkpoint_trigger" with content as dict/JSON
            #
            # Legacy format (type=None with content="checkpoint_trigger" as a string)
            # is deprecated and no longer handled here because downstream code expects
            # JSON/dict content and would fail on a plain string payload.
            is_checkpoint_trigger = msg_type == "checkpoint_trigger"
            if (
                is_checkpoint_trigger
                and msg.get("to") == "claude-main"
                and not msg.get("read", False)
            ):
                return msg
    except (json.JSONDecodeError, OSError, LockingNotSupportedError, TimeoutError):
        sys.stderr.write(f"[checkpoint-responder] Error reading blackboard:\n{traceback.format_exc()}\n")
    finally:
        if lock_acquired:
            release_lock(lock_fd)
        if lock_fd:
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
    lock_acquired = False
    try:
        # Acquire exclusive lock to prevent race conditions
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = open(LOCK_FILE, "w")
        acquire_lock(lock_fd)
        lock_acquired = True

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

    except (json.JSONDecodeError, OSError, LockingNotSupportedError, TimeoutError):
        sys.stderr.write(f"[checkpoint-responder] Error marking message read:\n{traceback.format_exc()}\n")
    finally:
        if lock_acquired:
            release_lock(lock_fd)
        if lock_fd:
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

        # Parse content: may be dict, JSON string, or other.
        # Parse failures (set to None), None values, and non-dict types are all
        # handled the same way (defaulting to empty dict) since these cases indicate
        # malformed/legacy data where we want graceful degradation to default values.
        content = trigger.get("content")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                content = None

        if not isinstance(content, dict):
            sys.stderr.write(
                f"[checkpoint-responder] Non-dict checkpoint content encountered; "
                f"using defaults instead (content={{}}, reason='watcher request', usage_pct=0%). "
                f"Original type={type(content).__name__}, value={repr(content)}\n"
            )
            content = {}
        reason = content.get("reason", "watcher request")
        # Both conductor.py and watcher_loop.py now put estimated_usage at top level.
        usage = content.get("estimated_usage", 0)
        usage_str, _ = format_usage_percentage(usage, "checkpoint-responder")

        sys.stderr.write(f"[checkpoint-responder] Checkpoint trigger detected: {reason}\n")

        # Return context to remind agent to checkpoint
        output_result({
            "additionalContext": CHECKPOINT_REMINDER_TEMPLATE.format(
                usage_str=usage_str,
                reason=reason
            )
        })
    else:
        output_result({})


if __name__ == "__main__":
    main()
