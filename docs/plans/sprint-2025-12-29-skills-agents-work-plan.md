# Sprint 2025-12-29: skills-agents Group Work Plan

**Group**: skills-agents
**Specialist Agent**: python-pro
**Worktree**: `/Users/danhaight/.claude/clc-worktrees/sprint-2025-12-29-skills-agents`
**Branch**: `group/skills-agents`
**Status**: Planning Complete

---

## Assigned Issues (3 total, 7 effort points)

| Issue | Title | Priority | Effort |
|-------|-------|----------|--------|
| #64 | Optimize CLAUDE.md to 100-200 lines | HIGH | LOW |
| #68 | Agent personas to native subagents format | HIGH | MEDIUM |
| #69 | Native skills as interface to CLC backend | HIGH | MEDIUM |

---

## Current State Analysis

### CLAUDE.md Files (Issue #64)

| File | Current Lines | Target Lines |
|------|---------------|--------------|
| `~/.claude/CLAUDE.md` | 341 | 100-200 |
| `~/.claude/clc/CLAUDE.md` | 358 | 100-200 |
| **Total** | **699** | **200-400** |

### Agent Personas (Issue #68)

**Current**: `~/.claude/clc/agents/*/personality.md`
**Target**: `~/.claude/agents/clc-{persona}/AGENT.md`

### Skills Interface (Issue #69)

| Skill | Backend | Trigger Phrases |
|-------|---------|-----------------|
| clc-query | `query.py` | "check clc", "query clc" |
| clc-record | `record-*.sh` | "record failure", "record heuristic" |
| clc-escalate | `ceo-inbox/` | "escalate to ceo" |

---

## File Impact Analysis

| File Path | Change Type | Risk |
|-----------|-------------|------|
| `~/.claude/CLAUDE.md` | MODIFY | Medium |
| `~/.claude/clc/CLAUDE.md` | MODIFY | Medium |
| `~/.claude/rules/*.md` | CREATE | Low |
| `~/.claude/agents/clc-*/AGENT.md` | CREATE | Low |
| `~/.claude/skills/clc-*/SKILL.md` | CREATE | Low |

---

## 3-Phase Implementation Plan

### Phase 1: CLAUDE.md Optimization (#64)
1. Create rules directory structure (`~/.claude/rules/`)
2. Extract content to rule files:
   - PR workflow -> `rules/pr-workflow.md`
   - CLC protocol -> `rules/clc-protocol.md`
   - Agent coordination -> `rules/agent-coordination.md`
3. Rewrite CLAUDE.md files (100-200 lines each)

### Phase 2: Agent Personas Migration (#68)
1. Create native agent directories
2. Convert persona files to AGENT.md format with YAML frontmatter
3. Add deprecation notice to old files

### Phase 3: Native Skills Interface (#69)
1. Create skill directories (`~/.claude/skills/clc-*/`)
2. Create clc-query skill (wraps query.py)
3. Create clc-record skill (wraps record-*.sh)
4. Create clc-escalate skill (wraps CEO inbox)

---

## External Dependencies

| Dependency | Group | Impact |
|------------|-------|--------|
| `query.py` progressive disclosure | hooks-query | Can work in parallel |

---

## Success Criteria

- [ ] CLAUDE.md files reduced to 100-200 lines each
- [ ] 4 CLC agents created in native format
- [ ] 3 CLC skills created and functional
- [ ] 62% token reduction verified
