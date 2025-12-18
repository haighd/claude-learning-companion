---
title: "CLC Dashboard Overhaul"
status: draft
author: "Dan Haight"
created: 2025-12-18
last_updated: 2025-12-18
version: "1.0"
related_prd: "docs/prd/2025-12-18-dashboard-overhaul.md"
---

# Implementation Plan: CLC Dashboard Overhaul

## Overview

Transform the CLC dashboard from a space-themed, multi-card landing page to a minimal, data-focused interface that enables instant health checks. Primary goal: see CLC health status in <5 seconds.

## Current State Analysis

### Components to Remove
| Component | Path | Reason |
|-----------|------|--------|
| UfoCursor | `frontend/src/components/ui/UfoCursor.tsx` | Space theme - UFO cursor with alien |
| ParticleBackground | `frontend/src/components/ParticleBackground.tsx` | Space theme - animated particles |
| cosmic-view/* | `frontend/src/components/cosmic-view/` | Space theme views (keep Analytics logic) |
| solar-system/* | `frontend/src/components/solar-system/` | Space theme - unused |
| particle-background/* | `frontend/src/components/particle-background/` | Supporting files for ParticleBackground |
| GridView | `frontend/src/components/overview/GridView.tsx` | 3-card domain layout |
| CosmicSettingsContext | `frontend/src/context/CosmicSettingsContext.tsx` | Space theme settings |
| CosmicAudioContext | `frontend/src/context/CosmicAudioContext.tsx` | Space theme sounds |

### Components to Modify
| Component | Path | Changes |
|-----------|------|---------|
| DashboardLayout | `frontend/src/layouts/DashboardLayout.tsx` | Remove space components, fix padding |
| Header | `frontend/src/components/Header.tsx` | Fix spacing, remove cosmic audio |
| TimelineView | `frontend/src/components/TimelineView.tsx` | Add tool type event configs |
| App.tsx | `frontend/src/App.tsx` | Remove cosmic providers, fix overview |
| types.ts | `frontend/src/types.ts` | Extend TimelineEvent types |
| index.css | `frontend/src/index.css` | Remove cosmic styles, fix cursor |
| analytics.py | `backend/routers/analytics.py` | Add workflow_runs to /api/events |

### Components to Keep (No Changes)
- `RunsPanel.tsx` - Reuse for landing page
- `StatsBar.tsx` - Already shows 8 stat cards
- `LearningVelocity.tsx` (Analytics) - User likes it
- All API hooks and WebSocket logic
- Backend API endpoints (except /api/events modification)

## Desired End State

```
┌─────────────────────────────────────────────────────────────────┐
│  CLC Dashboard                              [CEO] [Settings] ●  │
│  ─────────────────────────────────────────────────────────────  │
│  [Overview] [Heuristics] [Runs] [Analytics] [Timeline] [More▾]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐      │
│  │ 41 │ │ 35 │ │  6 │ │ 13 │ │ 50 │ │ 85%│ │ 12 │ │  3 │      │
│  │Runs│ │Pass│ │Fail│ │Heur│ │Lrn │ │Conf│ │Gold│ │Dom │      │
│  └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘      │
│                                                                 │
│  Recent Runs                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ bash-20251218-125247  │ completed │ 12:52 │ 1.2s        │   │
│  │ bash-20251218-125240  │ completed │ 12:52 │ 0.8s        │   │
│  │ task-20251218-122423  │ completed │ 12:24 │ 3.4s        │   │
│  │ ...                                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## What We're NOT Doing

- New features beyond fixing existing functionality
- Mobile/tablet responsive design
- Automated testing (separate effort)
- Changes to Analytics view (user likes it)
- Backend schema changes (tool type already in workflow_name)
- Authentication/authorization

---

## Phase 1: Remove Space Theme

**Goal:** Eliminate all space-themed visual elements

### Step 1.1: Remove UfoCursor from DashboardLayout

**File:** `frontend/src/layouts/DashboardLayout.tsx`

```diff
- import { UfoCursor } from '../components/ui/UfoCursor'
...
- <UfoCursor />
```

### Step 1.2: Remove ParticleBackground from DashboardLayout

**File:** `frontend/src/layouts/DashboardLayout.tsx`

```diff
- import { ParticleBackground } from '../components/ParticleBackground'
...
- <div className="absolute inset-0 z-0 opacity-100 pointer-events-none">
-     <ParticleBackground />
- </div>
```

### Step 1.3: Remove Cosmic Context Providers from App.tsx

**File:** `frontend/src/App.tsx`

```diff
- import { ..., CosmicSettingsProvider, CosmicAudioProvider, useCosmicSettings, ... } from './context'
...
- const { performanceMode } = useCosmicSettings()
- const { setParticleCount } = useTheme()
-
- // Performance Mode Logic
- useEffect(() => {
-   switch (performanceMode) {
-     case 'low': setParticleCount(50); break;
-     case 'medium': setParticleCount(100); break;
-     case 'high': setParticleCount(200); break;
-   }
- }, [performanceMode, setParticleCount])
...
function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <NotificationProvider>
          <DataProvider>
-           <CosmicSettingsProvider>
-             <CosmicAudioProvider>
                <AppContent />
-             </CosmicAudioProvider>
-           </CosmicSettingsProvider>
          </DataProvider>
        </NotificationProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}
```

### Step 1.4: Remove Cosmic Audio from Header

**File:** `frontend/src/components/Header.tsx`

```diff
- import { useCosmicAudio } from '../context/CosmicAudioContext'
...
- const { playHover, playClick } = useCosmicAudio()
...
// Remove all playHover() and playClick() calls
```

### Step 1.5: Fix cursor in CSS

**File:** `frontend/src/index.css`

Find and remove or comment out:
- `.cosmic-cursor-hidden` class
- Any `cursor: none` rules
- Space-themed color variables if present

### Step 1.6: Delete Space Theme Directories

```bash
rm -rf frontend/src/components/cosmic-view/
rm -rf frontend/src/components/solar-system/
rm -rf frontend/src/components/particle-background/
rm frontend/src/components/ui/UfoCursor.tsx
rm frontend/src/components/ParticleBackground.tsx
rm frontend/src/context/CosmicSettingsContext.tsx
rm frontend/src/context/CosmicAudioContext.tsx
```

**Note:** Before deleting `cosmic-view/`, extract `CosmicAnalyticsView` logic if needed for Analytics tab, or update DashboardLayout to use `LearningVelocity` directly.

### Step 1.7: Update Context Index Exports

**File:** `frontend/src/context/index.ts`

Remove exports for deleted contexts.

### Success Criteria - Phase 1

**Automated:**
- `cd frontend && bun run build` completes without errors
- `bun run typecheck` passes

**Manual:**
- Dashboard loads with default system cursor
- No particle animation in background
- No UFO/spaceship visible anywhere
- No console errors about missing components

---

## Phase 2: Fix Landing Page

**Goal:** Replace domain cards with stats + runs overview

### Step 2.1: Update DashboardLayout Overview Rendering

**File:** `frontend/src/layouts/DashboardLayout.tsx`

Replace GridView with direct children rendering:

```diff
- import { GridView } from '../components/overview/GridView'
...
{activeTab === 'overview' && (
-   !selectedDomain ? (
-       <GridView onDomainSelect={onDomainSelect} />
-   ) : (
-       <div className="...">
-           ...
-           {children}
-       </div>
-   )
+   <div className="container mx-auto px-4 py-6">
+       {children}
+   </div>
)}
```

### Step 2.2: Update App.tsx Overview Tab Content

**File:** `frontend/src/App.tsx`

The overview tab already renders StatsBar + HotspotVisualization + AlertsPanel. Modify to show StatsBar + RunsPanel:

```diff
{activeTab === 'overview' && (
-   <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
-       <div className="lg:col-span-2">
-           <HotspotVisualization ... />
-       </div>
-       <div className="space-y-6">
-           <AlertsPanel ... />
-       </div>
-   </div>
+   <div className="space-y-6">
+       <RunsPanel
+           runs={runs.map(r => ({
+               id: String(r.id),
+               agent_type: r.workflow_name || 'unknown',
+               description: `${r.workflow_name || 'Run'} - ${r.phase || r.status}`,
+               status: r.status as any,
+               started_at: r.started_at || r.created_at,
+               completed_at: r.completed_at,
+               duration_ms: r.completed_at && r.started_at
+                   ? new Date(r.completed_at).getTime() - new Date(r.started_at).getTime()
+                   : null,
+               heuristics_used: [],
+               files_touched: [],
+               outcome_reason: r.failed_nodes > 0 ? `${r.failed_nodes} nodes failed` : null,
+           }))}
+           onRetry={handleRetryRun}
+           onOpenInEditor={handleOpenInEditor}
+       />
+   </div>
)}
```

### Step 2.3: Delete GridView Component

```bash
rm frontend/src/components/overview/GridView.tsx
```

Update `frontend/src/components/overview/index.ts` if it exists.

### Success Criteria - Phase 2

**Automated:**
- `bun run build` completes without errors
- `bun run typecheck` passes

**Manual:**
- Landing page shows 8 stat cards at top
- Recent runs list visible below stats
- Can see run status (completed/failed) at a glance
- Health check possible in <5 seconds

---

## Phase 3: Fix Layout Issues

**Goal:** Remove wasted space, fix CEO button alignment

### Step 3.1: Reduce Header Top Margin

**File:** `frontend/src/components/Header.tsx`

```diff
- <header className="sticky top-4 z-50 ...">
+ <header className="sticky top-0 z-50 py-2 ...">
```

### Step 3.2: Reduce Content Padding in DashboardLayout

**File:** `frontend/src/layouts/DashboardLayout.tsx`

```diff
- <div className="relative z-10 container mx-auto px-4 py-8 pt-24 ...">
+ <div className="relative z-10 container mx-auto px-4 py-4 pt-16 ...">
```

Also update any other `pt-24` references to `pt-16` or less.

### Step 3.3: Fix CEO Inbox Button Alignment

**File:** `frontend/src/components/header-components/CeoInboxDropdown.tsx`

Inspect and fix positioning. The dropdown may be using `absolute` positioning that escapes the container. Ensure:
- Dropdown uses `relative` parent positioning
- Dropdown content has proper `right-0` or `left-0` alignment
- No negative margins pushing it outside container

### Step 3.4: Remove glass-panel excessive styling

**File:** `frontend/src/index.css`

Simplify `.glass-panel` class:

```diff
.glass-panel {
-   background: rgba(0, 0, 0, 0.4);
-   backdrop-filter: blur(20px);
-   border: 1px solid rgba(255, 255, 255, 0.1);
+   background: var(--theme-bg-secondary);
+   border: 1px solid var(--theme-border);
+   border-radius: 8px;
}
```

### Success Criteria - Phase 3

**Automated:**
- `bun run build` passes
- `bun run typecheck` passes

**Manual:**
- Content starts closer to navigation (minimal gap)
- CEO inbox button stays within header bounds
- Dropdown opens in correct position
- No wasted vertical space

---

## Phase 4: Fix Timeline Tool Types

**Goal:** Show Bash, Task, MCP, WebFetch in Timeline view

### Step 4.1: Extend TimelineEvent Type

**File:** `frontend/src/types.ts`

```diff
export interface TimelineEvent {
  id: number
  timestamp: string
- event_type: 'task_start' | 'task_end' | 'heuristic_consulted' | 'heuristic_validated' | 'heuristic_violated' | 'failure_recorded' | 'golden_promoted'
+ event_type: 'task_start' | 'task_end' | 'heuristic_consulted' | 'heuristic_validated' | 'heuristic_violated' | 'failure_recorded' | 'golden_promoted' | 'bash_run' | 'task_run' | 'mcp_call' | 'webfetch_call'
  description: string
  metadata: Record<string, any>
  file_path?: string
  line_number?: number
  domain?: string
+ tool_type?: string
}
```

### Step 4.2: Add Event Configs to TimelineView

**File:** `frontend/src/components/TimelineView.tsx`

```diff
+ import { Terminal, Cpu, Globe, Workflow } from 'lucide-react'
...
const eventConfig = {
  task_start: { icon: Play, color: 'bg-sky-500', label: 'Task Started' },
  task_end: { icon: CheckCircle, color: 'bg-emerald-500', label: 'Task Completed' },
  heuristic_consulted: { icon: Brain, color: 'bg-violet-500', label: 'Heuristic Consulted' },
  heuristic_validated: { icon: CheckCircle, color: 'bg-emerald-500', label: 'Heuristic Validated' },
  heuristic_violated: { icon: XCircle, color: 'bg-red-500', label: 'Heuristic Violated' },
  failure_recorded: { icon: AlertTriangle, color: 'bg-orange-500', label: 'Failure Recorded' },
  golden_promoted: { icon: Star, color: 'bg-amber-500', label: 'Golden Promotion' },
+ bash_run: { icon: Terminal, color: 'bg-green-500', label: 'Bash Command' },
+ task_run: { icon: Workflow, color: 'bg-blue-500', label: 'Task Agent' },
+ mcp_call: { icon: Cpu, color: 'bg-purple-500', label: 'MCP Call' },
+ webfetch_call: { icon: Globe, color: 'bg-cyan-500', label: 'Web Fetch' },
}
```

### Step 4.3: Update Backend /api/events to Include Workflow Runs

**File:** `backend/routers/analytics.py`

Modify the `get_events` function to include workflow runs:

```python
@router.get("/events")
async def get_events(limit: int = 50):
    """Get recent events feed including workflow runs."""
    with get_db() as conn:
        cursor = conn.cursor()
        events = []

        # Existing metrics events...
        cursor.execute("""
            SELECT metric_type, metric_name, metric_value, tags, context, timestamp
            FROM metrics
            WHERE timestamp > datetime('now', '-1 hour')
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit // 2,))  # Split limit between metrics and runs

        for row in cursor.fetchall():
            # ... existing logic ...

        # ADD: Recent workflow runs as events
        cursor.execute("""
            SELECT id, workflow_name, status, started_at, completed_at, created_at
            FROM workflow_runs
            WHERE created_at > datetime('now', '-24 hours')
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit // 2,))

        for row in cursor.fetchall():
            r = dict_from_row(row)
            workflow_name = r.get("workflow_name", "unknown")

            # Extract tool type from workflow_name prefix
            tool_type = workflow_name.split('-')[0] if '-' in workflow_name else 'unknown'

            # Map to event type
            event_type_map = {
                'bash': 'bash_run',
                'task': 'task_run',
                'mcp': 'mcp_call',
                'webfetch': 'webfetch_call',
            }
            event_type = event_type_map.get(tool_type, 'task_run')

            events.append({
                "type": event_type,
                "message": f"{tool_type.upper()}: {r['status']}",
                "timestamp": r["started_at"] or r["created_at"],
                "tags": None,
                "context": workflow_name,
                "tool_type": tool_type,
            })

        # Sort all events by timestamp
        events.sort(key=lambda e: e["timestamp"], reverse=True)
        return events[:limit]
```

### Success Criteria - Phase 4

**Automated:**
- `bun run build` passes
- `bun run typecheck` passes
- Backend starts without errors

**Manual:**
- Timeline view shows filter options for all 4 tool types
- Bash runs appear with Terminal icon (green)
- Task runs appear with Workflow icon (blue)
- MCP calls appear with Cpu icon (purple) - if any exist
- WebFetch calls appear with Globe icon (cyan) - if any exist
- Events sorted by timestamp correctly

---

## Phase 5: Aesthetic Polish (P1)

**Goal:** Clean, minimal data-focused appearance

### Step 5.1: Update Color Palette in CSS

**File:** `frontend/src/index.css`

Define minimal color variables:

```css
:root {
  --theme-bg-primary: #0f172a;      /* Dark slate */
  --theme-bg-secondary: #1e293b;    /* Slightly lighter */
  --theme-bg-tertiary: #334155;     /* Card backgrounds */
  --theme-text-primary: #f8fafc;    /* White text */
  --theme-text-secondary: #94a3b8;  /* Muted text */
  --theme-border: #334155;          /* Subtle borders */
  --theme-accent: #3b82f6;          /* Blue accent */
  --theme-success: #22c55e;
  --theme-error: #ef4444;
  --theme-warning: #f59e0b;
}

/* Light mode overrides */
[data-theme="light"] {
  --theme-bg-primary: #f8fafc;
  --theme-bg-secondary: #ffffff;
  --theme-bg-tertiary: #f1f5f9;
  --theme-text-primary: #0f172a;
  --theme-text-secondary: #64748b;
  --theme-border: #e2e8f0;
}
```

### Step 5.2: Remove Cosmic CSS Classes

**File:** `frontend/src/index.css`

Remove or simplify:
- `.cosmic-*` classes
- Gradient text effects (unless wanted)
- Glow effects
- Animation keyframes for space theme

### Step 5.3: Simplify Component Styling

Update components to use CSS variables instead of hardcoded cosmic colors:
- Replace `bg-black/60` with `bg-[var(--theme-bg-secondary)]`
- Replace `text-cyan-400` with `text-[var(--theme-accent)]`
- Replace `border-white/10` with `border-[var(--theme-border)]`

### Success Criteria - Phase 5

**Automated:**
- `bun run build` passes
- No CSS errors in console

**Manual:**
- Clean, professional appearance
- No gradients or glow effects
- Works in both light and dark mode
- Meets WCAG 2.1 AA color contrast

---

## Implementation Order

```
Phase 1 (Space Theme Removal)     ████████░░ 4 hours
Phase 2 (Landing Page)            ████░░░░░░ 2 hours
Phase 3 (Layout Fixes)            ███░░░░░░░ 1.5 hours
Phase 4 (Timeline)                ████░░░░░░ 2 hours
Phase 5 (Polish)                  ██████░░░░ 3 hours
                                  ─────────────────
                                  Total: ~12.5 hours
```

**Recommended approach:** Complete Phases 1-4 first (all P0 requirements), then Phase 5 (P1) as polish.

---

## Rollback Plan

Each phase can be rolled back independently:

1. **Phase 1:** Restore deleted files from git, revert DashboardLayout/App.tsx changes
2. **Phase 2:** Restore GridView, revert DashboardLayout overview rendering
3. **Phase 3:** Revert CSS/padding changes
4. **Phase 4:** Revert TimelineView and analytics.py changes
5. **Phase 5:** Revert CSS variable changes

---

## Testing Checklist

### After Each Phase:
- [ ] `bun run build` passes
- [ ] `bun run typecheck` passes
- [ ] Dashboard loads without console errors
- [ ] WebSocket connection established
- [ ] Navigation between tabs works

### Final Testing:
- [ ] Landing page shows stats + runs in <5 seconds
- [ ] No spaceship/UFO cursor anywhere
- [ ] No particle animations
- [ ] CEO inbox button properly aligned
- [ ] Timeline shows all 4 tool types
- [ ] Analytics view unchanged and working
- [ ] Light/dark mode both work
- [ ] Keyboard navigation functional

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | Dan Haight | Initial plan |
