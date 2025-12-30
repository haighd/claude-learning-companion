#!/usr/bin/env python3
"""
PreCompact Hook: Save critical context before auto-compaction.

This hook triggers when Claude Code is about to compact the context window.
It preserves critical information that would otherwise be lost:
1. Key decisions made this session
2. Active task state
3. Files being modified
4. Pending questions
5. Learning references from session

The goal is to enable "resume from checkpoint" after compaction.

Implementation Date: December 29, 2025
GitHub Issue: #66
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Characters to strip from extracted file paths
# These are common quoting/bracketing chars that surround paths in text:
# - Quotes: ` ' "
# - Brackets: [ ] ( ) { } < >
# - Punctuation: , |
# Note: Order doesn't matter for str.strip(). The double quote is included
# directly in this single-quoted string; the single quote is escaped.
PATH_STRIP_CHARS = '`,"\'\"][(){}|<>'


def get_clc_path() -> Path:
    """Get the CLC installation path."""
    return Path.home() / ".claude" / "clc"


def get_checkpoint_dir() -> Path:
    """Get the checkpoint directory, creating if needed."""
    checkpoint_dir = get_clc_path() / "checkpoints" / "pre-compact"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return checkpoint_dir


def extract_decisions(conversation_context: str) -> list:
    """
    Extract key decisions from conversation context.

    Looks for patterns indicating decisions were made:
    - "decided to..."
    - "will use..."
    - "approach: ..."
    - "chosen: ..."
    """
    decisions = []
    decision_patterns = [
        "decided to",
        "will use",
        "chosen approach",
        "selected",
        "going with",
        "using the",
        "approach:",
        "resolution:",
    ]

    lines = conversation_context.split("\n") if conversation_context else []
    for line in lines:
        line_lower = line.lower()
        for pattern in decision_patterns:
            if pattern in line_lower:
                decisions.append(line.strip()[:200])  # Limit length
                break

    return decisions[:10]  # Limit to 10 decisions


def extract_active_tasks(conversation_context: str) -> list:
    """
    Extract active tasks from conversation context.

    Looks for task indicators:
    - "working on..."
    - "implementing..."
    - "fixing..."
    - Todo items
    """
    tasks = []
    task_patterns = [
        "working on",
        "implementing",
        "fixing",
        "adding",
        "creating",
        "updating",
        "[ ]",  # Unchecked todo
        "in_progress",
    ]

    lines = conversation_context.split("\n") if conversation_context else []
    for line in lines:
        line_lower = line.lower()
        for pattern in task_patterns:
            if pattern in line_lower:
                tasks.append(line.strip()[:200])
                break

    return tasks[:10]


def extract_modified_files(conversation_context: str) -> list:
    """
    Extract files being modified from conversation context.

    Looks for file path patterns. Note: This is heuristic-based and may have
    false positives (e.g., paths in string literals). The extracted paths are
    used only for checkpoint context, not for critical operations.
    """
    files = set()
    file_extensions = (".py", ".ts", ".js", ".md", ".json", ".yaml", ".yml", ".sh")

    lines = conversation_context.split("\n") if conversation_context else []
    for line in lines:
        words = line.split()
        for word in words:
            # Check if a word looks like a file path with a valid extension
            if "/" in word and word.strip(PATH_STRIP_CHARS).endswith(file_extensions):
                path = word.strip(PATH_STRIP_CHARS)
                # Basic validation to reduce false positives
                if path.startswith(("/", "./", "~/")) or path.count("/") >= 2:
                    files.add(path)

    return list(files)[:20]


def save_checkpoint(checkpoint_data: dict) -> str:
    """
    Save checkpoint to file.

    Returns the checkpoint file path.
    """
    checkpoint_dir = get_checkpoint_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    checkpoint_file = checkpoint_dir / f"{timestamp}.json"

    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(checkpoint_data, f, indent=2, default=str)

    # Update "latest" symlink
    latest_link = checkpoint_dir / "latest.json"
    if latest_link.exists():
        latest_link.unlink()
    latest_link.symlink_to(checkpoint_file.name)

    return str(checkpoint_file)


def main():
    """
    Main hook entry point.

    Reads hook input from stdin, extracts critical context, saves checkpoint.
    """
    # Read hook input
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        hook_input = {}

    # Get conversation context from hook input
    conversation_context = hook_input.get("conversation", "")
    if isinstance(conversation_context, list):
        conversation_context = "\n".join(str(m) for m in conversation_context)

    # Get environment info
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

    # Extract critical information
    decisions = extract_decisions(conversation_context)
    active_tasks = extract_active_tasks(conversation_context)
    modified_files = extract_modified_files(conversation_context)

    # Build checkpoint data
    checkpoint_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "project_dir": project_dir,
        "trigger": "pre_compact",
        "decisions": decisions,
        "active_tasks": active_tasks,
        "modified_files": modified_files,
        "context_summary": conversation_context[:2000] if conversation_context else "",
        "metadata": {
            "decisions_count": len(decisions),
            "tasks_count": len(active_tasks),
            "files_count": len(modified_files),
        }
    }

    # Save checkpoint
    checkpoint_file = save_checkpoint(checkpoint_data)

    # Output hook result
    result = {
        "continue": True,  # Always continue - checkpointing is non-blocking
        "outputToStdout": f"[CLC] Pre-compact checkpoint saved: {checkpoint_file}",
        "metadata": {
            "checkpoint_file": checkpoint_file,
            "decisions_saved": len(decisions),
            "tasks_saved": len(active_tasks),
            "files_tracked": len(modified_files),
        }
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
