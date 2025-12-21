#!/usr/bin/env python3
"""
Single-Pass Watcher System

Generates prompts for watcher agents that do ONE comprehensive monitoring pass.
Watchers analyze state, make decisions, execute interventions, and exit.
Main Claude (via hook reminder) spawns the next watcher when user interacts.

Design:
    User message → Hook checks if watcher needed → Main Claude spawns watcher
    Watcher (Haiku) → analyzes → decides → intervenes if needed → logs → exits
    Next user message → cycle repeats if swarm still active

This is "continuous monitoring with deferred action" - monitoring happens each
user interaction, interventions happen immediately, but the cycle is driven
by user presence rather than autonomous agent spawning.

Usage:
    python watcher_loop.py prompt                              # Output watcher prompt
    python watcher_loop.py handler-prompt --escalation <json>  # Output handler prompt (for complex issues)
    python watcher_loop.py stop                                # Create stop signal file
    python watcher_loop.py status                              # Check watcher status
    python watcher_loop.py clear                               # Clear stop signal
    python watcher_loop.py summary                             # Show last watcher actions
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Use shared file locking utility
from utils.file_locking import acquire_lock, release_lock

# Paths
COORDINATION_DIR = Path.home() / ".claude" / "clc" / ".coordination"
BLACKBOARD_FILE = COORDINATION_DIR / "blackboard.json"
LOCK_FILE = BLACKBOARD_FILE.with_suffix(".lock")
WATCHER_LOG = COORDINATION_DIR / "watcher-log.md"
STOP_FILE = COORDINATION_DIR / "watcher-stop"
DECISION_FILE = COORDINATION_DIR / "decision.md"


def utc_timestamp() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def trigger_checkpoint_via_blackboard(reason: str, metrics: Optional[Dict] = None) -> Optional[str]:
    """Write checkpoint trigger message to blackboard.

    This allows the watcher to request a checkpoint without directly executing it.
    The main Claude agent's checkpoint-responder hook will read this message
    and prompt the user/agent to run /checkpoint.

    Uses file locking to prevent race conditions with concurrent readers/writers.

    Args:
        reason: Why checkpoint is being triggered (e.g., "context_60_percent")
        metrics: Optional dict of context metrics (usage, counts, etc.)

    Returns:
        Message ID if successful, None on failure
    """
    lock_fd = None
    try:
        # Ensure directory exists before locking
        COORDINATION_DIR.mkdir(parents=True, exist_ok=True)

        # Acquire exclusive lock to prevent race conditions
        lock_fd = open(LOCK_FILE, "w")
        acquire_lock(lock_fd)

        # Load or create blackboard under lock
        if BLACKBOARD_FILE.exists():
            bb = json.loads(BLACKBOARD_FILE.read_text())
        else:
            bb = {"messages": [], "context": {}}

        # Ensure messages list exists
        if "messages" not in bb:
            bb["messages"] = []

        # Create checkpoint trigger message
        msg_id = f"msg-{uuid.uuid4().hex[:8]}"
        # Note: estimated_usage is available via metrics dict if present;
        # we don't duplicate it at the top level to keep message structure clean.
        message = {
            "id": msg_id,
            "from": "watcher",
            "to": "claude-main",
            "content": json.dumps({
                "reason": reason,
                "estimated_usage": metrics.get("estimated_usage", 0) if metrics else 0,
                "metrics": metrics or {},
            }),
            "read": False,
            "timestamp": utc_timestamp()
        }

        bb["messages"].append(message)

        # Write atomically
        temp_file = BLACKBOARD_FILE.with_suffix(".tmp")
        temp_file.write_text(json.dumps(bb, indent=2))
        temp_file.rename(BLACKBOARD_FILE)

        return msg_id

    except (json.JSONDecodeError, OSError, RuntimeError):
        # RuntimeError: File locking not supported on this platform
        import traceback
        print(f"Failed to write checkpoint trigger:\n{traceback.format_exc()}", file=sys.stderr)
        return None
    finally:
        if lock_fd:
            release_lock(lock_fd)
            lock_fd.close()


def gather_state() -> Dict[str, Any]:
    """Gather current coordination state."""
    now = datetime.now(timezone.utc)
    state = {
        "timestamp": now.isoformat(),
        "blackboard": {},
        "agent_files": [],
        "stop_requested": STOP_FILE.exists(),
    }

    if BLACKBOARD_FILE.exists():
        try:
            state["blackboard"] = json.loads(BLACKBOARD_FILE.read_text())
        except (json.JSONDecodeError, OSError) as e:
            state["blackboard"] = {"error": f"Could not parse blackboard.json: {e}"}

    for f in COORDINATION_DIR.glob("agent_*.md"):
        mtime = datetime.fromtimestamp(f.stat().st_mtime).astimezone(timezone.utc)
        age_seconds = (now - mtime).total_seconds()
        state["agent_files"].append({
            "name": f.name,
            "age_seconds": round(age_seconds),
            "size_bytes": f.stat().st_size,
        })

    return state


def output_watcher_prompt():
    """Output single-pass watcher prompt."""
    state = gather_state()

    prompt = f"""You are a single-pass monitoring agent for a multi-agent swarm.

## Your Job

Do ONE comprehensive monitoring pass:
1. Analyze the coordination state
2. Detect any problems
3. Take action if needed (you CAN update files directly)
4. Log your findings
5. Exit with a clear summary

You do NOT need to spawn another watcher - that happens automatically on the next user interaction.

## Current Coordination State

```json
{json.dumps(state, indent=2)}
```

## Step 1: Analyze State

Check for these problems:
- **Stale agents**: No heartbeat update > 120 seconds (check last_seen timestamps)
- **Errors**: Any "error" fields in blackboard
- **Stuck tasks**: Agent marked "active" but no progress
- **Completed swarm**: All agents status = "completed" or "failed"

## Step 2: Determine Status

Based on analysis, your status is one of:

| Status | Meaning |
|--------|---------|
| `nominal` | Everything healthy, swarm progressing |
| `stale` | Agent(s) not updating, may need restart |
| `error` | Error detected in coordination state |
| `complete` | Swarm finished (all agents done) |
| `stopped` | Stop file exists, monitoring should end |

## Step 3: Take Action (if needed)

**For `stale` agents - you can restart them directly:**

```python
# Update blackboard to restart agent
import json
from pathlib import Path

bb_path = Path.home() / ".claude" / "clc" / ".coordination" / "blackboard.json"
bb = json.loads(bb_path.read_text())

# Mark agent for restart
bb["agents"]["<agent_id>"]["status"] = "restarting"
bb["agents"]["<agent_id>"]["last_seen"] = "<current_timestamp>"

bb_path.write_text(json.dumps(bb, indent=2))
```

**For `error` states - log the error and recommend action**

**For `complete` - create stop file to end monitoring:**
```bash
touch ~/.claude/clc/.coordination/watcher-stop
```

## Step 4: Log Your Findings

Append to watcher-log.md:
```bash
echo "<timestamp> | STATUS: <status> | NOTES: <brief observation>" >> ~/.claude/clc/.coordination/watcher-log.md
```

## Step 5: Output Summary

End with a clear summary block:

```
== WATCHER SUMMARY ==
STATUS: <nominal|stale|error|complete|stopped>
AGENTS_CHECKED: <count>
ISSUES_FOUND: <count or "none">
ACTIONS_TAKEN: <what you did, or "none">
RECOMMENDATION: <what main Claude should do next, if anything>
```

## Important Notes

- You have FULL access to Bash, Read, Edit, Write tools
- You CAN and SHOULD fix problems directly when possible
- You do NOT have Task tool (cannot spawn agents) - that's fine, main Claude handles that
- Be concise - this runs frequently
- If swarm is complete, create the stop file so monitoring ends

## Example Workflow

1. Read the state above
2. Notice agent "worker-1" last_seen is 300 seconds ago (stale!)
3. Update blackboard to mark it "restarting"
4. Log: "Restarted stale agent worker-1"
5. Output summary with STATUS: stale, ACTIONS_TAKEN: restarted worker-1
"""

    print(prompt)


def output_handler_prompt(escalation_json: str):
    """Output handler prompt for complex issues requiring deeper analysis."""
    try:
        escalation = json.loads(escalation_json)
    except json.JSONDecodeError:
        escalation = {"reason": escalation_json, "severity": "unknown"}

    prompt = f"""You are an intervention handler for a complex swarm issue.

The regular watcher detected something that needs deeper analysis.

## Escalation Details

```json
{json.dumps(escalation, indent=2)}
```

## Your Tasks

### 1. Gather Full Context

Read these files to understand the situation:
- `~/.claude/clc/.coordination/blackboard.json` - agent states
- `~/.claude/clc/.coordination/watcher-log.md` - monitoring history
- Any `agent_*.md` files in `.coordination/` - agent outputs

### 2. Analyze the Situation

- What exactly went wrong?
- Is this recoverable or critical?
- What's the root cause?

### 3. Decide and Execute

Available actions (pick one):

| Action | When to Use | How to Execute |
|--------|-------------|----------------|
| **RESTART** | Agent stuck but task valid | Update blackboard: status="restarting" |
| **ABANDON** | Task is invalid/impossible | Update blackboard: status="abandoned" |
| **ESCALATE** | Need human decision | Write to `~/.claude/clc/ceo-inbox/` |

### 4. Document Your Decision

Write to `~/.claude/clc/.coordination/decision.md`:

```markdown
## [timestamp] HANDLER DECISION

**Issue:** <what was wrong>
**Analysis:** <your reasoning>
**Action:** <RESTART|ABANDON|ESCALATE>
**Details:** <what you did>
```

### 5. Log and Exit

Append to watcher-log.md:
```
<timestamp> | HANDLER: <action taken> | <brief note>
```

Then output summary:
```
== HANDLER SUMMARY ==
ISSUE: <what was escalated>
DECISION: <action taken>
RESULT: <outcome>
```

## Important

- Be decisive - analyze quickly, act clearly
- You CAN fix things directly (update files, blackboard)
- You do NOT need to spawn another watcher - that's automatic
- If you need human input, use ESCALATE (write to ceo-inbox/)
"""

    print(prompt)


def stop_watcher_loop():
    """Create stop signal file."""
    COORDINATION_DIR.mkdir(parents=True, exist_ok=True)
    STOP_FILE.write_text(f"Stop requested at {utc_timestamp()}\n")
    print(f"Stop signal created: {STOP_FILE}")
    print("Monitoring will stop - no more watchers will be spawned.")


def check_status():
    """Check watcher/swarm status."""
    print("=" * 50)
    print("WATCHER STATUS")
    print("=" * 50)

    # Stop file
    if STOP_FILE.exists():
        print(f"[STOP] Stop requested: YES")
        print(f"       ({STOP_FILE.read_text().strip()})")
    else:
        print("[OK] Stop requested: NO (monitoring active)")

    # Watcher log
    if WATCHER_LOG.exists():
        log = WATCHER_LOG.read_text()
        entries = log.count("STATUS:")
        print(f"\nLog entries: {entries}")

        # Show last 3 entries
        lines = [l for l in log.strip().split("\n") if l.strip()]
        if lines:
            print("   Recent:")
            for line in lines[-3:]:
                print(f"   {line[:70]}...")
    else:
        print("\nLog: No entries yet")

    # Blackboard state
    state = gather_state()
    bb = state.get("blackboard", {})
    agents = bb.get("agents", {})

    print(f"\nAgents in blackboard: {len(agents)}")

    if agents:
        active = sum(1 for a in agents.values() if a.get("status") == "active")
        completed = sum(1 for a in agents.values() if a.get("status") == "completed")
        other = len(agents) - active - completed
        print(f"   Active: {active} | Completed: {completed} | Other: {other}")

        # Check for stale
        now = datetime.now(timezone.utc)
        for aid, agent in agents.items():
            last_seen = agent.get("last_seen", "")
            if last_seen:
                try:
                    ls_time = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                    # Ensure timezone-aware comparison
                    if ls_time.tzinfo is None:
                        ls_time = ls_time.replace(tzinfo=timezone.utc)
                    age = (now - ls_time).total_seconds()
                    if age > 120 and agent.get("status") == "active":
                        print(f"   [!] {aid}: STALE ({int(age)}s since last update)")
                except (ValueError, TypeError, AttributeError) as e:
                    # Skip agents with malformed timestamps
                    pass

    print("=" * 50)


def clear_stop():
    """Clear the stop signal to allow monitoring to resume."""
    if STOP_FILE.exists():
        STOP_FILE.unlink()
        print("[OK] Stop signal cleared.")
        print("     Monitoring can resume on next user interaction.")
    else:
        print("No stop signal to clear.")


def show_summary():
    """Show summary of last watcher actions."""
    print("=" * 50)
    print("LAST WATCHER SUMMARY")
    print("=" * 50)

    # Check decision file
    if DECISION_FILE.exists():
        print("\nLast Decision:")
        content = DECISION_FILE.read_text()
        # Show last decision block
        if "## [" in content:
            blocks = content.split("## [")
            if len(blocks) > 1:
                last_block = "## [" + blocks[-1]
                print(last_block[:500])
                if len(last_block) > 500:
                    print("   ...")
        else:
            print(content[:300])
    else:
        print("\nNo decisions recorded yet")

    # Check watcher log for last entry
    if WATCHER_LOG.exists():
        log = WATCHER_LOG.read_text()
        lines = [l for l in log.strip().split("\n") if l.strip()]
        if lines:
            print(f"\nLast Log Entry:")
            print(f"   {lines[-1]}")

    print("=" * 50)


def main():
    if len(sys.argv) < 2:
        print("Single-Pass Watcher System")
        print("")
        print("Usage: python watcher_loop.py <command>")
        print("")
        print("Commands:")
        print("  prompt                              Generate watcher prompt")
        print("  handler-prompt --escalation <json>  Generate handler prompt")
        print("  stop                                Stop monitoring (create stop file)")
        print("  status                              Show current status")
        print("  clear                               Clear stop signal, resume monitoring")
        print("  summary                             Show last watcher actions")
        print("")
        print("Model: Single-pass watchers analyze->decide->act->exit.")
        print("       Main Claude spawns next watcher on user interaction.")
        return

    cmd = sys.argv[1].lower()

    if cmd == "prompt":
        output_watcher_prompt()
    elif cmd == "handler-prompt":
        escalation_json = "{}"
        if len(sys.argv) > 2 and sys.argv[2] == "--escalation":
            if len(sys.argv) > 3:
                escalation_json = sys.argv[3]
            else:
                print("Error: --escalation requires JSON argument", file=sys.stderr)
                sys.exit(1)
        output_handler_prompt(escalation_json)
    elif cmd == "stop":
        stop_watcher_loop()
    elif cmd == "status":
        check_status()
    elif cmd == "clear":
        clear_stop()
    elif cmd == "summary":
        show_summary()
    else:
        print(f"Unknown command: {cmd}")
        print("Use: prompt, handler-prompt, stop, status, clear, summary")
        sys.exit(1)


if __name__ == "__main__":
    main()
