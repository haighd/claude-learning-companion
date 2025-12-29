#!/usr/bin/env python3
"""
Subagent Learning Hook: Ensure learnings are recorded before summary.

Implements the "learning-before-summary" pattern for subagents:
1. Intercepts subagent completion
2. Extracts learnings from work performed
3. Records to CLC before allowing summary return

GitHub Issue: #71
Implementation Date: December 29, 2025
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def get_clc_path() -> Path:
    return Path.home() / ".claude" / "clc"


def extract_learnings(work_context: dict) -> list:
    """Extract learnings from subagent work context."""
    learnings = []

    # Extract from errors/resolutions
    for error in work_context.get('errors', []):
        if error.get('resolved'):
            learnings.append({
                'type': 'failure',
                'title': f"Resolved: {error.get('message', 'Unknown')[:50]}",
                'summary': error.get('resolution', ''),
                'domain': work_context.get('domain', 'general'),
                'source': 'subagent-hook'
            })

    # Extract from decisions
    for decision in work_context.get('decisions', []):
        learnings.append({
            'type': 'observation',
            'title': f"Decision: {decision.get('what', 'Unknown')[:50]}",
            'summary': decision.get('rationale', ''),
            'domain': work_context.get('domain', 'general'),
            'source': 'subagent-hook'
        })

    # Extract from patterns discovered
    for pattern in work_context.get('patterns', []):
        learnings.append({
            'type': 'heuristic',
            'title': pattern.get('name', 'Unnamed pattern'),
            'summary': pattern.get('description', ''),
            'domain': work_context.get('domain', 'general'),
            'source': 'subagent-hook'
        })

    return learnings


def record_learnings(learnings: list) -> dict:
    """Record learnings to CLC memory."""
    clc_path = get_clc_path()
    learnings_dir = clc_path / "memory" / "learnings" / "subagent"
    learnings_dir.mkdir(parents=True, exist_ok=True)

    recorded = []
    for learning in learnings:
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"{timestamp}-{learning['type']}.json"
        filepath = learnings_dir / filename

        learning['recorded_at'] = datetime.now().isoformat()
        with open(filepath, 'w') as f:
            json.dump(learning, f, indent=2)
        recorded.append(learning['title'])

    return {'recorded_count': len(recorded), 'recorded': recorded}


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        hook_input = {}

    work_context = hook_input.get('work_context', {})
    summary = hook_input.get('summary', '')
    agent_id = hook_input.get('agent_id', 'unknown')

    # Extract and record learnings
    learnings = extract_learnings(work_context)
    record_result = record_learnings(learnings)

    # Enhance summary if learnings were recorded
    enhanced_summary = summary
    if learnings:
        enhanced_summary += f"\n\n[CLC] Recorded {record_result['recorded_count']} learnings"

    result = {
        "continue": True,
        "modifiedSummary": enhanced_summary,
        "metadata": {
            "agent_id": agent_id,
            "learnings_extracted": len(learnings),
            "learnings_recorded": record_result['recorded_count'],
            "timestamp": datetime.now().isoformat()
        }
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
