#!/usr/bin/env python3
"""
Haiku Watcher - Real Claude Haiku agent for swarm monitoring.

This is NOT a state machine. It spawns an actual Claude Haiku agent
that THINKS about whether something is wrong.

Usage:
    Called by launcher or directly via Claude Code Task tool.

Design:
    - Reads coordination state
    - Passes to Haiku agent with monitoring prompt
    - Agent reasons about the state
    - Returns assessment: "nominal" or escalation details
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Import context monitor for Phase 2 proactive checkpoint management
try:
    from context_monitor import get_context_status
    CONTEXT_MONITOR_AVAILABLE = True
except ImportError:
    get_context_status = None
    CONTEXT_MONITOR_AVAILABLE = False

# Paths
COORDINATION_DIR = Path.home() / ".claude" / "clc" / ".coordination"
BLACKBOARD_FILE = COORDINATION_DIR / "blackboard.json"
WATCHER_LOG = COORDINATION_DIR / "watcher-log.md"


def gather_state() -> Dict[str, Any]:
    """Gather current coordination state for the agent to analyze."""
    state = {
        "timestamp": datetime.now().isoformat(),
        "blackboard": {},
        "agent_files": [],
        "recent_activity": [],
        "context_status": None,  # Phase 2: Context utilization monitoring
    }

    # Read blackboard
    if BLACKBOARD_FILE.exists():
        try:
            state["blackboard"] = json.loads(BLACKBOARD_FILE.read_text())
        except (json.JSONDecodeError, IOError, OSError) as e:
            state["blackboard"] = {"error": f"Could not parse blackboard.json: {e}"}

    # List agent files
    for f in COORDINATION_DIR.glob("agent_*.md"):
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        age_seconds = (datetime.now() - mtime).total_seconds()
        state["agent_files"].append({
            "name": f.name,
            "age_seconds": round(age_seconds),
            "size_bytes": f.stat().st_size,
        })

    # Check for any .status files
    agents_dir = COORDINATION_DIR / "agents"
    if agents_dir.exists():
        for f in agents_dir.glob("*.status"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            age_seconds = (datetime.now() - mtime).total_seconds()
            state["recent_activity"].append({
                "agent": f.stem,
                "last_heartbeat_seconds_ago": round(age_seconds),
            })

    # Phase 2: Get context utilization status
    if CONTEXT_MONITOR_AVAILABLE and get_context_status:
        try:
            state["context_status"] = get_context_status()
        except (AttributeError, TypeError, KeyError, IOError, ValueError):
            # All exceptions are handled uniformly here because context status
            # is non-critical for the watcher - we log the full traceback and
            # continue monitoring. The exception types cover:
            # - AttributeError/TypeError/KeyError: context monitor module issues
            # - IOError: file system issues reading session state
            # - ValueError: datetime parsing errors in check_cooldown
            import traceback
            state["context_status"] = {"error": f"Failed to get context status: {traceback.format_exc()}"}

    return state


def get_haiku_prompt(state: Dict[str, Any]) -> str:
    """Build the prompt for the Haiku monitoring agent."""

    # Format context status section if available
    context_section = ""
    context_status = state.get("context_status")
    if context_status and isinstance(context_status, dict) and "estimated_usage" in context_status:
        usage_pct = context_status.get("estimated_usage", 0) * 100
        should_checkpoint = context_status.get("should_checkpoint", False)
        reason = context_status.get("reason", "N/A")
        in_cooldown = context_status.get("in_cooldown", False)
        context_section = f"""
## Context Utilization (Phase 2)

- **Estimated Usage**: {usage_pct:.0f}%
- **Should Checkpoint**: {should_checkpoint}
- **Reason**: {reason}
- **In Cooldown**: {in_cooldown}
"""

    return f"""You are a lightweight monitoring agent checking on a multi-agent swarm.

## Current Coordination State

```json
{json.dumps(state, indent=2, default=str)}
```
{context_section}
## Your Task

Analyze this state and determine if anything needs attention:

1. Are any agents stale (no heartbeat > 120 seconds)?
2. Are there any error indicators in the blackboard?
3. Is there a deadlock or conflict between agents?
4. Are tasks progressing or stuck?
5. **Is context utilization > 60%?** (trigger checkpoint if not in cooldown)

## Response Format

If everything looks fine:
```
STATUS: nominal
NOTES: [brief observation]
```

If context needs checkpointing (usage > 60% and not in cooldown):
```
STATUS: context_high
REASON: Context at XX% utilization
RECOMMENDED_ACTION: trigger_checkpoint
```

If there's a problem requiring intervention:
```
STATUS: escalate
REASON: [what's wrong]
AFFECTED: [which agents/tasks]
SEVERITY: [low/medium/high]
RECOMMENDED_ACTION: [restart/reassign/abort/synthesize/escalate_to_human]
```

Be concise. This runs every 30-60 seconds.
"""


def log_check(status: str, notes: str) -> None:
    """Append to watcher log."""
    timestamp = datetime.now().isoformat()
    entry = f"\n## [{timestamp}]\n**Status:** {status}\n**Notes:** {notes}\n"

    COORDINATION_DIR.mkdir(parents=True, exist_ok=True)
    with open(WATCHER_LOG, "a", encoding="utf-8") as f:
        f.write(entry)


def main():
    """
    Main entry point.

    This script is meant to be called BY a Task agent, not to spawn one.
    The launcher spawns a Haiku Task agent that runs this analysis.

    For direct testing, this just prints what would be sent to the agent.
    """
    state = gather_state()
    prompt = get_haiku_prompt(state)

    print("=" * 60)
    print("HAIKU WATCHER - State Gathered")
    print("=" * 60)
    print(f"\nState summary:")
    print(f"  - Blackboard agents: {len(state['blackboard'].get('agents', {}))}")
    print(f"  - Agent files: {len(state['agent_files'])}")
    print(f"  - Recent activity: {len(state['recent_activity'])}")
    print(f"\nPrompt for Haiku agent ({len(prompt)} chars):")
    print("-" * 40)
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print("-" * 40)
    print("\nTo actually run this, use the Task tool with model='haiku'")
    print("and pass the gathered state + prompt.")

    return state, prompt


if __name__ == "__main__":
    main()
