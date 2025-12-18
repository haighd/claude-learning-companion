---
title: "CLC Dashboard Overhaul"
status: draft
author: "Dan Haight"
created: 2025-12-18
last_updated: 2025-12-18
version: "1.0"
---

# PRD: CLC Dashboard Overhaul

## Overview

### Problem Statement
The CLC dashboard has accumulated visual and functional issues that hinder its primary use case: quickly assessing whether the learning system is working correctly. The current landing page is confusing, the space theme is distracting, layout bugs create visual clutter, and the Timeline view doesn't track all tool types.

### Opportunity
A streamlined, data-focused dashboard will make health checks instantaneous and provide a professional, distraction-free interface for monitoring CLC activity.

### Proposed Solution
Overhaul the dashboard with a minimal/data-focused aesthetic, fix layout bugs, replace the landing page with a functional overview, and update the Timeline to track all tool types.

## Users & Stakeholders

### Target Users

#### Primary: CLC Administrator (Dan)
- **Who**: The person running Claude Code with CLC enabled
- **Needs**: Quick health checks, confirmation that learning is happening, access to analytics
- **Pain Points**: Confusing landing page, distracting theme, broken Timeline, wasted screen space

### Stakeholders
- **Claude Agents**: Indirectly benefit from a working CLC system that the dashboard helps monitor

## User Journey

### Current State
User opens dashboard → Sees confusing 3-card landing page with "inspect domains" buttons → Doesn't immediately know if CLC is healthy → Has to navigate to Runs or other views → Distracted by spaceship cursor and space theme → Timeline doesn't show Bash/MCP/WebFetch activity

### Future State
User opens dashboard → Immediately sees 8 stat cards showing key metrics → Scrolls down to see recent runs history → Knows within 5 seconds if CLC is working → Clean, professional interface stays out of the way → Timeline shows all tool activity

## Requirements

### Functional Requirements

#### Must Have (P0)
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-001 | Replace landing page with stats + runs overview | Landing page displays 8 stat cards (matching other pages) with a scrollable recent runs history list below |
| FR-002 | Remove spaceship cursor | Default system cursor used throughout all views |
| FR-003 | Fix CEO inbox button alignment | Button renders within the navigation container bounds |
| FR-004 | Remove wasted vertical space | Content area starts immediately below navigation with standard padding (16-24px max) |
| FR-005 | Fix Timeline to include all tool types | Timeline displays Bash, MCP, WebFetch, and Task tool executions with appropriate icons/labels |
| FR-006 | Remove space theme elements | No particle backgrounds, cosmic imagery, animated space elements, or space-related styling |

#### Should Have (P1)
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-007 | Apply minimal/data-focused aesthetic | Clean typography, subtle shadows, muted color palette, no decorative elements, works in light/dark mode |
| FR-008 | Simplify navigation structure | Remove or consolidate redundant views, clear visual hierarchy |

#### Nice to Have (P2)
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-009 | Add loading states | Skeleton loaders while data fetches, no layout shift |

### Non-Functional Requirements

| Category | Requirement | Target |
|----------|-------------|--------|
| Performance | Initial page load | < 2 seconds |
| Performance | Time to interactive | < 3 seconds |
| Accessibility | Keyboard navigation | Full tab navigation support |
| Accessibility | Color contrast | WCAG 2.1 AA compliance |

## Scope

### In Scope
- Landing page redesign (stats cards + runs history)
- Cursor fix (remove spaceship)
- Layout fixes (CEO button alignment, vertical spacing)
- Timeline view updates (add Bash, MCP, WebFetch support)
- Theme removal (space/cosmic elements)
- Aesthetic update (minimal/data-focused)

### Out of Scope
- New features beyond fixing existing functionality
- Mobile/tablet responsive design (desktop tool)
- Backend API changes (unless required for Timeline)
- Analytics view changes (keep as-is, user likes it)
- Authentication/authorization
- Automated testing (can be separate effort)

### Dependencies
- Backend may need updates if Timeline data structure doesn't include new tool types
- Existing component library (shadcn/ui or similar) for consistent styling

## Success Metrics

### Primary Metrics
| Metric | Baseline | Target |
|--------|----------|--------|
| Time to assess CLC health | ~30s (navigate, find info) | < 5s (glance at landing) |
| Visual bugs | 3+ (cursor, alignment, spacing) | 0 |
| Tool types shown in Timeline | 1 (Task only) | 4 (Task, Bash, MCP, WebFetch) |

### Secondary Metrics
| Metric | Target |
|--------|--------|
| User satisfaction | "It just works, stays out of my way" |
| Components removed/simplified | Net reduction in component count |

### Measurement Plan
- Visual inspection confirms bugs fixed
- Timeline manually tested with each tool type
- User confirms landing page meets needs

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Timeline backend needs update | **Confirmed** | Medium | Data exists; need to add workflow runs to `/api/events` endpoint |
| Removing components breaks other features | Low | Medium | Test each view after changes |
| Aesthetic changes take longer than expected | Medium | Low | Prioritize P0 functional fixes over P1 aesthetic polish |
| Empty DB files cause confusion | Low | Low | Clean up unused `building.db` and `clc.db` (0 bytes) |

## Open Questions

- [x] What aesthetic direction? → Minimal/Clean + Data-focused hybrid
- [x] Does the Timeline API already return tool type information? → **No, but data exists.** Tool type is embedded in `workflow_name` (e.g., `bash-20251218-...`, `task-20251218-...`). Timeline currently shows heuristic events, not workflow runs. Fix requires adding workflow runs to Timeline events feed.
- [ ] Are there other views besides Analytics that should be preserved as-is?

## Technical Investigation Results

### Database Structure
- **Location:** `~/.claude/clc/memory/index.db` (3.4MB with data)
- **Note:** `building.db` and `clc.db` are empty (0 bytes) - may be legacy/unused
- **Tool type data:** Embedded in `workflow_runs.workflow_name` as prefix

### Current Tool Type Coverage
| Tool | Prefix | Count | Tracked by Hooks |
|------|--------|-------|------------------|
| Bash | `bash-` | 41 | Yes |
| Task | `task-` | 9 | Yes |
| MCP | `mcp-` | 0 | Yes (no calls yet) |
| WebFetch | `webfetch-` | 0 | Yes (no calls yet) |

### Timeline Fix Requirements
1. **Frontend `TimelineView.tsx`:** Add event configs for `bash_run`, `task_run`, `mcp_call`, `webfetch_call`
2. **Frontend `types.ts`:** Extend `TimelineEvent.event_type` union with new tool types
3. **Backend `/api/events`:** Include recent workflow runs in events feed, extracting tool type from `workflow_name`
4. **Backend parsing:** Extract tool type with: `workflow_name.split('-')[0]`

## Components Affected

Based on codebase review, likely changes to:

### Remove/Replace
- `ParticleBackground.tsx` - space theme
- `cosmic-view/` directory - space theme
- `solar-system/` directory - space theme
- Landing page 3-card layout

### Modify
- `Header.tsx` - CEO button alignment, spacing
- `App.tsx` or router - landing page content
- `TimelineView.tsx` - add tool type support
- `StatsBar.tsx` - ensure 8 cards display
- Global CSS - cursor, spacing, theme variables

### Keep
- `RunsPanel.tsx` - reuse for landing page history
- Analytics view components
- Core API hooks and WebSocket logic

## Appendix

### Current Dashboard Structure
```
frontend/src/components/
├── AlertsPanel.tsx
├── AnomalyPanel.tsx
├── cosmic-view/          # REMOVE (space theme)
├── Header.tsx            # MODIFY (alignment)
├── hotspot-treemap/
├── knowledge-graph/
├── ParticleBackground.tsx # REMOVE (space theme)
├── RunsPanel.tsx         # REUSE for landing
├── solar-system/         # REMOVE (space theme)
├── StatsBar.tsx          # MODIFY (landing page)
├── TimelineView.tsx      # MODIFY (tool types)
└── ...
```

### Design Direction Reference
- **Minimal/Clean**: Notion, Linear, Raycast
- **Data-focused**: Grafana, Datadog, Vercel Analytics

### Revision History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | Dan Haight | Initial draft |
