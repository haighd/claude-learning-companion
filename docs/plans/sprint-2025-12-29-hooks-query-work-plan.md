# Sprint 2025-12-29: hooks-query Group Work Plan

**Group**: hooks-query
**Specialist Agent**: python-pro
**Worktree**: `/Users/danhaight/.claude/clc-worktrees/sprint-2025-12-29-hooks-query`
**Branch**: `group/hooks-query`
**Status**: Planning Complete

---

## Assigned Issues (5 total, 12 effort points)

| Issue # | Title | Priority | Effort |
|---------|-------|----------|--------|
| #63 | SessionStart hook for automatic CLC context loading | HIGH | MEDIUM |
| #65 | Progressive disclosure in query.py | HIGH | HIGH |
| #66 | PreCompact hook for context preservation | MEDIUM | LOW |
| #71 | Subagent learning-before-summary pattern | HIGH | MEDIUM |
| #74 | /clear strategy automation | HIGH | LOW |

---

## Implementation Order

**Key Dependency Chain:**
```
#65 (Progressive Disclosure) --> #63 (SessionStart) --> #74 (/clear)
```

**Independent Issues** (can be parallelized):
- #66 (PreCompact)
- #71 (SubagentStop)

---

## File Impact Analysis

| File Path | Change Type | Issue # | Risk |
|-----------|-------------|---------|------|
| `query/progressive.py` | CREATE | #65 | Low |
| `query/query.py` | MODIFY | #65 | Medium (backward compat) |
| `hooks/session_start_loader.py` | MODIFY | #63, #74 | Low (exists) |
| `hooks/pre_compact.py` | MODIFY | #66 | Low (exists) |
| `hooks/learning-loop/post_tool_learning.py` | MODIFY | #71 | Medium |
| `hooks/shared/context_health.py` | CREATE | #74 | Low |
| `hooks/shared/learning_capture.py` | CREATE | #71 | Low |
| `~/.claude/settings.json` | VERIFY | #63, #66 | Medium (shared) |
| `CLAUDE.md` | MODIFY | #63 | Low (coordinate with skills-agents) |

---

## 4-Phase Implementation Plan

### Phase 1: Progressive Disclosure Foundation (Issue #65)
1. Create `query/progressive.py` with `ProgressiveQuery` class
   - Tier 1: `get_metadata()` (~50 tokens - rule names only)
   - Tier 2: `get_full_rule(rule_id)` (lazy load)
   - Tier 3: `get_domain_context(domain)` (on-demand)
2. Refactor `build_context()` in query.py
3. Add caching with `functools.lru_cache`
4. Target: 60% token reduction

### Phase 2: Session Automation (Issue #63, #74)
1. Enhance `session_start_loader.py` to use progressive query
2. Create `hooks/shared/context_health.py` for /clear suggestions
3. Add context freshness checks (>30K tokens, task switch, corrections)
4. Update CLAUDE.md to remove manual query requirement

### Phase 3: Context Preservation (Issue #66)
1. Enhance `pre_compact.py` with auto-restore mechanism
2. Store restore hints in checkpoint metadata
3. Add restore logic to SessionStart hook
4. Coordinate checkpoint format with infra-commands (#73)

### Phase 4: Learning Loop (Issue #71)
1. Enhance `post_tool_learning.py` for learning-before-summary
2. Create `learning_capture.py` utility
3. Generate `learning_refs` list before task completion
4. Store refs in workflow metadata for dashboard linking

---

## External Dependencies

| Our Issue | Depends On | Source Group | Risk |
|-----------|------------|--------------|------|
| #66 | #73 (checkpoint pattern) | infra-commands | Medium |
| #63 | #64 (CLAUDE.md optimization) | skills-agents | Low |

---

## Success Criteria

- [ ] #65: Metadata-only query returns <100 tokens
- [ ] #65: 60% reduction in startup tokens (measured)
- [ ] #63: Session starts without manual CLC query
- [ ] #66: Context survives compaction (restore works)
- [ ] #71: learning_refs appear in TaskOutput metadata
- [ ] #74: /clear suggestion triggers at 30K tokens
