#!/usr/bin/env python3
"""
PreClear Checkpoint Hook: Preserve context before /clear command.

Triggers before /clear to:
1. Analyze session state for critical context
2. Save checkpoint with recoverable state
3. Provide guidance on what to preserve

GitHub Issue: #74
Implementation Date: December 29, 2025
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_checkpoint_dir() -> Path:
    checkpoint_dir = Path.home() / ".claude" / "clc" / "checkpoints" / "pre-clear"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return checkpoint_dir


def analyze_session_state(conversation: str) -> dict:
    """Analyze session for critical content that would be lost."""
    analysis = {
        'has_uncommitted_code': False,
        'has_pending_decisions': False,
        'has_active_debugging': False,
        'has_unrecorded_learnings': False,
        'modified_files': [],
        'criticality': 'low',
        'criticality_confidence': 0.0  # 0.0-1.0 confidence in criticality assessment
    }

    lines = conversation.split('\n') if conversation else []
    match_counts = {'uncommitted': 0, 'decisions': 0, 'debugging': 0, 'learnings': 0}

    # Detect uncommitted changes - heuristic approach
    # Note: May have false positives (e.g., discussions about git).
    # This is intentional - we prefer to warn on false positives rather
    # than miss real uncommitted changes before a /clear command.
    uncommitted_patterns = ['git add', 'modified:', 'staged:', 'uncommitted']
    for line in lines:
        if any(p in line.lower() for p in uncommitted_patterns):
            match_counts['uncommitted'] += 1
            analysis['has_uncommitted_code'] = True

    # Detect pending decisions
    decision_patterns = ['should we', 'what do you think', 'decision:', 'need to decide']
    for line in lines:
        if any(p in line.lower() for p in decision_patterns):
            match_counts['decisions'] += 1
            analysis['has_pending_decisions'] = True

    # Detect debugging
    debug_patterns = ['error:', 'exception:', 'traceback', 'debugging']
    for line in lines:
        if any(p in line.lower() for p in debug_patterns):
            match_counts['debugging'] += 1
            analysis['has_active_debugging'] = True

    # Detect unrecorded learnings
    learning_patterns = ['found that', 'discovered', 'realized', 'learned']
    for line in lines:
        if any(p in line.lower() for p in learning_patterns):
            match_counts['learnings'] += 1
            analysis['has_unrecorded_learnings'] = True

    # Calculate criticality
    if analysis['has_uncommitted_code'] or analysis['has_active_debugging']:
        analysis['criticality'] = 'high'
    elif analysis['has_pending_decisions'] or analysis['has_unrecorded_learnings']:
        analysis['criticality'] = 'medium'

    # Calculate confidence in criticality assessment based on match counts
    # More matches = higher confidence this isn't a false positive
    total_matches = sum(match_counts.values())
    if total_matches == 0:
        analysis['criticality_confidence'] = 1.0  # High confidence in "nothing found"
    elif total_matches == 1:
        analysis['criticality_confidence'] = 0.5  # Single match could be false positive
    elif total_matches <= 3:
        analysis['criticality_confidence'] = 0.7  # Few matches - moderate confidence
    else:
        analysis['criticality_confidence'] = 0.9  # Many matches - high confidence

    analysis['match_counts'] = match_counts
    return analysis


def save_checkpoint(conversation: str, analysis: dict, session_id: str) -> str:
    checkpoint_dir = get_checkpoint_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    checkpoint_file = checkpoint_dir / f"{timestamp}.json"

    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "trigger": "pre_clear",
        "analysis": analysis,
        "context_summary": conversation[:5000] if conversation else ""
    }

    with open(checkpoint_file, "w") as f:
        json.dump(data, f, indent=2)

    latest = checkpoint_dir / "latest.json"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(checkpoint_file.name)

    return str(checkpoint_file)


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        hook_input = {}

    conversation = hook_input.get('conversation', '')
    if isinstance(conversation, list):
        conversation = "\n".join(str(m) for m in conversation)

    session_id = os.environ.get('CLAUDE_SESSION_ID', 'unknown')
    analysis = analyze_session_state(conversation)
    checkpoint_file = save_checkpoint(conversation, analysis, session_id)

    guidance = []
    if analysis['criticality'] != 'low':
        guidance.append(f"# Pre-Clear Warning: {analysis['criticality'].upper()} criticality")
        if analysis['has_uncommitted_code']:
            guidance.append("- Uncommitted code detected - consider committing first")
        if analysis['has_active_debugging']:
            guidance.append("- Active debugging session - document findings")
        if analysis['has_pending_decisions']:
            guidance.append("- Pending decisions - record before clearing")
        if analysis['has_unrecorded_learnings']:
            guidance.append("- Learnings detected - run /capture-learnings")

    # Build output message
    checkpoint_msg = f"[CLC] Checkpoint saved: {checkpoint_file}"
    output_msg = "\n".join(guidance) + "\n" + checkpoint_msg if guidance else checkpoint_msg

    result = {
        "continue": True,
        "outputToStdout": output_msg,
        "metadata": {
            "checkpoint_file": checkpoint_file,
            "criticality": analysis['criticality'],
            "criticality_confidence": analysis['criticality_confidence'],
            "match_counts": analysis.get('match_counts', {}),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
