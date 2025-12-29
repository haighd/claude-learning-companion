# Sprint 2025-12-29: infra-commands Group Work Plan

**Group**: infra-commands
**Specialist Agent**: cli-developer
**Worktree**: `/Users/danhaight/.claude/clc-worktrees/sprint-2025-12-29-infra-commands`
**Branch**: `group/infra-commands`
**Status**: Planning Complete

---

## Assigned Issues (4 total, 6 effort points)

| # | Title | Priority | Effort |
|---|-------|----------|--------|
| 58 | project.md wrong scope | HIGH | LOW |
| 59 | /resume doesn't find project.md | HIGH | LOW |
| 72 | MCP server auditor script | MEDIUM | LOW |
| 73 | Checkpoint pattern for recovery | HIGH | MEDIUM |

---

## File Impact Analysis

| File Path | Change Type | Shared? | Risk |
|-----------|-------------|---------|------|
| `~/.claude/commands/checkpoint.md` | MODIFY | No | Low |
| `~/.claude/commands/resume.md` | MODIFY | No | Low |
| `~/.claude/clc/scripts/audit-mcp-servers.sh` | CREATE | No | Low |
| `~/.claude/clc/checkpoints/` | MODIFY | Yes | Medium |
| `~/.claude/clc/scripts/lib/checkpoint_utils.py` | CREATE | Yes | Medium |

---

## 3-Phase Implementation Plan

### Phase 1: Foundation (Issues #58, #59)
1. Fix project.md scope (#58)
   - Add explicit project-local path instruction to `/checkpoint`
   - Priority: `$PWD/project.md` > `.claude/project.md` > NEVER global
2. Add project.md to resume sources (#59)
   - Add project.md as first/highest priority checkpoint source
   - Update auto-selection logic

### Phase 2: Checkpoint Infrastructure (#73)
1. Define checkpoint structure:
   ```
   checkpoints/
   ├── index.json
   ├── pre-compact/
   ├── manual/
   ├── session-end/
   └── latest.json
   ```
2. Create `checkpoint_utils.py` library
3. Update existing PreCompact hook to use shared utilities
4. Implement resume from checkpoint

### Phase 3: MCP Auditor Script (#72)
1. Create `scripts/audit-mcp-servers.sh`
2. Parse MCP config from known locations
3. Output formatted report with token estimates

---

## Coordination with hooks-query

**Critical**: Issue #73 is a dependency for hooks-query's #66 (PreCompact hook)

**Interface Contract**:
1. Checkpoint files in `checkpoints/{trigger_type}/`
2. Use shared `checkpoint_utils.py`
3. JSON schema v2.0

---

## Success Criteria

- [ ] `/checkpoint` creates project.md locally
- [ ] `/resume` finds project.md first
- [ ] Checkpoint structure created
- [ ] `checkpoint_utils.py` functional
- [ ] `audit-mcp-servers.sh` produces report
- [ ] hooks-query group unblocked
