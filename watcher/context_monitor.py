#!/usr/bin/env python3
"""
Context Monitor - Estimates context window utilization.

This module tracks coarse-grained interaction metrics (message count, file
reads/edits, tool calls, subagent spawns) and applies fixed heuristic
weights to estimate how much of the model's context window is likely
to be in use. Because the underlying token budget API is not exposed,
the estimation is intentionally conservative so that checkpoints are
triggered early rather than late.

The core flow is:
  1. `load_session_state()` reads session metrics from
     `~/.claude/hooks/learning-loop/session-state.json`, falling back to
     `get_default_context_metrics()` if missing or invalid.
  2. `estimate_context_usage(metrics)` multiplies each metric by the
     corresponding entry in `WEIGHTS` and sums the results to produce an
     estimated usage fraction in the range 0.0–1.0.
  3. `get_context_status()` combines the estimated usage with checkpoint
     metadata (last checkpoint time, cooldown) and returns a status dict
     that higher-level tooling can use to decide whether to create a
     checkpoint.
  4. `reset_context_metrics()` is called by checkpoint hooks to zero out
     the counters and record the time of the last checkpoint.

Heuristic approach
-------------------
The `WEIGHTS` dictionary encodes an approximate fraction of the total
context window consumed by each operation. For example, with an assumed
~200k-token window, a `message_count` weight of 0.01 implies that each
message is treated as if it consumes roughly 1% of the window. This
approach favors early checkpointing at the cost of underutilizing the
theoretical maximum context capacity, which is safer for long sessions.

Usage examples
--------------
CLI:
    # Show current estimated usage and checkpoint status
    python context_monitor.py --status

    # Reset metrics after creating a manual checkpoint
    python context_monitor.py --reset

Programmatic:
    from watcher import context_monitor

    status = context_monitor.get_context_status()
    if status["should_checkpoint"]:
        # Trigger your checkpoint logic here
        ...
        context_monitor.reset_context_metrics()
Part of Phase 2: Proactive Watcher Monitoring for Context Management.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Paths
SESSION_STATE_PATH = Path.home() / ".claude" / "hooks" / "learning-loop" / "session-state.json"
CHECKPOINT_INDEX_PATH = Path.home() / ".claude" / "clc" / "checkpoints" / "index.json"

# Heuristic weights (conservative estimates)
# Assume a total context window of ~200k tokens; values below are
# fractions of total context consumed per operation (e.g., 0.01 = 1%).
WEIGHTS = {
    'message_count': 0.01,       # ~1% of 200k context per message (~2000 tokens implied)
    'file_reads': 0.02,          # ~2% of 200k context per file read (~4000 tokens implied)
    'file_edits': 0.015,         # ~1.5% of 200k context per edit (~3000 tokens implied)
    'tool_calls': 0.005,         # ~0.5% of 200k context per tool call (~1000 tokens implied)
    'subagent_spawns': 0.05,     # ~5% of 200k context per subagent (~10000 tokens implied)
}

# Thresholds
CHECKPOINT_THRESHOLD = 0.60  # Trigger at 60%
COOLDOWN_SECONDS = 600       # 10 minute cooldown


def load_session_state() -> Dict[str, Any]:
    """Load current session context metrics."""
    if not SESSION_STATE_PATH.exists():
        # Wrap default metrics in the expected session state structure
        return {'context_metrics': get_default_context_metrics()}

    try:
        state = json.loads(SESSION_STATE_PATH.read_text())
        # Ensure context metrics exist
        if 'context_metrics' not in state:
            state['context_metrics'] = get_default_context_metrics()
        return state
    except (json.JSONDecodeError, OSError):
        import traceback
        sys.stderr.write(f"[context_monitor] Error loading session state:\n{traceback.format_exc()}\n")
        # On error, also return wrapped default metrics
        return {'context_metrics': get_default_context_metrics()}


def get_default_context_metrics() -> Dict[str, Any]:
    """Return default context metrics."""
    return {
        'message_count': 0,
        'file_reads': 0,
        'file_edits': 0,
        'tool_calls': 0,
        'subagent_spawns': 0,
        'last_checkpoint_time': None,
    }


def estimate_context_usage(metrics: Dict[str, Any]) -> float:
    """
    Estimate context usage as percentage (0.0 - 1.0).

    Uses heuristic weights based on typical token consumption.
    Conservative to trigger checkpoints early.
    """
    usage = sum(
        metrics.get(metric, 0) * weight
        for metric, weight in WEIGHTS.items()
    )
    return min(usage, 1.0)


def get_last_checkpoint_time() -> Optional[str]:
    """Get timestamp of most recent checkpoint for current project."""
    if not CHECKPOINT_INDEX_PATH.exists():
        return None

    try:
        index = json.loads(CHECKPOINT_INDEX_PATH.read_text())
        checkpoints = index.get('checkpoints', [])
        if checkpoints:
            # Get most recent, filtering out empty 'created' values
            valid_timestamps = [cp.get('created', '') for cp in checkpoints if cp.get('created')]
            if valid_timestamps:
                return max(valid_timestamps)
    except (json.JSONDecodeError, OSError) as e:
        import traceback
        sys.stderr.write(f"[context_monitor] Error reading checkpoint index:\n{traceback.format_exc()}\n")
        # Fall through to check session state below

    # Also check session state for last_checkpoint_time
    state = load_session_state()
    return state.get('context_metrics', {}).get('last_checkpoint_time')


def check_cooldown(last_checkpoint_time: Optional[str]) -> bool:
    """Check if we're still in cooldown period."""
    if not last_checkpoint_time or last_checkpoint_time == "":
        return False  # No cooldown if never checkpointed or empty timestamp

    try:
        # Handle both Z suffix and +00:00 format in a single, safe operation
        normalized_time = last_checkpoint_time.replace('Z', '+00:00')
        last_cp = datetime.fromisoformat(normalized_time)

        # Ensure timezone aware
        if last_cp.tzinfo is None:
            last_cp = last_cp.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        elapsed = (now - last_cp).total_seconds()
        return elapsed < COOLDOWN_SECONDS
    except (ValueError, TypeError) as e:
        import traceback
        sys.stderr.write(f"[context_monitor] Error parsing checkpoint time:\n{traceback.format_exc()}\n")
        return False


def get_context_status() -> Dict[str, Any]:
    """
    Get current context status for watcher.

    Returns dict with:
        - estimated_usage: float 0.0-1.0
        - metrics: raw metric counts
        - should_checkpoint: bool
        - reason: str explaining status
        - in_cooldown: bool
    """
    state = load_session_state()
    metrics = state.get('context_metrics', {})

    usage = estimate_context_usage(metrics)
    last_cp = get_last_checkpoint_time()
    in_cooldown = check_cooldown(last_cp)

    should_checkpoint = usage >= CHECKPOINT_THRESHOLD and not in_cooldown

    if should_checkpoint:
        reason = f"Context at {usage*100:.0f}% (threshold: {CHECKPOINT_THRESHOLD*100:.0f}%)"
    elif in_cooldown:
        reason = f"Context at {usage*100:.0f}% but in cooldown period"
    else:
        reason = f"Context at {usage*100:.0f}% (below threshold)"

    return {
        'estimated_usage': usage,
        'metrics': metrics,
        'should_checkpoint': should_checkpoint,
        'reason': reason,
        'in_cooldown': in_cooldown,
        'last_checkpoint_time': last_cp,
    }


def reset_context_metrics():
    """Reset context metrics after checkpoint (called by checkpoint hooks)."""
    state = load_session_state()
    state['context_metrics'] = {
        'message_count': 0,
        'file_reads': 0,
        'file_edits': 0,
        'tool_calls': 0,
        'subagent_spawns': 0,
        'last_checkpoint_time': datetime.now(timezone.utc).isoformat(),
    }

    try:
        SESSION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SESSION_STATE_PATH.write_text(json.dumps(state, indent=2))
    except IOError as e:
        sys.stderr.write(f"[context_monitor] Error saving session state: {e}\n")


if __name__ == "__main__":
    # CLI for testing
    import argparse
    parser = argparse.ArgumentParser(description="Context Monitor CLI")
    parser.add_argument("--reset", action="store_true", help="Reset context metrics")
    parser.add_argument("--status", action="store_true", help="Show context status")
    args = parser.parse_args()

    if args.reset:
        reset_context_metrics()
        print("Context metrics reset.")
    else:
        status = get_context_status()
        print(json.dumps(status, indent=2, default=str))
