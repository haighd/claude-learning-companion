# Sprint Work Plan: Auto-Claude Features
**Group:** auto-claude-features
**Sprint:** 20251220
**Worktree:** `/Users/danhaight/.claude/clc-worktrees/sprint-20251220-auto-claude-features`
**Branch:** `sprint/auto-claude-features`

---

## Assigned Issues

1. **Issue #32** - [Kanban] Auto-create tasks from failures and CEO inbox items
   - Priority: **medium**
   - Effort: **medium**
   - Labels: enhancement, auto-claude

2. **Issue #33** - [Auto-Claude] Complete Graph Memory integration with FalkorDB
   - Priority: **low**
   - Effort: **high**
   - Labels: enhancement, auto-claude
   - Depends on: #29 (KnowledgeGraph import fix - handled by another group)

---

## File Impact Analysis

### Issue #32: Kanban Automation

| File Path | Change Type | Shared? | Risk |
|-----------|-------------|---------|------|
| `dashboard-app/backend/utils/auto_capture.py` | Modify | No | Low - isolated utility |
| `hooks/learning-loop/post_tool_learning_new.py` | Modify | Yes | Medium - active hook |
| `dashboard-app/backend/routers/workflows.py` | Modify | No | Low - add helper functions |
| `memory/kanban_automation.py` | Create | No | Low - new module |
| `watcher/kanban_watcher.py` | Create | No | Low - new service |
| `scripts/start-kanban-watcher.sh` | Create | No | Low - new script |
| `ceo-inbox/.gitkeep` | Create | No | None - directory marker |

### Issue #33: Graph Memory Integration

| File Path | Change Type | Shared? | Risk |
|-----------|-------------|---------|------|
| `memory/graph_store.py` | Modify | No | Low - add retry logic |
| `memory/graph_sync.py` | Modify | No | Low - fix method name |
| `memory/relationship_detector.py` | Test | No | None - verify existing |
| `dashboard-app/backend/routers/graph.py` | Fix | No | Low - sync_all() typo |
| `memory/graph_sync_service.py` | Create | No | Low - new background service |
| `scripts/start-graph-sync.sh` | Create | No | Low - new script |
| `docker-compose.yml` | Modify | Yes | Medium - infrastructure change |
| `hooks/learning-loop/post_tool_learning_new.py` | Modify | Yes | Medium - add relationship detection |
| `docs/graph-memory-setup.md` | Create | No | None - documentation |

---

## Implementation Steps

### Issue #32: Kanban Auto-Creation (Priority: Medium, ~2-3 hours)

#### Step 1: Create Core Automation Module
**File:** `memory/kanban_automation.py`
- Function: `create_task_from_failure(learning_id, title, summary, domain)`
- Function: `create_task_from_ceo_inbox(filepath, title, priority)`
- Function: `create_task_from_heuristic(heuristic_id, rule, domain)`
- Function: `move_task_to_done(task_id)`
- Function: `find_linked_task(learning_id=None, heuristic_id=None)`
- Database operations: INSERT into kanban_tasks
- Return task_id for linking

#### Step 2: Integrate with Auto-Capture Hook
**File:** `dashboard-app/backend/utils/auto_capture.py`
- Import kanban_automation module
- After recording failure to DB, call `create_task_from_failure()`
- Handle exceptions gracefully (log but don't block capture)
- Add flag to disable if needed: `KANBAN_AUTO_CREATE_ENABLED`

#### Step 3: Integrate with Learning Loop Hook
**File:** `hooks/learning-loop/post_tool_learning_new.py`
- Import kanban_automation module
- When new heuristic created: call `create_task_from_heuristic()`
- When heuristic validated: call `move_task_to_done()`
- When failure resolved: call `move_task_to_done()`

#### Step 4: Create CEO Inbox Watcher
**File:** `watcher/kanban_watcher.py`
- Watch `ceo-inbox/` directory for new .md files
- Parse YAML frontmatter for title, priority, urgency
- Call `create_task_from_ceo_inbox()`
- Track processed files to avoid duplicates
- Run as background service (similar to haiku_watcher.py)

**File:** `scripts/start-kanban-watcher.sh`
```bash
#!/bin/bash
# Start Kanban automation watcher
cd ~/.claude/clc
python3 -m watcher.kanban_watcher
```

#### Step 5: Add Dashboard Statistics
**File:** `dashboard-app/backend/routers/workflows.py`
- New endpoint: `GET /api/kanban/stats`
- Return counts by auto-creation source:
  - failures_pending
  - ceo_decisions_pending
  - validations_pending
  - auto_created_total
  - manually_created_total

#### Step 6: Testing
- Create test failure → verify task created in "pending"
- Create CEO inbox file → verify task created
- Create heuristic → verify validation task in "review"
- Validate heuristic → verify task moved to "done"
- Check dashboard stats endpoint

---

### Issue #33: Graph Memory Integration (Priority: Low, ~4-5 hours)

#### Step 1: Fix Existing Issues
**File:** `dashboard-app/backend/routers/graph.py` (Line 465)
- Change `sync.sync_all()` to `sync.full_sync()`
- The method doesn't exist; use correct name from graph_sync.py

**File:** `memory/graph_store.py`
- Add connection retry logic in `connect()` method
- Add exponential backoff for failed connections
- Improve logging for connection failures

#### Step 2: Create Background Sync Service
**File:** `memory/graph_sync_service.py`
- Periodic sync every 5 minutes (configurable)
- Incremental sync by default, full sync on startup
- Graceful degradation if FalkorDB unavailable
- Log sync statistics
- Signal handling for clean shutdown

**File:** `scripts/start-graph-sync.sh`
```bash
#!/bin/bash
# Start graph sync background service
cd ~/.claude/clc
python3 -m memory.graph_sync_service
```

#### Step 3: Enable Relationship Detection
**File:** `hooks/learning-loop/post_tool_learning_new.py`
- After creating heuristic in graph, call relationship detector
- Only detect relationships for new heuristic (not full scan)
- Use `find_related_for_heuristic(heuristic_id)` from relationship_detector.py
- Apply detected relationships with `apply_relationships_to_graph()`
- Handle FalkorDB unavailable gracefully

#### Step 4: Docker Compose Configuration
**File:** `docker-compose.yml` (create or modify)
```yaml
version: '3.8'
services:
  falkordb:
    image: falkordb/falkordb:latest
    container_name: clc-falkordb
    ports:
      - "6379:6379"
    volumes:
      - falkordb-data:/var/lib/falkordb
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  falkordb-data:
```

**Note:** FalkorDB is already running (verified with docker ps), but document it for future setups.

#### Step 5: Documentation
**File:** `docs/graph-memory-setup.md`
```markdown
# Graph Memory Setup Guide

## Overview
The knowledge graph provides semantic relationships between heuristics, failures, and learnings.

## Architecture
- **Primary Store:** SQLite (memory/index.db)
- **Graph Store:** FalkorDB (optional, port 6379)
- **Sync Service:** Keeps SQLite and FalkorDB synchronized
- **Visualization:** 3D cosmic graph in dashboard

## Setup (Optional)
FalkorDB is optional. The system works with SQLite fallback.

### To Enable Graph Features:
1. Start FalkorDB: `docker-compose up -d falkordb`
2. Start sync service: `bash scripts/start-graph-sync.sh`
3. Initial sync: `curl -X POST http://localhost:8000/api/graph/sync`

### Verification:
- Check health: `curl http://localhost:8000/api/graph/health`
- Should return: `{"status": "healthy", "connected": true}`

## Features
- Semantic similarity detection
- Conflict detection between heuristics
- Related heuristics queries
- 3D knowledge graph visualization

## Maintenance
- Sync runs every 5 minutes automatically
- Manual sync: POST /api/graph/sync
- Stats: GET /api/graph/stats
```

#### Step 6: Testing
- Verify SQLite fallback works (stop FalkorDB)
- Start FalkorDB container
- Run initial full sync
- Create new heuristic → verify node created
- Check relationship detection runs
- Query related heuristics endpoint
- Check conflict detection endpoint
- Verify 3D visualization loads (depends on #29 fix)

---

## Dependencies

### From Other Sprint Groups
- **Issue #29** (ui-polish group): Fix KnowledgeGraph import
  - Blocking: 3D visualization won't display until this is fixed
  - Workaround: Can test API endpoints directly
  - Timeline: Should be completed in parallel

### External Dependencies
- **FalkorDB Docker container**: Already running (verified)
- **Redis Python client**: Already installed (imported in graph_store.py)
- **SQLite database**: Already exists with proper schema

### Cross-File Coordination
- `hooks/learning-loop/post_tool_learning_new.py` will be modified by BOTH issues
  - Issue #32: Add Kanban automation
  - Issue #33: Add relationship detection
  - Solution: Make both additions non-conflicting (different sections)

---

## Blockers/Risks

### Issue #32 Risks
1. **Hook Integration Risk (Medium)**
   - Risk: post_tool_learning_new.py is active production hook
   - Mitigation: Add try/except blocks, feature flags, extensive logging
   - Fallback: Kanban automation fails silently, doesn't break learning loop

2. **CEO Inbox Watcher (Low)**
   - Risk: ceo-inbox/ directory doesn't exist yet
   - Mitigation: Create with .gitkeep, handle missing directory gracefully
   - Alternative: Poll for directory creation

3. **Database Lock Contention (Low)**
   - Risk: Multiple processes writing to kanban_tasks simultaneously
   - Mitigation: SQLite handles this with WAL mode, add timeout=5.0
   - Monitoring: Log any SQLITE_BUSY errors

### Issue #33 Risks
1. **Docker Compose Conflicts (Medium)**
   - Risk: Modifying shared docker-compose.yml
   - Mitigation: FalkorDB already running, just document configuration
   - Alternative: Provide standalone docker run command

2. **Sync Service Reliability (Medium)**
   - Risk: Background service crashes or hangs
   - Mitigation: Implement signal handling, heartbeat logging, auto-restart
   - Monitoring: Log to file, check process health

3. **Relationship Detection Performance (Low)**
   - Risk: Analyzing all heuristics could be slow
   - Mitigation: Only analyze new heuristic against existing ones
   - Optimization: Add thresholds, limit candidates to same domain first

4. **FalkorDB Compatibility (Low)**
   - Risk: Graph store code untested in production
   - Mitigation: Graceful fallback to SQLite always available
   - Testing: Verify fallback mode works before enabling FalkorDB

---

## Estimated Time

### Issue #32: Kanban Automation
- **Core module creation**: 45 minutes
- **Auto-capture integration**: 30 minutes
- **Learning loop integration**: 30 minutes
- **CEO inbox watcher**: 45 minutes
- **Dashboard stats endpoint**: 20 minutes
- **Testing and debugging**: 30 minutes
- **Total**: ~3 hours

### Issue #33: Graph Memory
- **Fix existing issues**: 30 minutes
- **Background sync service**: 1 hour
- **Relationship detection integration**: 45 minutes
- **Docker compose documentation**: 20 minutes
- **Setup documentation**: 30 minutes
- **Testing and verification**: 1.5 hours
- **Total**: ~4.5 hours

### Combined Sprint Total: ~7-8 hours

---

## Success Criteria

### Issue #32 Complete When:
- [ ] New failures auto-create Kanban tasks in "pending"
- [ ] CEO inbox files auto-create tasks in "pending"
- [ ] New heuristics auto-create tasks in "review"
- [ ] Tasks link to source records via linked_learnings/linked_heuristics
- [ ] Task completion auto-triggers on validation/resolution
- [ ] Dashboard stats show auto-creation breakdown
- [ ] CEO inbox watcher runs as background service
- [ ] All integrations have error handling and logging

### Issue #33 Complete When:
- [ ] Graph API endpoints work with SQLite fallback
- [ ] sync_all() typo fixed to full_sync()
- [ ] Background sync service runs reliably
- [ ] New heuristics trigger relationship detection
- [ ] Related heuristics query returns semantically similar items
- [ ] Conflict detection identifies opposing heuristics
- [ ] FalkorDB setup documented in markdown guide
- [ ] Health endpoint reports FalkorDB connection status
- [ ] Graceful degradation when FalkorDB unavailable

---

## Notes

### Architecture Decisions
1. **Kanban automation is event-driven**, not polling-based (except CEO inbox)
2. **Graph sync is time-based** (every 5 minutes), not event-driven
3. **Both services fail gracefully** - never block primary operations
4. **SQLite remains source of truth** - FalkorDB is enhancement layer

### Future Enhancements (Out of Scope)
- Real-time WebSocket notifications for new tasks
- Task assignment to specific agents
- Dependency tracking between tasks
- Advanced graph queries (shortest path, centrality)
- Vector embeddings for semantic similarity (beyond keyword matching)

### Integration Points with Other Work
- **ui-polish group (#29)**: Fixes KnowledgeGraph import for visualization
- **dashboard-fixes group**: May touch same API endpoints
- **hooks group**: Shares post_tool_learning_new.py modifications

---

**Plan Status:** Ready for Implementation
**Next Step:** Begin Issue #32 Step 1 (Create kanban_automation.py)
**Estimated Completion:** End of sprint (within 8 hours)
