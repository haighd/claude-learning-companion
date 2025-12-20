# Sprint Work Plan: Dashboard Advanced Features
**Sprint**: 2025-12-20 Dashboard Advanced
**Group**: dashboard-advanced
**Agent**: frontend-developer
**Worktree**: `/Users/danhaight/.claude/clc-worktrees/sprint-20251220-dashboard-advanced`
**Branch**: `sprint/dashboard-advanced`

---

## Assigned Issues

| # | Title | Priority | Effort | Est. Time |
|---|-------|----------|--------|-----------|
| #25 | Session Replay - Watch recorded Claude sessions | medium | high | 3-4 days |
| #26 | Synchronized Time-Scrubbing Across All Panels | medium | high | 3-4 days |
| #27 | Debug Stepping for Failed Workflows | medium | high | 2-3 days |

**Total Estimated Time**: 8-11 days (effort:high features require careful incremental delivery)

---

## Current State Analysis

### Existing Infrastructure

**Timeline Component** (`/Users/danhaight/.claude/clc/dashboard-app/frontend/src/components/TimelineView.tsx`):
- Lines 29-33: Playback state management already exists (isPlaying, playbackIndex, speed)
- Lines 52-62: Playback handlers (play/pause, skip back/forward) implemented but non-functional
- Lines 86-120: UI controls present but currently only auto-scroll events
- **Gap**: No actual session data capture, no real playback functionality

**Session Infrastructure** (`/Users/danhaight/.claude/clc/dashboard-app/backend/session_index.py`):
- Full session parsing from `~/.claude/projects/*/*.jsonl` files
- Metadata extraction with lazy loading
- Message-level data available (tool_use, content, timestamps)
- **Gap**: No playback-specific capture (stdout, state snapshots)

**Workflow Infrastructure** (`/Users/danhaight/.claude/clc/dashboard-app/backend/routers/workflows.py`):
- `workflow_runs` table tracks execution
- `node_executions` table exists in schema (`conductor/schema.sql:80`)
- Basic run status tracking
- **Gap**: No detailed state capture at each node

**Data Context** (`/Users/danhaight/.claude/clc/dashboard-app/frontend/src/context/DataContext.tsx`):
- Centralized data management via `useDataContext()`
- WebSocket integration for real-time updates
- Auto-refresh every 10 seconds
- **Gap**: No time-based filtering or historical state queries

---

## File Impact Analysis

| File Path | Change Type | Shared? | Risk |
|-----------|-------------|---------|------|
| `/dashboard-app/frontend/src/components/TimelineView.tsx` | Major refactor | No | Medium - existing playback UI needs real functionality |
| `/dashboard-app/frontend/src/components/SessionReplayPanel.tsx` | New file | No | Low - isolated new component |
| `/dashboard-app/frontend/src/components/session-history/SessionDetail.tsx` | Enhancement | Yes | Low - add replay trigger |
| `/dashboard-app/frontend/src/components/TimeControls.tsx` | New file | Yes | Medium - shared global time scrubber |
| `/dashboard-app/frontend/src/context/TimeContext.tsx` | New file | Yes | High - all panels will depend on this |
| `/dashboard-app/frontend/src/hooks/useTimeTravel.ts` | New file | Yes | Medium - historical data queries |
| `/dashboard-app/frontend/src/hooks/useSessionReplay.ts` | New file | No | Low - isolated hook |
| `/dashboard-app/frontend/src/components/WorkflowDebugger.tsx` | New file | No | Low - isolated new feature |
| `/dashboard-app/backend/routers/sessions.py` | Enhancement | Yes | Medium - add replay endpoints |
| `/dashboard-app/backend/routers/workflows.py` | Enhancement | Yes | Medium - add debug endpoints |
| `/dashboard-app/backend/routers/analytics.py` | Enhancement | Yes | High - time-filtered queries across all data |
| `/dashboard-app/backend/models.py` | Enhancement | Yes | Low - add request/response models |
| `/templates/init_db.sql` | Schema changes | Yes | High - database changes affect all |

**High Risk Files** (require coordination):
- `/dashboard-app/frontend/src/context/TimeContext.tsx` - All panels depend on this
- `/dashboard-app/backend/routers/analytics.py` - Central data source
- `/templates/init_db.sql` - Schema changes require migration

---

## Implementation Steps

### Phase 1: Foundation (Days 1-2) - Time Infrastructure

#### 1.1 Global Time Context (#26 foundation)
**Files**:
- NEW: `/dashboard-app/frontend/src/context/TimeContext.tsx`
- NEW: `/dashboard-app/frontend/src/hooks/useTimeTravel.ts`
- MODIFY: `/dashboard-app/frontend/src/App.tsx`

**Tasks**:
- Create `TimeContext` with state: `{ currentTime: Date | null, timeRange: [Date, Date], isLive: boolean }`
- Implement `useTimeTravel()` hook for time selection
- Wire TimeContext into App root
- Add visual "viewing historical" banner

**Acceptance Criteria**:
- Components can read `currentTime` from context
- Setting time to past shows "Historical View" indicator
- Switching to "Live" clears time filter

**Dependencies**: None
**Blockers**: None

---

#### 1.2 Backend Time-Filtered Queries (#26 backend)
**Files**:
- MODIFY: `/dashboard-app/backend/routers/analytics.py`
- MODIFY: `/dashboard-app/backend/routers/heuristics.py`
- MODIFY: `/dashboard-app/backend/routers/runs.py`
- NEW: `/dashboard-app/backend/utils/time_filters.py`

**Tasks**:
- Add `?at_time=<iso-timestamp>` query param to all GET endpoints
- Add `?time_range=<start>/<end>` query param support
- Implement `get_data_at_time()` helper that filters by timestamps
- Update stats endpoint to calculate metrics for historical ranges
- Add SQL indexes on timestamp columns if missing

**Example**:
```python
# /api/stats?at_time=2025-12-19T15:00:00Z
# Returns stats as they were at 3pm on Dec 19
```

**Acceptance Criteria**:
- GET `/api/stats?at_time=<timestamp>` returns historical stats
- GET `/api/heuristics?at_time=<timestamp>` returns heuristics that existed then
- GET `/api/runs?time_range=<start>/<end>` returns runs in that window

**Dependencies**: Database has timestamps on all tables
**Blockers**: May need to verify timestamp coverage in DB

---

### Phase 2: Session Replay (#25) - Days 3-5

#### 2.1 Session Data Capture Enhancement
**Files**:
- MODIFY: `/dashboard-app/backend/session_index.py`
- NEW: `/dashboard-app/backend/utils/session_capture.py`

**Tasks**:
- Extend session parsing to extract:
  - Tool calls with inputs/outputs (already partially done)
  - Bash command outputs (from tool_use content)
  - File read/write operations with diffs
  - Thinking blocks (already extracted)
- Create playback-optimized data structure:
  ```typescript
  {
    frames: [
      { timestamp, type: 'tool_call', tool: 'Bash', input: '...', output: '...' },
      { timestamp, type: 'file_edit', path: '...', diff: '...' },
      { timestamp, type: 'thinking', content: '...' }
    ]
  }
  ```
- Store in `session_summaries` table or new `session_playback` table

**Acceptance Criteria**:
- Session can be loaded with frame-by-frame playback data
- Each frame has timestamp, type, and content
- Large outputs are truncated with "show more" option

**Dependencies**: Session JSONL parsing works (already implemented)
**Blockers**: Need to test with real session files to ensure parsing quality

---

#### 2.2 Replay UI Component
**Files**:
- NEW: `/dashboard-app/frontend/src/components/SessionReplayPanel.tsx`
- NEW: `/dashboard-app/frontend/src/hooks/useSessionReplay.ts`
- MODIFY: `/dashboard-app/frontend/src/components/session-history/SessionDetail.tsx`

**Tasks**:
- Create `<SessionReplayPanel>` with three-pane layout:
  - Left: Terminal output (bash commands/results)
  - Center: File viewer with syntax highlighting + diffs
  - Right: Agent reasoning (thinking blocks)
- Implement `useSessionReplay(sessionId)` hook:
  - Load frames from backend
  - Track current frame index
  - Auto-play with configurable speed
  - Pause/resume, skip forward/back
- Add "Watch Replay" button to `SessionDetail` component
- Implement scrub bar with event markers

**Acceptance Criteria**:
- User clicks "Watch Replay" on a session
- Playback shows commands, outputs, file changes, thinking in sync
- Speed controls work (0.5x, 1x, 2x, 5x)
- Scrub bar allows jumping to any frame

**Dependencies**: 2.1 complete (session data capture)
**Blockers**: None

---

#### 2.3 Replay Backend Endpoints
**Files**:
- MODIFY: `/dashboard-app/backend/routers/sessions.py`
- MODIFY: `/dashboard-app/backend/models.py`

**Tasks**:
- Add `GET /api/sessions/{id}/replay` endpoint
  - Returns `{ frames: [...], metadata: {...} }`
- Add `GET /api/sessions/{id}/replay/frame/{index}` for lazy loading
- Add frame caching to prevent re-parsing

**Acceptance Criteria**:
- Endpoint returns playback frames in correct order
- Supports pagination for long sessions
- Response time < 500ms for typical sessions

**Dependencies**: 2.1 complete
**Blockers**: None

---

### Phase 3: Synchronized Time Scrubbing (#26) - Days 6-8

#### 3.1 Global Time Scrubber Component
**Files**:
- NEW: `/dashboard-app/frontend/src/components/TimeControls.tsx`
- MODIFY: `/dashboard-app/frontend/src/layouts/DashboardLayout.tsx`

**Tasks**:
- Create `<TimeControls>` component with:
  - Date/time range picker
  - Presets (Last Hour, Last Day, Last Week, Custom)
  - "Live" toggle
  - Play/pause for auto-progression through time
  - Speed controls
  - Event markers on timeline (failures, promotions, etc.)
- Mount in header or as floating panel
- Connect to `TimeContext`

**Acceptance Criteria**:
- User can select time range via UI
- "Live" mode shows real-time data
- Historical mode shows banner "Viewing data as of [timestamp]"
- Play button auto-advances through timeline

**Dependencies**: 1.1 complete (TimeContext)
**Blockers**: None

---

#### 3.2 Panel Time Synchronization
**Files**:
- MODIFY: `/dashboard-app/frontend/src/components/HeuristicPanel.tsx`
- MODIFY: `/dashboard-app/frontend/src/components/RunsPanel.tsx`
- MODIFY: `/dashboard-app/frontend/src/components/StatsBar.tsx`
- MODIFY: `/dashboard-app/frontend/src/components/AnomalyPanel.tsx`
- MODIFY: `/dashboard-app/frontend/src/hooks/useDashboardData.ts`

**Tasks**:
- Update `useDashboardData()` to accept `timeFilter` param
- Modify all data fetching to include `?at_time=` or `?time_range=`
- Add loading states during historical data fetch
- Cache historical snapshots to prevent excessive queries

**Acceptance Criteria**:
- When time is changed, all panels re-fetch data
- Historical data displays correctly
- Loading states are visible during fetch
- No unnecessary re-renders

**Dependencies**: 1.2 complete (backend time queries), 3.1 complete (time controls)
**Blockers**: None

---

#### 3.3 Snap-to-Event Feature
**Files**:
- MODIFY: `/dashboard-app/frontend/src/components/TimeControls.tsx`
- MODIFY: `/dashboard-app/frontend/src/hooks/useTimeTravel.ts`

**Tasks**:
- Add "Previous Event" / "Next Event" buttons
- Fetch significant events from `/api/events?significant=true`
- Implement jump-to-event logic
- Highlight event in timeline

**Acceptance Criteria**:
- "Next Event" jumps to next significant timestamp
- Event marker is highlighted
- All panels update to show state at that event

**Dependencies**: 3.1, 3.2 complete
**Blockers**: Need to define "significant events" (failures, golden rule promotions, etc.)

---

### Phase 4: Workflow Debugger (#27) - Days 9-11

#### 4.1 Workflow State Capture Enhancement
**Files**:
- MODIFY: `/dashboard-app/backend/routers/workflows.py`
- NEW: `/dashboard-app/backend/utils/workflow_debugger.py`
- MODIFY: `/templates/init_db.sql` (add `node_state_snapshots` table)

**Tasks**:
- Extend `node_executions` table to capture:
  - Input data (JSON)
  - Output data (JSON)
  - Error details (if failed)
  - Heuristics consulted (list of IDs)
  - Context at execution time
- Add `node_state_snapshots` table:
  ```sql
  CREATE TABLE node_state_snapshots (
    id INTEGER PRIMARY KEY,
    execution_id INTEGER NOT NULL,
    snapshot_type TEXT, -- 'pre', 'post', 'error'
    state_data TEXT, -- JSON
    timestamp DATETIME,
    FOREIGN KEY (execution_id) REFERENCES node_executions(id)
  );
  ```
- Modify workflow execution to capture state

**Acceptance Criteria**:
- Each node execution has pre/post state snapshots
- Errors include full context
- Heuristics applied are recorded

**Dependencies**: Database migration strategy
**Blockers**: Need to coordinate with backend-developer on schema changes

---

#### 4.2 Debug Stepping UI
**Files**:
- NEW: `/dashboard-app/frontend/src/components/WorkflowDebugger.tsx`
- NEW: `/dashboard-app/frontend/src/hooks/useWorkflowDebugger.ts`
- MODIFY: `/dashboard-app/frontend/src/components/runs/RunDetail.tsx`

**Tasks**:
- Create `<WorkflowDebugger>` component with:
  - Workflow graph visualization (nodes + edges)
  - Current node highlight
  - State inspector panel (inputs, outputs, errors)
  - Step controls (prev/next node)
  - Failure point indicator
  - Heuristics panel (which rules applied, which were violated)
- Add "Debug" button to failed runs in `RunDetail`
- Implement step-through logic

**Acceptance Criteria**:
- User can step through failed workflow node by node
- Each step shows inputs, outputs, and state
- Failure node is clearly marked
- Heuristics violations are displayed

**Dependencies**: 4.1 complete (state capture)
**Blockers**: None

---

#### 4.3 Debug Backend Endpoints
**Files**:
- MODIFY: `/dashboard-app/backend/routers/workflows.py`
- MODIFY: `/dashboard-app/backend/models.py`

**Tasks**:
- Add `GET /api/workflows/runs/{id}/debug` endpoint:
  - Returns workflow structure + execution trace
  - Includes state snapshots for each node
  - Returns heuristics applied/violated
- Add `GET /api/workflows/runs/{id}/nodes/{node_id}/state`
  - Returns detailed state for specific node execution

**Acceptance Criteria**:
- Debug endpoint returns full execution trace
- State snapshots are included
- Response format is optimized for debugger UI

**Dependencies**: 4.1 complete
**Blockers**: None

---

## Sprint Scope Decision

### INCLUDE in Sprint (Must-Have)

**Issue #26 - Time Scrubbing (PRIORITY)**:
- Phase 1: Foundation (1.1, 1.2) - Days 1-2
- Phase 3.1: Time Controls UI - Day 6
- Phase 3.2: Panel Synchronization - Day 7

**Rationale**: Time infrastructure is foundational for other features. Get this working first.

**Issue #25 - Session Replay (MVP)**:
- Phase 2.1: Basic data capture - Day 3
- Phase 2.2: Simple replay UI (terminal + thinking only) - Days 4-5
- DEFER: Advanced features (file diffs, scrub bar)

**Rationale**: Deliver basic "watch what Claude did" functionality. Polish later.

**Issue #27 - Workflow Debugger (Simple Version)**:
- Phase 4.1: Basic state capture (inputs/outputs only) - Day 8
- Phase 4.2: Simple step-through UI - Days 9-10
- DEFER: Heuristics integration, graph visualization

**Rationale**: Deliver basic debugger. Advanced features are polish.

### DEFER to Future Sprint

- Session Replay: File diff viewer, advanced scrub bar
- Time Scrubbing: Snap-to-event feature (#26.3)
- Workflow Debugger: Full graph visualization, heuristics violation display
- Performance optimizations (caching, lazy loading)

---

## Dependencies

### From Other Groups
- **backend-developer**:
  - Database schema validation (node_executions, timestamps)
  - Migration strategy for schema changes
  - Review of time-filtered query performance

- **qa-expert**:
  - Test data generation (historical sessions, workflow runs)
  - Performance testing for time queries

### Internal Dependencies (Sequential)
1. TimeContext must exist before any panel can use time filtering
2. Backend time queries must work before frontend can fetch historical data
3. Session data capture must exist before replay UI can display anything
4. Workflow state capture must exist before debugger can step through

---

## Blockers / Risks

### High Risk
1. **Database Performance**: Time-filtered queries across all data could be slow
   - **Mitigation**: Add indexes on timestamp columns, implement caching
   - **Fallback**: Limit historical range to last 30 days initially

2. **Schema Changes**: Adding `node_state_snapshots` table requires migration
   - **Mitigation**: Coordinate with backend-developer, use migration script
   - **Fallback**: Store state as JSON in existing `node_executions` table

3. **Context Flooding**: Large session replays could overwhelm UI
   - **Mitigation**: Implement pagination, lazy loading, truncation
   - **Fallback**: Limit replay to last N frames (e.g., 100)

### Medium Risk
1. **WebSocket Integration**: Real-time updates + historical view might conflict
   - **Mitigation**: Disable WebSocket updates when in historical mode
   - **Fallback**: Require page refresh to return to live view

2. **Shared Component Changes**: TimeControls affects all dashboard panels
   - **Mitigation**: Make time filtering opt-in per panel initially
   - **Fallback**: Feature flag for time scrubbing

### Low Risk
1. **Session Parsing Quality**: JSONL files may have unexpected formats
   - **Mitigation**: Add error handling, fallback to basic display
   - **Test Early**: Load real session files on Day 3

---

## Testing Strategy

### Unit Tests (Required)
- `TimeContext`: State management, time selection logic
- `useTimeTravel`: Hook behavior, time range calculations
- `useSessionReplay`: Frame loading, playback controls

### Integration Tests (Required)
- Time scrubber updates all panels correctly
- Historical data fetch returns correct results
- Session replay displays frames in order

### Manual Tests (Required)
- Load session from 2 days ago, verify all data matches that time
- Step through failed workflow, verify state is correct
- Play session replay, verify terminal output matches session file

### Performance Tests (Nice to Have)
- Time-filtered query performance with 10k runs
- Session replay with 500+ frames
- Panel update latency when changing time

---

## Estimated Time Breakdown

| Phase | Tasks | Estimated Days |
|-------|-------|----------------|
| 1. Foundation | TimeContext + backend time queries | 2 days |
| 2. Session Replay MVP | Data capture + basic UI | 3 days |
| 3. Time Scrubbing | Global scrubber + panel sync | 2 days |
| 4. Workflow Debugger | State capture + stepping UI | 3 days |
| **Total** | | **10 days** |

**Buffer**: 1-2 days for unexpected issues, testing, polish

**Realistic Sprint Goal**: Complete Phases 1-3 (7 days), partial Phase 4

---

## Success Criteria

### Must Have (Sprint Success)
- [ ] User can select a historical time and see dashboard state at that moment
- [ ] User can watch basic replay of a Claude session (commands + thinking)
- [ ] User can step through failed workflow node-by-node and see inputs/outputs

### Should Have (Nice to Have)
- [ ] Session replay includes file diffs
- [ ] Time scrubber has event markers
- [ ] Workflow debugger shows heuristics violations

### Won't Have (Future Sprint)
- Advanced scrub bar features
- Performance optimizations
- Full graph visualization for debugger

---

## Coordination Notes

### Daily Check-ins Required
- Sync with backend-developer on schema changes (Day 1, 8)
- Sync with qa-expert on test data (Day 3, 6)

### Code Review Strategy
- Phase 1: Submit PR early (Day 2) for foundation review
- Incremental PRs per phase to avoid massive review
- Tag reviewers explicitly for high-risk files (TimeContext, analytics.py)

### Documentation Required
- API documentation for time-filtered endpoints
- User guide for session replay feature
- Developer guide for adding time-aware components

---

## Next Steps (After Plan Approval)

1. Wait for CEO approval of this plan
2. Coordinate with backend-developer on database schema
3. Set up worktree and branch
4. Begin Phase 1.1 (TimeContext implementation)
5. Submit incremental PRs as phases complete

---

**Plan Status**: DRAFT - Awaiting CEO Approval
**Created**: 2025-12-20
**Author**: frontend-developer agent
