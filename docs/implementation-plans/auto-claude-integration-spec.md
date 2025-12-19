# Technical Specification: Auto-Claude Integration Opportunities

**Status**: Draft
**Created**: 2025-12-18
**Related Issue**: https://github.com/haighd/claude-learning-companion/issues/14

---

## Overview

This spec details implementation approaches for integrating key Auto-Claude concepts into CLC. Prioritized by value/effort ratio.

---

## 1. Self-Healing QA Loops

### Problem Statement
CLC escalates to CEO immediately when encountering uncertainty or failures. This creates bottlenecks and unnecessary human intervention for fixable issues.

### Proposed Solution

#### Architecture
```
┌─────────────────────────────────────────────────────┐
│  Failure Detection                                  │
│  └─ Categorize: fixable vs unfixable               │
├─────────────────────────────────────────────────────┤
│  Self-Healing Loop (for fixable failures)          │
│  ├─ Attempt 1: Same context, retry                 │
│  ├─ Attempt 2: Add error context, retry            │
│  ├─ Attempt 3: Escalate model tier                 │
│  └─ Attempt N: Give up, escalate to CEO            │
├─────────────────────────────────────────────────────┤
│  CEO Escalation (for unfixable or exhausted)       │
└─────────────────────────────────────────────────────┘
```

#### Fixable Failure Types
| Type | Detection | Fix Strategy |
|------|-----------|--------------|
| Lint errors | Exit code + pattern | Apply linter suggestions |
| Type errors | TypeScript/mypy output | Add types, fix signatures |
| Test failures | pytest/jest output | Analyze failure, modify code |
| Import errors | Module not found | Install package or fix path |
| Syntax errors | Parse errors | Fix syntax based on error |

#### Unfixable Failure Types (Immediate Escalation)
- Architectural decisions required
- Multiple valid approaches with tradeoffs
- External service failures
- Permission/access issues
- Data integrity concerns

#### Configuration
```yaml
# ~/.claude/clc/config/self-healing.yaml
self_healing:
  enabled: true
  max_attempts: 5
  model_escalation_strategy:
    - attempts: [1, 2]
      model: haiku
    - attempts: [3, 4]
      model: sonnet
    - attempts: [5]
      model: opus
  fixable_patterns:
    - "SyntaxError"
    - "TypeError"
    - "ImportError"
    - "eslint"
    - "mypy"
  unfixable_patterns:
    - "EACCES"
    - "EPERM"
    - "architectural"
```

#### Implementation Files
| File | Purpose |
|------|---------|
| `query/self_healer.py` | Main healing loop logic |
| `query/failure_classifier.py` | Categorize fixable vs unfixable |
| `query/fix_strategies.py` | Strategy per failure type |
| `config/self-healing.yaml` | Configuration |

#### Database Schema Addition
```sql
CREATE TABLE healing_attempts (
    id INTEGER PRIMARY KEY,
    failure_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    model_used TEXT NOT NULL,
    strategy_used TEXT,
    success BOOLEAN NOT NULL,
    error_context TEXT,
    fix_applied TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Success Metrics
- CEO escalation reduction: Target 30%
- Auto-fix success rate: Track per failure type
- Time to resolution: Compare with/without healing

---

## 2. Graph-Based Memory (FalkorDB/Graphiti)

### Problem Statement
SQLite stores heuristics as flat records. No way to query semantic relationships like "heuristics that often apply together" or "conflicting rules."

### Proposed Solution

#### Architecture
```
┌─────────────────────────────────────────────────────┐
│  Query Interface (unchanged API)                    │
├─────────────────────────────────────────────────────┤
│  Hybrid Storage Layer                               │
│  ├─ SQLite: Primary (structured data, fast)        │
│  └─ FalkorDB: Secondary (relationships, semantic)  │
├─────────────────────────────────────────────────────┤
│  Sync Service                                       │
│  └─ Keep SQLite ↔ FalkorDB consistent              │
└─────────────────────────────────────────────────────┘
```

#### Graph Schema
```cypher
// Node types
(:Heuristic {id, content, confidence, domain})
(:GoldenRule {id, content, domain})
(:Failure {id, description, root_cause})
(:Success {id, description, approach})
(:Domain {name})

// Relationships
(:Heuristic)-[:DERIVED_FROM]->(:Failure)
(:Heuristic)-[:VALIDATED_BY]->(:Success)
(:Heuristic)-[:CONFLICTS_WITH]->(:Heuristic)
(:Heuristic)-[:COMPLEMENTS]->(:Heuristic)
(:Heuristic)-[:BELONGS_TO]->(:Domain)
(:GoldenRule)-[:PROMOTED_FROM]->(:Heuristic)
(:Heuristic)-[:SIMILAR_TO {score}]->(:Heuristic)
```

#### New Query Capabilities
```python
# Related heuristics
graph.query("""
  MATCH (h:Heuristic {id: $id})-[:COMPLEMENTS|SIMILAR_TO*1..2]-(related)
  RETURN related
""", id=heuristic_id)

# Conflict detection
graph.query("""
  MATCH (h1:Heuristic)-[:CONFLICTS_WITH]-(h2:Heuristic)
  WHERE h1.domain = $domain AND h2.domain = $domain
  RETURN h1, h2
""", domain=domain)

# Knowledge graph visualization data
graph.query("""
  MATCH (h:Heuristic)-[r]-(connected)
  RETURN h, r, connected
  LIMIT 100
""")
```

#### Implementation Files
| File | Purpose |
|------|---------|
| `memory/graph_store.py` | FalkorDB interface |
| `memory/graph_sync.py` | SQLite ↔ Graph sync |
| `memory/relationship_detector.py` | Auto-detect relationships |
| `dashboard-app/frontend/src/KnowledgeGraph.tsx` | Visualization |

#### Docker Compose Addition
```yaml
services:
  falkordb:
    image: falkordb/falkordb:latest
    ports:
      - "6379:6379"
    volumes:
      - falkordb_data:/data

volumes:
  falkordb_data:
```

#### Fallback Behavior
- If FalkorDB unavailable: Use SQLite only (current behavior)
- Log warning, continue operation
- Queue relationship updates for when graph is available

---

## 3. Worktree Isolation

### Problem Statement
CLC operates directly in the main workspace. Experimental changes can corrupt state.

### Proposed Solution

#### Commands
```bash
# Start isolated experiment
/experiment start "test new heuristic promotion logic"

# Check experiment status
/experiment status

# Merge successful experiment
/experiment merge

# Discard failed experiment
/experiment discard
```

#### Architecture
```
┌─────────────────────────────────────────────────────┐
│  Main Workspace (~/.claude/clc/)                    │
│  └─ Protected during experiments                    │
├─────────────────────────────────────────────────────┤
│  Worktree (~/.claude/clc/.worktrees/exp-{id}/)     │
│  ├─ Full copy of CLC                               │
│  ├─ Isolated database                              │
│  └─ Experiment-specific changes                    │
├─────────────────────────────────────────────────────┤
│  Merge/Discard                                      │
│  └─ Clean integration or rollback                  │
└─────────────────────────────────────────────────────┘
```

#### Implementation
```python
# scripts/experiment.py
import re
import shutil
import subprocess
from pathlib import Path

MAX_EXP_ID_LENGTH = 64  # Prevent filesystem path length issues

def validate_exp_id(exp_id: str) -> bool:
    """Validate experiment ID to prevent command injection.

    Must start with an alphanumeric character and contain only alphanumerics,
    hyphens, and underscores. Leading hyphens are prevented to avoid shell flag
    confusion. Maximum length is limited to prevent filesystem path issues.
    """
    if len(exp_id) > MAX_EXP_ID_LENGTH:
        return False
    return bool(re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', exp_id))

def run_git(*args: str) -> subprocess.CompletedProcess:
    """Run git command safely using argument list (no shell interpolation)."""
    return subprocess.run(['git'] + list(args), check=True)

def start_experiment(description: str) -> str:
    """Create isolated worktree for experiment."""
    exp_id = generate_id()  # Must return safe alphanumeric ID
    if not validate_exp_id(exp_id):
        raise ValueError(f"Invalid experiment ID: {exp_id}")

    # Use pathlib for safe path construction
    worktree_path = Path(".worktrees") / f"exp-{exp_id}"
    branch_name = f"exp-{exp_id}"

    # Create worktree using subprocess with argument list (safe)
    run_git('worktree', 'add', str(worktree_path), '-b', branch_name)

    # Copy database (isolated state) - ensure directory exists first
    (worktree_path / "memory").mkdir(parents=True, exist_ok=True)
    shutil.copy("memory/index.db", worktree_path / "memory" / "index.db")

    # Record experiment
    save_experiment_metadata(exp_id, description)

    return exp_id

# WARNING: Conceptual example – not directly executable.
# Functions like `merge_databases` and `validate_experiment` are placeholders.
# Actual implementation requires a complete storage layer.

def merge_experiment(exp_id: str) -> bool:
    """Merge successful experiment back to main."""
    if not validate_exp_id(exp_id):
        raise ValueError(f"Invalid experiment ID: {exp_id}")

    # Use pathlib for safe path construction
    worktree_path = Path(".worktrees") / f"exp-{exp_id}"
    branch_name = f"exp-{exp_id}"

    # Validate experiment succeeded
    if not validate_experiment(exp_id):
        return False

    # ATOMIC MERGE STRATEGY: Git first, then database.
    # This ensures code and data stay consistent - if either fails, we roll back.
    #
    # NOTE: `merge_databases` is a conceptual function that would be
    # implemented in the storage/persistence layer. It handles conflict
    # resolution, deduplication, and timestamp reconciliation.

    # Step 1: Stage git merge (--no-commit allows abort if DB merge fails)
    try:
        run_git('checkout', 'main')
        run_git('merge', '--no-ff', '--no-commit', branch_name)
    except subprocess.CalledProcessError as e:
        # Git merge failed (conflicts) - abort and report
        run_git('merge', '--abort')
        raise RuntimeError(f"Git merge failed (conflicts): {e}")

    # Step 2: Merge database (git is staged but not committed)
    try:
        merge_databases("memory/index.db", str(worktree_path / "memory" / "index.db"))
    except Exception as e:
        # Database merge failed - abort the staged git merge
        run_git('merge', '--abort')
        raise RuntimeError(f"Database merge failed, git merge aborted: {e}")

    # Step 3: Both succeeded - finalize the git commit
    try:
        run_git('commit', '-m', f'Merge experiment {exp_id}')
    except subprocess.CalledProcessError as e:
        # Commit failed (e.g., pre-commit hook) - rollback database and abort git
        # NOTE: rollback_db_merge is conceptual - would restore from backup
        # rollback_db_merge()
        run_git('merge', '--abort')
        raise RuntimeError(f"Git commit failed, database merge rolled back: {e}")

    # Cleanup - use robust error handling to ensure both operations complete
    cleanup_errors = []
    try:
        run_git('worktree', 'remove', str(worktree_path))
    except subprocess.CalledProcessError as e:
        cleanup_errors.append(f"Worktree removal failed: {e}")

    try:
        run_git('branch', '-d', branch_name)
    except subprocess.CalledProcessError as e:
        cleanup_errors.append(f"Branch deletion failed: {e}")

    if cleanup_errors:
        # Log but don't fail - merge already succeeded
        print(f"Cleanup warnings: {cleanup_errors}")

    return True

def discard_experiment(exp_id: str):
    """Discard failed experiment."""
    if not validate_exp_id(exp_id):
        raise ValueError(f"Invalid experiment ID: {exp_id}")

    # Use pathlib for safe path construction
    worktree_path = Path(".worktrees") / f"exp-{exp_id}"
    branch_name = f"exp-{exp_id}"

    # Use robust error handling - try to clean up both even if one fails
    errors = []
    try:
        run_git('worktree', 'remove', '--force', str(worktree_path))
    except subprocess.CalledProcessError as e:
        errors.append(f"Worktree removal failed: {e}")

    try:
        run_git('branch', '-D', branch_name)
    except subprocess.CalledProcessError as e:
        errors.append(f"Branch deletion failed: {e}")

    if errors:
        raise RuntimeError(f"Cleanup partially failed: {errors}")
```

#### Slash Command
```markdown
# ~/.claude/clc/setup/commands/experiment.md
---
description: Manage isolated experiments for risky CLC changes
---

Run experiment management:
- `start [description]`: Create isolated worktree
- `status`: Show active experiments
- `merge`: Integrate successful experiment
- `discard`: Remove failed experiment

Command: $ARGUMENTS
```

---

## 4. Dashboard Kanban Enhancement

### Problem Statement
Dashboard shows analytics but no workflow management. Users can't track task progress visually.

### Proposed Solution

#### New Tab: Workflows
```
┌─────────────────────────────────────────────────────┐
│  [Overview] [Heuristics] [Runs] [Workflows] [Query] │
├─────────────────────────────────────────────────────┤
│  Pending    │  In Progress  │  Review   │  Done     │
│  ─────────  │  ───────────  │  ───────  │  ─────    │
│  ┌───────┐  │  ┌───────┐    │           │  ┌─────┐  │
│  │Task 1 │  │  │Task 2 │    │           │  │Done │  │
│  └───────┘  │  └───────┘    │           │  └─────┘  │
│  ┌───────┐  │               │           │           │
│  │Task 3 │  │               │           │           │
│  └───────┘  │               │           │           │
└─────────────────────────────────────────────────────┘
```

#### Backend Endpoints
```python
# dashboard-app/backend/main.py

@app.get("/api/workflows")
async def get_workflows():
    """Get all workflow items grouped by status."""

@app.post("/api/workflows")
async def create_workflow(item: WorkflowItem):
    """Create new workflow item."""

@app.patch("/api/workflows/{id}/status")
async def update_status(id: str, status: str):
    """Move item between columns."""

@app.post("/api/workflows/{id}/link")
async def link_to_learning(id: str, learning_id: str):
    """Link workflow to heuristic/learning."""
```

#### Frontend Component
```typescript
// dashboard-app/frontend/src/components/Kanban.tsx
import React, { useState } from 'react';
import {
  DndContext,
  DragEndEvent,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';

type ColumnId = 'pending' | 'in_progress' | 'review' | 'done';

interface WorkflowItem {
  id: string;
  title: string;
  description: string;
  status: ColumnId;
  linkedLearnings: string[];
  createdAt: Date;
}

// Droppable column component
const Column: React.FC<{ id: ColumnId; children: React.ReactNode }> = ({ id, children }) => {
  const { setNodeRef } = useDroppable({ id });
  return <div ref={setNodeRef}>{children}</div>;
};

const Kanban: React.FC = () => {
  const [items, setItems] = useState<WorkflowItem[]>([]);
  const columns: ColumnId[] = ['pending', 'in_progress', 'review', 'done'];

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Find which column contains an item
  const findContainer = (id: string): ColumnId | undefined => {
    const item = items.find(i => i.id === id);
    return item?.status;
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    // Determine target column: if dropped on a column, use that;
    // if dropped on an item, use that item's column
    const targetColumn = columns.includes(overId as ColumnId)
      ? (overId as ColumnId)
      : findContainer(overId);

    if (targetColumn) {
      updateWorkflowStatus(activeId, targetColumn);
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragEnd={handleDragEnd}
    >
      {columns.map(columnId => (
        <Column key={columnId} id={columnId}>
          <SortableContext
            items={items.filter(i => i.status === columnId).map(i => i.id)}
            strategy={verticalListSortingStrategy}
          >
            {/* Render sortable items */}
          </SortableContext>
        </Column>
      ))}
    </DndContext>
  );
};
```

#### Dependencies
```json
{
  "dependencies": {
    "@dnd-kit/core": "^6.0.0",
    "@dnd-kit/sortable": "^8.0.0"
  }
}
```

---

## 5. Execution Agents (Future Phase)

### Problem Statement
CLC agents only advise; they don't execute. This requires human implementation of all suggestions.

### Proposed Solution (Sketch)

This is a larger architectural change. High-level approach:

#### Mode Toggle
```python
from enum import Enum

class AgentMode(Enum):
    ADVISORY = "advisory"      # Current behavior
    EXECUTOR = "executor"      # New: can take actions

# Per-agent configuration
agent_config = {
    "researcher": {
        "mode": AgentMode.ADVISORY,
        "allowed_actions": ["web_search", "file_read", "grep"]
    },
    "architect": {
        "mode": AgentMode.ADVISORY,
        "allowed_actions": ["file_read", "mkdir", "scaffold"]
    },
    "skeptic": {
        "mode": AgentMode.EXECUTOR,  # Opt-in per agent
        "allowed_actions": ["run_tests", "lint", "type_check"]
    }
}
```

#### Safety Controls
- Whitelist of allowed actions per agent
- Require confirmation for destructive actions
- Automatic rollback on failure
- Audit log of all executions

**Note**: This feature requires significant design work. Recommend deferring to Phase 2 after simpler integrations prove valuable.

---

## Implementation Priority

| Feature | Value | Effort | Priority |
|---------|-------|--------|----------|
| Self-Healing QA | High | Medium | P0 |
| Worktree Isolation | Medium | Low | P1 |
| Kanban Dashboard | Medium | Medium | P2 |
| Graph Memory | High | High | P3 |
| Execution Agents | High | High | Future |

## Next Steps

1. Implement self-healing QA loops (P0)
2. Add `/experiment` slash command (P1)
3. Dashboard Kanban tab (P2)
4. Evaluate graph DB needs after 1-3 are stable

---

## 6. Coexistence Guide

For details on running CLC and Auto-Claude together, including resource separation, potential issues and mitigations, installation options, and recommended hybrid workflows, see the [Auto-Claude Integration Guide](../auto-claude-integration-guide.md).

---

*Spec Version: 1.2 - Removed duplicated coexistence content, linked to main guide*
