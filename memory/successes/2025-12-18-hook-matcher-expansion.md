# Success: Hook Matcher Expansion for Full Tool Coverage

**Date**: 2025-12-18
**Domain**: hooks, learning-loop

## What Worked

Identified and fixed a configuration gap where the learning-loop hooks were only matching `Task|TaskOutput` tools, despite PR #9 having extended the hook code to handle Bash, MCP, WebFetch, and file operations.

### Root Cause

The `~/.claude/settings.json` matcher pattern was never updated when PR #9 added new tool handlers:
- Hook code supported: Task, TaskOutput, Bash, MCP, WebFetch, WebSearch, Read, Edit, Write, Glob, Grep
- Matcher pattern only included: `Task|TaskOutput`

This caused a 3+ hour tracking gap (08:27 AM to 11:36 AM EST) during unrelated PR work.

### The Fix

Updated both PreToolUse and PostToolUse matchers in `~/.claude/settings.json`:
```json
// Before
"matcher": "Task|TaskOutput"

// After
"matcher": "Task|TaskOutput|Bash|mcp__.*|WebFetch|WebSearch|Read|Edit|Write|Glob|Grep"
```

## Why It Worked

1. **Configuration vs Code**: The hook code was correct, but Claude Code's hook system requires explicit matcher patterns in settings.json
2. **Regex matching**: Used `mcp__.*` to capture all MCP server tools dynamically
3. **Smart filtering preserved**: The hook code already skips trivial commands (echo, ls, pwd, etc.) unless they fail

## Validation

- Before fix: Gap in workflow_runs from 08:27 to 11:36 (3 hours)
- After fix (session restart required):
  - 7 new Bash workflow runs (2870-2876)
  - 4 new file operation trails (1186-1189)
  - All tool types now captured

## Transferable Heuristic

> When extending hook functionality to new tool types, update BOTH the hook code AND the settings.json matcher pattern. Claude Code caches settings at startup, so a session restart is required for matcher changes to take effect.

## Key Insight

The mismatch between code capabilities and configuration is a common failure mode. When adding new functionality to hooks:
1. Update the handler code
2. Update the matcher pattern
3. Restart Claude Code session
4. Verify with test commands

## Related

- PR #9: Extended hook code for Bash/MCP/WebFetch
- PR #11: Timezone display fix (unrelated, but exposed the gap)
