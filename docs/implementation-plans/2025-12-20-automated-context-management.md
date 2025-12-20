# Implementation Plan: Automated Context Window Management

---
created: 2025-12-20
status: draft
related_prd: docs/prd/2025-12-20-automated-context-management.md
estimated_phases: 3
---

## Overview

Implement a comprehensive, automated context management system that maintains context quality without manual intervention, enabling truly autonomous agent operation. The system uses a three-layer approach: reactive (PreCompact hook), proactive (watcher monitoring), and preventive (task batching).

**Key Insight**: The existing `/checkpoint` command captures structured semantic context (What/Why/Where, Active Issues, Key Decisions, Next Steps) which is fundamentally different from `/compact` which only summarizes conversation text. Auto-checkpoints must replicate this structured approach.

## Current State Analysis

### Existing Components

| Component | Location | Current Capability | Gap |
|-----------|----------|-------------------|-----|
| `auto-checkpoint.cjs` | `~/.claude/hooks/` | Warns when context > 60% | Only warns, doesn't actually checkpoint |
| Checkpoint command | `~/.claude/commands/checkpoint.md` | Updates `project.md` | No structured checkpoint format |
| Watcher system | `~/.claude/clc/watcher/` | Two-tier (Haiku + Opus), monitors blackboard | No context utilization monitoring |
| Coordinator | `~/.claude/clc/coordinator/` | Blackboard + event log, task queue, claim chains | No task batching by context size |

### Hook System Capabilities (Researched)

| Hook Event | Can Block? | Can Add Context? | Our Use |
|------------|------------|------------------|---------|
| **PreCompact** | No | No | Save checkpoint file before compaction |
| **SessionStart** | No | Yes (additionalContext) | Restore context from checkpoint |
| **UserPromptSubmit** | Yes | Yes | Proactive warnings (existing) |

**Critical Finding**: PreCompact cannot block compaction but receives `transcript_path` to the full conversation JSONL, enabling quality state extraction.

## Desired End State

```
Agent works → Context grows → 60% threshold →
Watcher triggers proactive checkpoint → Quality state saved →
Context continues → Compaction triggered →
PreCompact intercepts → Final checkpoint saved →
Compaction proceeds → SessionStart restores →
Agent resumes with full context awareness
```

**Success Criteria**:
- Zero phantom checkpoints (verification confirms file exists)
- Checkpoint quality matches manual `/checkpoint`
- 4+ hours autonomous operation without intervention
- < 1 manual checkpoint intervention per day (down from 5-10)

## What We're NOT Doing

1. **Blocking compaction** - PreCompact can only observe; we work within this constraint
2. **Token budget API** - Not reliably exposed; using heuristics instead
3. **Replacing /compact** - Supplementing with quality checkpoints, not replacing
4. **Cross-machine coordination** - Single machine focus for this implementation
5. **Modifying Claude Code internals** - Working within current hook capabilities

## Implementation Approach

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTOMATED CONTEXT MANAGEMENT                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LAYER 1: PREVENTIVE (Phase 3)                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ coordinator/task_batcher.py                                 │ │
│  │ - Estimates token cost before task assignment               │ │
│  │ - Splits large tasks into context-sized chunks              │ │
│  │ - Auto-checkpoint between batches                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                   │
│  LAYER 2: PROACTIVE (Phase 2)                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ watcher/context_monitor.py                                  │ │
│  │ - Monitors context utilization heuristics every 30s         │ │
│  │ - Triggers checkpoint at 60% via blackboard message         │ │
│  │ - Coordinates multi-agent checkpoint timing                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                   │
│  LAYER 3: REACTIVE (Phase 1) ← START HERE                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ hooks/pre-compact-checkpoint.cjs                            │ │
│  │ - Intercepts PreCompact event (auto trigger)                │ │
│  │ - Reads transcript from transcript_path                     │ │
│  │ - Extracts structured state                                 │ │
│  │ - Writes verified checkpoint file                           │ │
│  │                                                             │ │
│  │ hooks/session-start-restore.cjs                             │ │
│  │ - On SessionStart, finds latest checkpoint                  │ │
│  │ - Returns additionalContext with resume instructions        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  VERIFICATION LAYER (All Phases)                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ scripts/verify-checkpoint.sh                                │ │
│  │ - Confirms file exists after creation                       │ │
│  │ - Validates required fields present                         │ │
│  │ - Updates global index                                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Storage Architecture

```
Project-specific checkpoints:
  .claude/checkpoints/
    └── 2025-12-20-143022.md

Global checkpoint index:
  ~/.claude/clc/checkpoints/
    └── index.json

Checkpoint file structure:
  ---
  created: 2025-12-20T14:30:22Z
  trigger: auto | manual | watcher
  project: /path/to/project
  session_id: abc123
  iteration: 3
  verified: true
  ---

  ## What Changed
  - [file:line] - Description of change

  ## Why Changed
  - Rationale for changes

  ## Active Issues
  - Current problem state

  ## Key Decisions
  - Architectural choices made

  ## Next Steps
  - [ ] Task 1
  - [ ] Task 2
```

---

## Phase 1: PreCompact Auto-Checkpoint (P0)

**Goal**: Reactive checkpointing that saves quality state before any compaction occurs.

**PRD Requirements Addressed**: FR-001, FR-002, FR-003, FR-004, FR-005

### 1.1 Create PreCompact Checkpoint Hook

**File**: `~/.claude/hooks/pre-compact-checkpoint.cjs`

**Functionality**:
1. Triggered on PreCompact event with `trigger: auto`
2. Read full transcript from `transcript_path`
3. Parse JSONL to extract:
   - Recent file changes (Edit, Write tool calls)
   - Key decisions (look for decision-related patterns)
   - Active issues (error patterns, TODO markers)
   - Conversation summary (last N assistant messages)
4. Generate structured checkpoint markdown
5. Write to `.claude/checkpoints/YYYY-MM-DD-HHMMSS.md`
6. Call verification script
7. Update global index

**Input Schema** (from Claude Code):
```json
{
  "session_id": "abc123",
  "transcript_path": "~/.claude/projects/.../00893aaf.jsonl",
  "hook_event_name": "PreCompact",
  "trigger": "auto"
}
```

**Output Schema**:
```json
{
  "continue": true,
  "suppressOutput": true
}
```

**Key Implementation Details**:
- Must complete in < 2 seconds (NFR requirement)
- Graceful fallback if transcript parsing fails
- No blocking - compaction must proceed

### 1.2 Create Session Start Restore Hook

**File**: `~/.claude/hooks/session-start-restore.cjs`

**Functionality**:
1. Triggered on SessionStart
2. Check for recent checkpoint (< 24 hours) for current project
3. If found, read checkpoint and format as resume context
4. Return via `additionalContext` field

**Output Schema**:
```json
{
  "additionalContext": "## Resuming from Checkpoint\n\n[structured content]",
  "continue": true
}
```

### 1.3 Create Verification System

**File**: `~/.claude/clc/scripts/verify-checkpoint.sh`

**Functionality**:
1. Verify file exists at expected path
2. Validate YAML frontmatter present
3. Check required sections exist:
   - `## What Changed`
   - `## Next Steps`
4. Update global index with checkpoint metadata
5. Return exit code 0 on success, 1 on failure

**Global Index Schema** (`~/.claude/clc/checkpoints/index.json`):
```json
{
  "version": "1.0",
  "checkpoints": [
    {
      "id": "2025-12-20-143022",
      "path": "/path/to/project/.claude/checkpoints/2025-12-20-143022.md",
      "project": "/path/to/project",
      "created": "2025-12-20T14:30:22Z",
      "trigger": "auto",
      "verified": true,
      "iteration": 3,
      "summary": "Implementing auth feature - 3 files modified"
    }
  ],
  "last_updated": "2025-12-20T14:30:25Z"
}
```

### 1.4 Configure Hooks in Settings

**File**: `~/.claude/settings.json` (add to existing)

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "auto",
        "hooks": [
          {
            "type": "command",
            "command": "node ~/.claude/hooks/pre-compact-checkpoint.cjs",
            "timeout": 5000
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "node ~/.claude/hooks/session-start-restore.cjs",
            "timeout": 3000
          }
        ]
      }
    ]
  }
}
```

### 1.5 Update /resume Command

**File**: `~/.claude/commands/resume.md` (modify existing)

Add logic to:
1. Query global checkpoint index
2. Find most recent checkpoint for current project
3. Display checkpoint summary
4. Offer to load checkpoint context

### Phase 1 Success Criteria

**Automated Verification**:
```bash
# Test PreCompact hook execution
echo '{"session_id":"test","transcript_path":"/tmp/test.jsonl","hook_event_name":"PreCompact","trigger":"auto"}' | node ~/.claude/hooks/pre-compact-checkpoint.cjs

# Verify checkpoint created
ls -la .claude/checkpoints/

# Verify index updated
cat ~/.claude/clc/checkpoints/index.json | jq '.checkpoints[-1]'

# Test verification script
~/.claude/clc/scripts/verify-checkpoint.sh .claude/checkpoints/latest.md
```

**Manual Verification**:
- [ ] Trigger auto-compaction by filling context window
- [ ] Verify checkpoint file created with correct structure
- [ ] Start new session, verify resume context loaded
- [ ] Compare checkpoint quality to manual `/checkpoint`

---

## Phase 2: Watcher Multi-Agent Monitor (P1)

**Goal**: Proactive monitoring that triggers checkpoints at 60% threshold before context pressure builds.

**PRD Requirements Addressed**: FR-006, FR-007, FR-009, FR-010

### 2.1 Create Context Monitor Module

**File**: `~/.claude/clc/watcher/context_monitor.py`

**Functionality**:
1. Estimate context utilization using heuristics:
   - Message count in session
   - File operations (Read, Edit, Write tool calls)
   - Subagent spawns (Task tool calls)
   - Elapsed time
2. Apply weights to estimate percentage
3. Return structured metrics

**Heuristics Model**:
```python
def estimate_context_usage(state: Dict) -> float:
    """
    Estimate context usage as percentage (0.0 - 1.0).

    Token budget API not available, so we use observable heuristics:
    - Each message ~500-2000 tokens
    - Each file read ~1000-5000 tokens
    - Each tool output ~200-1000 tokens

    Conservative estimate to trigger early rather than late.
    """
    weights = {
        'message_count': 0.01,      # 1% per message
        'file_reads': 0.02,         # 2% per file read
        'file_edits': 0.015,        # 1.5% per edit
        'tool_calls': 0.005,        # 0.5% per tool
        'subagent_spawns': 0.05,    # 5% per subagent
    }

    usage = sum(
        state.get(metric, 0) * weight
        for metric, weight in weights.items()
    )

    return min(usage, 1.0)
```

### 2.2 Extend Watcher State Gathering

**File**: `~/.claude/clc/watcher/haiku_watcher.py` (modify)

Add to `gather_state()`:
```python
# Context utilization metrics
state["context_metrics"] = {
    "estimated_usage": context_monitor.estimate_context_usage(session_state),
    "message_count": session_state.get("message_count", 0),
    "tool_calls": session_state.get("tool_calls", 0),
    "last_checkpoint": get_last_checkpoint_time(project_path),
}
```

### 2.3 Add Threshold Detection to Watcher Prompt

**File**: `~/.claude/clc/watcher/haiku_watcher.py` (modify `get_haiku_prompt()`)

Add detection criteria:
```python
detection_criteria += """
- Context utilization > 60%? (trigger checkpoint)
- Time since last checkpoint > 30 minutes with active work?
"""
```

Add new status:
```python
# STATUS: context_high
# RECOMMENDED_ACTION: trigger_checkpoint
```

### 2.4 Checkpoint Trigger via Blackboard

When watcher detects high context:
1. Write message to blackboard: `{"type": "checkpoint_trigger", "reason": "context_60_percent"}`
2. Agent's PostToolUse hook reads blackboard messages
3. Agent runs `/checkpoint` on next opportunity

### 2.5 Checkpoint Counter and Lineage

**File**: `~/.claude/clc/scripts/checkpoint-counter.sh`

Track checkpoint iterations:
```bash
# Read current iteration
iteration=$(cat .claude/.checkpoint_iteration 2>/dev/null || echo "0")

# Increment
echo $((iteration + 1)) > .claude/.checkpoint_iteration

# Include in checkpoint metadata
echo "iteration: $iteration"
```

### Phase 2 Success Criteria

**Automated Verification**:
```bash
# Test context estimation
python -c "from watcher.context_monitor import estimate_context_usage; print(estimate_context_usage({'message_count': 50, 'file_reads': 10}))"

# Test watcher with mock high context
python ~/.claude/clc/watcher/test_watcher.py --scenario context_high

# Verify checkpoint trigger message in blackboard
cat .coordination/blackboard.json | jq '.messages[] | select(.type == "checkpoint_trigger")'
```

**Manual Verification**:
- [ ] Run extended session (30+ messages)
- [ ] Verify watcher detects 60% threshold
- [ ] Verify checkpoint triggered automatically
- [ ] Verify iteration counter increments correctly

---

## Phase 3: Context-Aware Task Batching (P1)

**Goal**: Preventive task splitting that keeps work within context budget.

**PRD Requirements Addressed**: FR-008

### 3.1 Create Task Batcher Module

**File**: `~/.claude/clc/coordinator/task_batcher.py`

**Functionality**:
1. Estimate token cost of task before assignment
2. Split large tasks into context-sized chunks
3. Insert checkpoint tasks between batches

**Token Cost Estimation**:
```python
def estimate_task_tokens(task: Dict) -> int:
    """
    Estimate tokens a task will consume.

    Factors:
    - Task description length
    - Number of files likely to be touched
    - Complexity indicators (keywords like "refactor", "implement")
    """
    base_cost = len(task['description']) // 4  # ~4 chars per token

    complexity_multipliers = {
        'refactor': 2.0,
        'implement': 1.5,
        'fix': 1.0,
        'update': 0.8,
        'add': 1.2,
    }

    multiplier = 1.0
    for keyword, mult in complexity_multipliers.items():
        if keyword in task['description'].lower():
            multiplier = max(multiplier, mult)

    file_count = task.get('estimated_files', 3)
    file_cost = file_count * 2000  # ~2000 tokens per file

    return int((base_cost + file_cost) * multiplier)
```

### 3.2 Task Splitting Logic

```python
def split_task_for_context(task: Dict, available_tokens: int) -> List[Dict]:
    """
    Split a large task into context-sized subtasks.

    Strategy:
    1. If task fits, return as-is
    2. If task has explicit subtasks, use those
    3. Otherwise, split by file groups
    """
    estimated = estimate_task_tokens(task)

    if estimated <= available_tokens:
        return [task]

    # Split by subtasks if available
    if 'subtasks' in task:
        return task['subtasks']

    # Split by file groups
    files = task.get('files', [])
    if files:
        return split_by_file_groups(task, files, available_tokens)

    # Cannot split - return with warning
    task['warning'] = 'Task may exceed context budget'
    return [task]
```

### 3.3 Inter-Batch Checkpointing

Modify conductor workflow to insert checkpoint nodes:

```python
def create_batched_workflow(tasks: List[Dict]) -> Dict:
    """
    Create workflow with checkpoint nodes between batches.
    """
    workflow = {"nodes": {}, "edges": []}

    batches = batch_tasks_by_context(tasks)

    for i, batch in enumerate(batches):
        # Add batch node
        workflow["nodes"][f"batch_{i}"] = {
            "type": "parallel",
            "tasks": batch
        }

        # Add checkpoint node after each batch (except last)
        if i < len(batches) - 1:
            workflow["nodes"][f"checkpoint_{i}"] = {
                "type": "single",
                "prompt": "Run /checkpoint to save progress"
            }

            workflow["edges"].append({
                "from": f"batch_{i}",
                "to": f"checkpoint_{i}"
            })
            workflow["edges"].append({
                "from": f"checkpoint_{i}",
                "to": f"batch_{i+1}"
            })

    return workflow
```

### Phase 3 Success Criteria

**Automated Verification**:
```bash
# Test token estimation
python -c "from coordinator.task_batcher import estimate_task_tokens; print(estimate_task_tokens({'description': 'Implement user authentication with OAuth2', 'estimated_files': 5}))"

# Test task splitting
python -c "from coordinator.task_batcher import split_task_for_context; print(len(split_task_for_context(large_task, 50000)))"
```

**Manual Verification**:
- [ ] Submit large multi-file task
- [ ] Verify task is split into batches
- [ ] Verify checkpoint inserted between batches
- [ ] Verify each batch completes within context budget

---

## Files to Create/Modify Summary

| File | Action | Phase | Purpose |
|------|--------|-------|---------|
| `~/.claude/hooks/pre-compact-checkpoint.cjs` | Create | 1 | PreCompact auto-checkpoint hook |
| `~/.claude/hooks/session-start-restore.cjs` | Create | 1 | SessionStart context restoration |
| `~/.claude/clc/scripts/verify-checkpoint.sh` | Create | 1 | Checkpoint verification |
| `~/.claude/clc/checkpoints/index.json` | Create | 1 | Global checkpoint index |
| `~/.claude/settings.json` | Modify | 1 | Add hook configurations |
| `~/.claude/commands/resume.md` | Modify | 1 | Add checkpoint loading |
| `~/.claude/clc/watcher/context_monitor.py` | Create | 2 | Context utilization monitoring |
| `~/.claude/clc/watcher/haiku_watcher.py` | Modify | 2 | Add context metrics to state |
| `~/.claude/clc/scripts/checkpoint-counter.sh` | Create | 2 | Iteration tracking |
| `~/.claude/clc/coordinator/task_batcher.py` | Create | 3 | Context-aware task batching |
| `~/.claude/clc/conductor/conductor.py` | Modify | 3 | Inter-batch checkpointing |

---

## Integration Points for Future Phases

### Phase 1 → Phase 2 Integration

Phase 1 creates checkpoint files. Phase 2 needs to:
- Read last checkpoint time from index
- Trigger checkpoint via blackboard message
- Update checkpoint with `trigger: watcher` source

**Interface**:
```python
# Phase 2 calls this to trigger checkpoint
def trigger_checkpoint(reason: str) -> None:
    write_to_blackboard({
        "type": "checkpoint_trigger",
        "reason": reason,
        "timestamp": datetime.now().isoformat()
    })
```

### Phase 2 → Phase 3 Integration

Phase 2 monitors context. Phase 3 needs to:
- Query current context estimate before batching
- Adjust batch sizes based on remaining context

**Interface**:
```python
# Phase 3 calls this to get available context
def get_available_context() -> int:
    usage = estimate_context_usage(get_session_state())
    total_budget = 100000  # Conservative estimate
    return int(total_budget * (1.0 - usage))
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PreCompact hook adds latency | M | L | Keep hook lightweight (< 2s), async file I/O |
| Checkpoint file corruption | L | H | Verify integrity after write, atomic temp-file rename |
| Heuristics misjudge context usage | M | M | Conservative thresholds (60% not 80%), fallback to PreCompact |
| Task splitting breaks coherent work | M | M | Allow manual override, learn from patterns |
| Disk space from checkpoints | L | L | Auto-prune checkpoints > 7 days, configurable retention |

---

## Testing Strategy

### Unit Tests

```bash
# Phase 1
test/hooks/test_pre_compact_checkpoint.js
test/hooks/test_session_start_restore.js
test/scripts/test_verify_checkpoint.sh

# Phase 2
test/watcher/test_context_monitor.py
test/watcher/test_checkpoint_trigger.py

# Phase 3
test/coordinator/test_task_batcher.py
test/conductor/test_batched_workflow.py
```

### Integration Tests

1. **End-to-end checkpoint cycle**:
   - Fill context to trigger compaction
   - Verify checkpoint created
   - Start new session
   - Verify context restored

2. **Multi-agent coordination**:
   - Spawn 3 agents on same project
   - Verify checkpoints don't conflict
   - Verify index tracks all checkpoints

3. **Batched task execution**:
   - Submit 10-file refactoring task
   - Verify split into batches
   - Verify checkpoints between batches

---

## Rollout Plan

### Phase 1 Rollout
1. Deploy hooks to `~/.claude/hooks/`
2. Update settings.json
3. Test with single agent for 1 week
4. Monitor for phantom checkpoints (should be 0)
5. Measure autonomous operation duration

### Phase 2 Rollout
1. Deploy context_monitor.py
2. Update watcher prompts
3. Test threshold detection accuracy
4. Tune heuristics based on real usage

### Phase 3 Rollout
1. Deploy task_batcher.py
2. Test with known large tasks
3. Gather feedback on split quality
4. Iterate on splitting algorithm

---

## Appendix

### Related Documents
- PRD: `docs/prd/2025-12-20-automated-context-management.md`
- Watcher Architecture: `~/.claude/clc/watcher/README.md`
- Coordinator Architecture: `~/.claude/clc/coordinator/CLAIM_CHAINS_QUICK_REF.md`
- Existing Hooks: `~/.claude/hooks/auto-checkpoint.cjs`

### Glossary
- **PreCompact**: Hook event fired before Claude Code runs context compaction
- **Checkpoint**: Saved state including context, progress, and resume instructions
- **Phantom Checkpoint**: Reported checkpoint that was never actually created
- **Watcher**: CLC's Haiku-tier monitoring system for agent oversight
- **Blackboard**: Shared state store for multi-agent coordination
