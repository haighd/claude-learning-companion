# PRD: Automated Context Window Management for Claude Code

---
title: "Automated Context Window Management"
status: draft
author: Dan Haight
created: 2025-12-20
last_updated: 2025-12-20
version: "1.0"
---

## Overview

### Problem Statement
Claude Code agents experience increased hallucination rates when context window utilization exceeds 60%. Currently, context management requires manual intervention via the `/checkpoint` command, which introduces several failure modes:

1. **Phantom checkpoints** - Agents claim to create checkpoints that don't actually exist
2. **Multi-agent blindspot** - Difficult to monitor context across multiple concurrent agents
3. **Quality loss with /compact** - Claude's native compaction loses critical context quality
4. **Autonomous operation gap** - No reliable way to preserve quality when user is away

### Opportunity
Implement a comprehensive, automated context management system that maintains context quality without manual intervention, enabling truly autonomous agent operation.

### Proposed Solution
A **hybrid three-layer system** combining:
1. **PreCompact Auto-Checkpoint** - Reactive: Intercept before compaction, save quality state
2. **Watcher Multi-Agent Monitor** - Proactive: Central monitoring across all running agents
3. **Context-Aware Task Batching** - Preventive: Break work into context-sized chunks

## Users & Stakeholders

### Target Users

#### Primary: Dan (Power User / Developer)
- **Who**: Runs multiple Claude Code agents in parallel
- **Needs**: Autonomous operation, quality preservation, minimal hallucination
- **Pain Points**: Manual checkpoint management, quality loss with /compact, multi-agent oversight burden

#### Secondary: CLC-Managed Agents
- **Who**: Claude Code agents spawned by the system
- **Needs**: Clear context, accurate state restoration, coordinated work
- **Pain Points**: Context pollution, phantom checkpoints, uncoordinated restarts

### Stakeholders
- **CLC System**: Needs reliable state for learning capture and coordination
- **Future Users**: Template for context management best practices

## User Journey

### Current State
```
User spawns agents → Agents work → Context grows →
User notices high utilization → Manual /checkpoint →
Sometimes phantom checkpoint → User must verify →
If user away: auto-compact runs → Quality degrades →
Hallucinations increase → Work quality suffers
```

### Future State
```
User spawns agents → Agents work →
Watcher monitors all agents → Context approaches 60% →
Auto-checkpoint triggered → High-quality state saved →
If compaction needed: PreCompact intercepts →
Quality checkpoint created → Compaction proceeds →
Agent resumes with clear context → Quality maintained
```

## Requirements

### Functional Requirements

#### Must Have (P0)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-001 | PreCompact hook intercepts before /compact runs | Hook fires, captures full context state before compaction |
| FR-002 | Auto-checkpoint creates verifiable checkpoint file | File exists on disk, contains all required state fields |
| FR-003 | Checkpoint quality matches manual /checkpoint | Same structure, same resumability, same context preservation |
| FR-004 | System works when user is away (autonomous) | No user intervention required for checkpoint/resume cycle |
| FR-005 | Phantom checkpoint prevention | Verification step confirms file creation before reporting success |

#### Should Have (P1)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-006 | Multi-agent watcher monitors all running agents | Single dashboard/log shows context status for all agents |
| FR-007 | Watcher triggers checkpoint at 60% threshold | Proactive checkpoint before context pressure builds |
| FR-008 | Context-aware task batching | Large tasks auto-split into context-sized chunks |
| FR-009 | Checkpoint counter tracks iterations | Clear lineage of checkpoint → work → checkpoint |
| FR-010 | Resume instructions auto-generated | Next session can pick up exactly where left off |

#### Nice to Have (P2)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-011 | Quality score comparison (checkpoint vs compact) | Metrics showing context quality before/after |
| FR-012 | Multi-agent orchestrated checkpointing | Coordinate checkpoint timing across agents to avoid conflicts |
| FR-013 | Checkpoint pruning (keep N most recent) | Automatic cleanup of old checkpoints |

### Non-Functional Requirements

| Category | Requirement | Target |
|----------|-------------|--------|
| Performance | PreCompact hook latency | < 2 seconds |
| Reliability | Checkpoint creation success rate | > 99% |
| Storage | Checkpoint file size | < 50KB per checkpoint |
| Monitoring | Watcher polling interval | Every 30 seconds |

## Scope

### In Scope
- PreCompact hook implementation for auto-checkpoint
- Watcher extension for multi-agent monitoring
- Context-aware task batching in coordinator
- Checkpoint verification system
- Resume instruction generation

### Out of Scope
- Claude Code API changes (working within current hook capabilities)
- Token budget API (not reliably exposed)
- Replacing /compact entirely (supplementing, not replacing)
- Cross-machine agent coordination (single machine focus)

### Dependencies
- Existing hooks infrastructure (`~/.claude/hooks/`)
- Watcher system (`~/.claude/clc/watcher/`)
- Coordinator system (`~/.claude/clc/coordinator/`)
- Checkpoint command (`~/.claude/commands/checkpoint.md`)

## Success Metrics

### Primary Metrics

| Metric | Baseline | Target | Stretch |
|--------|----------|--------|---------|
| Manual checkpoint interventions | 5-10/day | < 1/day | 0/day |
| Phantom checkpoint rate | ~10% | 0% | 0% |
| Post-checkpoint hallucination rate | Unmeasured | < 5% | < 2% |
| Context quality preservation | N/A | 90% of manual | 95% of manual |

### Secondary Metrics

| Metric | Target |
|--------|--------|
| Autonomous operation duration | 4+ hours without intervention |
| Multi-agent checkpoint coordination conflicts | 0 per session |

### Measurement Plan
- Track checkpoint events in CLC metrics table
- Compare work quality before/after checkpoints
- Monitor watcher alerts and interventions
- Log context utilization at checkpoint time

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PreCompact hook adds latency | M | L | Keep hook lightweight, async where possible |
| Checkpoint file corruption | L | H | Verify file integrity after write |
| Watcher misses context spike | M | M | Conservative 60% threshold, not 80% |
| Task batching splits work incorrectly | M | M | Allow manual override, learn from patterns |
| Disk space from checkpoints | L | L | Auto-prune, configurable retention |

## Open Questions

- [ ] Can PreCompact hook block/delay compaction, or only observe?
- [x] What's the exact structure needed for resume instructions? → **RESOLVED: Match existing checkpoint.md structure (What/Why/Where, Active Issues, Key Decisions, Next Steps)**
- [x] Should watcher use Haiku or local heuristics for monitoring? → **RESOLVED: Haiku API calls (more accurate, ~$0.001/check)**
- [ ] How to handle checkpoint during active file edits?

## Key Insight: Why /checkpoint > /compact

The existing `/checkpoint` command captures **structured semantic context**:

| Component | What It Captures | Why It Matters |
|-----------|------------------|----------------|
| What Changed | File:line references | Precise state restoration |
| Why Changed | Rationale for changes | Preserves intent |
| Active Issues | Current problem state | Context awareness |
| Key Decisions | Architectural choices | Prevents re-decisions |
| Next Steps | Task list | Clear direction |

**This is fundamentally different from `/compact`** which summarizes conversation text. Checkpoint preserves **work state and intent**, not dialogue summary. The auto-checkpoint must replicate this structure.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT MANAGEMENT SYSTEM                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LAYER 1: PREVENTIVE (Task Batching)                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Coordinator breaks work into context-sized chunks       │   │
│  │ Auto-checkpoint between batches                         │   │
│  │ Estimates token cost before task assignment             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  LAYER 2: PROACTIVE (Watcher Monitor)                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Haiku-tier monitoring every 30s across all agents       │   │
│  │ Triggers checkpoint at 60% utilization                  │   │
│  │ Coordinates multi-agent checkpoint timing               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  LAYER 3: REACTIVE (PreCompact Hook)                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Intercepts PreCompact event                             │   │
│  │ Saves high-quality checkpoint before compaction         │   │
│  │ Generates resume instructions                           │   │
│  │ Allows compaction to proceed                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  CHECKPOINT VERIFICATION                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Verify file exists after creation                       │   │
│  │ Validate required fields present                        │   │
│  │ Only report success after verification                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: PreCompact Auto-Checkpoint (P0)
- Implement PreCompact hook
- Auto-checkpoint on compaction
- Verification system
- Resume instruction generation

### Phase 2: Watcher Multi-Agent Monitor (P1)
- Extend watcher for multi-agent monitoring
- 60% threshold checkpoint trigger
- Coordination to prevent conflicts

### Phase 3: Context-Aware Task Batching (P1)
- Coordinator enhancement for token estimation
- Task splitting logic
- Inter-batch checkpoint automation

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `~/.claude/hooks/pre-compact-checkpoint.cjs` | Create | PreCompact auto-checkpoint hook |
| `~/.claude/clc/watcher/context_monitor.py` | Create | Multi-agent context monitoring |
| `~/.claude/clc/coordinator/task_batcher.py` | Create | Context-aware task batching |
| `~/.claude/clc/scripts/verify-checkpoint.sh` | Create | Checkpoint verification |
| `~/.claude/commands/checkpoint.md` | Modify | Add verification step |

## Appendix

### Related Documents
- CLC Watcher Architecture: `~/.claude/clc/watcher/`
- Hooks System: `~/.claude/hooks/`
- Coordinator System: `~/.claude/clc/coordinator/`
- Auto-Claude Integration Spec: `~/.claude/clc/docs/implementation-plans/auto-claude-integration-spec.md`

### Glossary
- **PreCompact**: Hook event fired before Claude Code runs context compaction
- **Checkpoint**: Saved state including context, progress, and resume instructions
- **Phantom Checkpoint**: Reported checkpoint that was never actually created
- **Watcher**: CLC's Haiku-tier monitoring system for agent oversight

### Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-20 | Dan Haight | Initial draft |
