# Auto-Claude Integration

This guide explains how to use [Auto-Claude](https://github.com/AndyMik90/Auto-Claude) alongside CLC.

## Overview

| System | Purpose | Agents |
|--------|---------|--------|
| **CLC** | Knowledge retention | Advisory (perspectives) |
| **Auto-Claude** | Autonomous coding | Executive (do the work) |

They're complementary: CLC remembers, Auto-Claude executes.

## Compatibility

**No conflicts.** They use entirely separate file paths:

| Resource | CLC | Auto-Claude |
|----------|-----|-------------|
| Config | Global: `~/.claude/CLAUDE.md` (project-local `.claude/` also supported) | `./CLAUDE.md` |
| Data | `~/.claude/clc/` | `./specs/`, `./.worktrees/` |
| Hooks | Global hooks | None (Python orchestration) |

## Installation Options

### Option A: Subdirectory (Recommended)

```bash
cd ~/Projects/my-project
git clone https://github.com/AndyMik90/Auto-Claude.git .auto-claude
cd .auto-claude
uv venv && uv pip install -r requirements.txt
cp .env.example .env
claude setup-token

# Update .gitignore (idempotent - only add if not present)
cd ..
for item in .auto-claude/ .worktrees/ specs/; do
    grep -qxF "$item" .gitignore 2>/dev/null || echo "$item" >> .gitignore
done
```

### Option B: Root Installation

See [full integration guide](https://github.com/haighd/claude-learning-companion/blob/main/docs/auto-claude-integration-guide.md).

## Potential Issues

### 1. CLAUDE.md Override

Project-local CLAUDE.md overrides global. Add CLC integration:

```markdown
## CLC Integration
Before any task, query accumulated knowledge:
```bash
python ~/.claude/clc/query/query.py --context
```
Apply relevant golden rules and heuristics.
```

### 2. Hook Noise

CLC hooks capture Auto-Claude's builds (noisy). Add exclusion:

```python
# In pre_tool_learning.py
import os
import sys
from pathlib import Path

cwd = Path(os.getcwd())
auto_claude_markers = [cwd / ".auto-claude", cwd / "auto-claude-framework"]
in_worktree = (cwd / ".git").is_file()
if any(marker.exists() for marker in auto_claude_markers) or in_worktree:
    sys.exit(0)
```

### 3. Knowledge Gap

Auto-Claude doesn't query CLC. Manually inject context into specs.

## Hybrid Workflow

```
1. PLANNING      → Query CLC for relevant heuristics
2. SPEC CREATION → Inject CLC learnings into Auto-Claude spec
3. BUILD         → Let Auto-Claude agents implement
4. REVIEW        → Use your normal PR workflow (/gemini review)
5. CAPTURE       → Record learnings back to CLC
```

## Task Routing

| Task Type | Use |
|-----------|-----|
| Quick fix (< 30 min) | CLC + manual |
| Complex feature with clear spec | Auto-Claude |
| Unclear requirements | CLC to clarify first |

## References

These links point to the latest version of the documentation on the default branch:

- [Full Integration Guide](https://github.com/haighd/claude-learning-companion/blob/main/docs/auto-claude-integration-guide.md)
- [Technical Spec](https://github.com/haighd/claude-learning-companion/blob/main/docs/implementation-plans/auto-claude-integration-spec.md)
- [GitHub Issue #14](https://github.com/haighd/claude-learning-companion/issues/14)
