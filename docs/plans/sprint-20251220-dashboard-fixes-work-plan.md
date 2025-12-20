# Sprint Work Plan: Dashboard Fixes
**Sprint ID:** sprint-20251220-dashboard-fixes
**Group:** dashboard-fixes
**Agent:** frontend-developer
**Worktree:** `/Users/danhaight/.claude/clc-worktrees/sprint-20251220-dashboard-fixes`
**Branch:** `sprint/dashboard-fixes`
**Created:** 2025-12-20

---

## Assigned Issues

| Issue | Title | Priority | Effort | Status |
|-------|-------|----------|--------|--------|
| #35 | [Dashboard] HTML title still shows 'Emergent Learning Framework' | Low | Low | Not Started |
| #34 | [Dashboard] Pages missing scroll functionality | High | Low | Not Started |
| #29 | [Dashboard] KnowledgeGraph component not imported - graph tab broken | High | Low | Not Started |

---

## File Impact Analysis

| File Path | Change Type | Shared? | Risk | Notes |
|-----------|-------------|---------|------|-------|
| `/Users/danhaight/.claude/clc-worktrees/sprint-20251220-dashboard-fixes/dashboard-app/frontend/index.html` | Modify | No | Minimal | Simple text change in title tag |
| `/Users/danhaight/.claude/clc-worktrees/sprint-20251220-dashboard-fixes/dashboard-app/frontend/src/App.tsx` | Modify | Yes | Low | Add missing import statement |
| `/Users/danhaight/.claude/clc-worktrees/sprint-20251220-dashboard-fixes/dashboard-app/frontend/src/layouts/DashboardLayout.tsx` | Modify | Yes | Medium | Add overflow styling to tab container |

**Risk Assessment:**
- **App.tsx** - High-traffic file, shared by all tabs. Missing import causes runtime error on graph tab.
- **DashboardLayout.tsx** - Affects all non-overview/graph/analytics tabs. Styling changes could impact visual layout.
- **index.html** - Isolated change, no dependencies.

---

## Current State Analysis

### Issue #35 - HTML Title (Low Priority)
**Current State:**
- Line 8 of `index.html`: `<title>Emergent Learning Dashboard</title>`
- Should be: `Claude Learning Companion` or similar

**Root Cause:**
- Leftover from original "Emergent Learning Framework" branding
- Not updated during rename to CLC

**Impact:**
- Browser tab shows incorrect title
- No functional impact, cosmetic only

---

### Issue #34 - Missing Scroll Functionality (High Priority)
**Current State:**
- `DashboardLayout.tsx` line 94 has fixed height container: `min-h-[calc(100vh-100px)]`
- No `overflow-y` or `max-h` properties to enable scrolling
- Affects tabs: Heuristics, Timeline, Runs, Workflows, Query, Assumptions, Spikes, Invariants, Fraud

**Root Cause:**
- Container uses `min-h` for minimum height but no maximum constraint
- Missing `overflow-y: auto` or `overflow-y: scroll` CSS property
- Content can grow beyond viewport without scrollbar

**Technical Details:**
- Line 94 applies to all tabs except 'overview', 'graph', 'analytics'
- Current classes: `bg-[var(--theme-bg-secondary)] border border-[var(--theme-border)] p-4 rounded-lg min-h-[calc(100vh-100px)]`
- Need to add: `max-h-[calc(100vh-100px)] overflow-y-auto`

**Impact:**
- Users cannot access content below fold
- Serious UX issue affecting 9+ tabs
- High priority due to accessibility concerns

---

### Issue #29 - KnowledgeGraph Import Missing (High Priority)
**Current State:**
- `App.tsx` line 266 uses `<KnowledgeGraph>` component
- No import statement for `KnowledgeGraph` in imports section (lines 1-22)
- Component exists at `./components/knowledge-graph/`
- `DashboardLayout.tsx` imports it correctly (line 6): `import { KnowledgeGraph } from '../components'`

**Root Cause:**
- Import removed or never added after refactoring
- Component is exported from `components/index.ts` (line 13): `export { KnowledgeGraph } from './knowledge-graph'`
- `components/index.ts` is already imported in `App.tsx` (line 6-18)

**Technical Details:**
- Need to add `KnowledgeGraph` to the import list on line 6-18
- Current imports from './components':
  ```typescript
  import {
    StatsBar,
    HeuristicPanel,
    TimelineView,
    RunsPanel,
    QueryInterface,
    SessionHistoryPanel,
    AssumptionsPanel,
    SpikeReportsPanel,
    InvariantsPanel,
    FraudReviewPanel,
    KanbanBoard
  } from './components'
  ```
- Should add `KnowledgeGraph` to this list

**Impact:**
- Graph tab completely broken - runtime error when clicked
- Critical for users needing knowledge visualization
- High priority

---

## Implementation Steps

### Phase 1: Critical Fixes (High Priority)
Execute in order to unblock graph tab and restore scroll functionality.

#### 1. Fix KnowledgeGraph Import (#29)
**File:** `/Users/danhaight/.claude/clc-worktrees/sprint-20251220-dashboard-fixes/dashboard-app/frontend/src/App.tsx`

**Action:**
- Add `KnowledgeGraph` to the component imports from `'./components'` (lines 6-18)
- Insert alphabetically between `HeuristicPanel` and `QueryInterface`

**Expected Result:**
- Graph tab loads without error
- KnowledgeGraph component renders correctly

**Testing:**
- Navigate to graph tab
- Verify no console errors
- Verify graph renders with controls and legend

**Estimated Time:** 2 minutes

---

#### 2. Add Scroll Functionality to Tab Container (#34)
**File:** `/Users/danhaight/.claude/clc-worktrees/sprint-20251220-dashboard-fixes/dashboard-app/frontend/src/layouts/DashboardLayout.tsx`

**Action:**
- Modify line 94 container classes
- Add `max-h-[calc(100vh-100px)]` to constrain height
- Add `overflow-y-auto` to enable vertical scrolling

**Current:**
```tsx
<div className="bg-[var(--theme-bg-secondary)] border border-[var(--theme-border)] p-4 rounded-lg min-h-[calc(100vh-100px)]">
```

**Updated:**
```tsx
<div className="bg-[var(--theme-bg-secondary)] border border-[var(--theme-border)] p-4 rounded-lg min-h-[calc(100vh-100px)] max-h-[calc(100vh-100px)] overflow-y-auto">
```

**Expected Result:**
- Tabs with long content show vertical scrollbar
- Content scrollable within viewport
- No layout shift or broken styling

**Testing:**
- Navigate to Heuristics tab (likely has long content)
- Verify scrollbar appears if content exceeds viewport
- Navigate to Timeline, Runs, Query tabs
- Verify all scrollable without breaking layout

**Estimated Time:** 5 minutes

---

### Phase 2: Polish (Low Priority)

#### 3. Update HTML Title (#35)
**File:** `/Users/danhaight/.claude/clc-worktrees/sprint-20251220-dashboard-fixes/dashboard-app/frontend/index.html`

**Action:**
- Change line 8 from `<title>Emergent Learning Dashboard</title>`
- To: `<title>Claude Learning Companion</title>`

**Expected Result:**
- Browser tab displays "Claude Learning Companion"
- Consistent with project branding

**Testing:**
- Reload dashboard in browser
- Verify browser tab title

**Estimated Time:** 1 minute

---

## Dependencies

### External Dependencies
- None - all changes are isolated frontend fixes

### Inter-Group Dependencies
- None - no coordination needed with other sprint groups

### Build Dependencies
- Vite dev server may need restart after changes (auto-reload should handle)
- No package.json changes required
- No new dependencies to install

---

## Blockers/Risks

### Potential Risks

#### Risk 1: Scroll Container Height Calculation
**Risk Level:** Low
**Description:** `calc(100vh-100px)` might not account for actual header height
**Mitigation:**
- Test across different viewport sizes
- Verify header height is actually ~100px
- Adjust if needed based on actual measurements

**Fallback:**
- Use `max-h-screen` if calc doesn't work
- Consider using CSS variables for dynamic header height

---

#### Risk 2: Import Ordering Side Effects
**Risk Level:** Minimal
**Description:** Adding import might reveal other missing dependencies
**Mitigation:**
- Component is already exported from barrel file
- DashboardLayout already imports successfully
- No circular dependency concerns

**Fallback:**
- Use direct import path if barrel export fails
- Example: `import KnowledgeGraph from './components/knowledge-graph'`

---

#### Risk 3: Overflow Styling Conflicts
**Risk Level:** Low
**Description:** Adding `overflow-y-auto` might conflict with child component styling
**Mitigation:**
- Test all affected tabs individually
- Check for nested scroll containers
- Verify no visual regressions

**Fallback:**
- Use `overflow-y-scroll` to force scrollbar visibility
- Adjust padding if scrollbar causes layout shift
- Consider `scrollbar-gutter: stable` for consistent layout

---

### Known Issues
- **Issue #34** affects 9+ tabs - comprehensive testing required
- Some tabs (QueryInterface, KanbanBoard) may have their own scroll containers
- Need to verify no double-scrollbar situations

---

## Testing Strategy

### Manual Testing Checklist

#### Pre-Flight
- [ ] Verify worktree is on correct branch (`sprint/dashboard-fixes`)
- [ ] Confirm no uncommitted changes in worktree
- [ ] Start dev server: `cd dashboard-app/frontend && bun run dev`

#### Issue #29 Testing
- [ ] Navigate to Graph tab
- [ ] Verify no console errors
- [ ] Verify KnowledgeGraph renders
- [ ] Test graph interactions (zoom, pan, click nodes)
- [ ] Verify legend and controls visible

#### Issue #34 Testing
For each tab: Heuristics, Timeline, Runs, Workflows, Query, Assumptions, Spikes, Invariants, Fraud
- [ ] Navigate to tab
- [ ] Check if content exceeds viewport
- [ ] Verify scrollbar appears when needed
- [ ] Scroll to bottom of content
- [ ] Verify no layout breaks
- [ ] Check for double scrollbars
- [ ] Test keyboard navigation (arrow keys, page up/down)

#### Issue #35 Testing
- [ ] Reload browser
- [ ] Check browser tab title
- [ ] Verify displays "Claude Learning Companion"

### Browser Compatibility
- Test in Chrome/Edge (primary)
- Verify in Firefox (optional)
- Check Safari (macOS) if available

### Viewport Sizes
- Desktop: 1920x1080
- Laptop: 1440x900
- Small: 1280x720

---

## Estimated Time Breakdown

| Task | Estimated Time | Complexity |
|------|---------------|------------|
| Issue #29 - Add import | 2 minutes | Trivial |
| Issue #34 - Add scroll | 5 minutes | Simple |
| Issue #35 - Update title | 1 minute | Trivial |
| **Implementation Total** | **8 minutes** | - |
| Manual testing | 15 minutes | - |
| Documentation/PR | 10 minutes | - |
| **Grand Total** | **~33 minutes** | - |

---

## Definition of Done

### Code Quality
- [ ] All TypeScript type checks pass
- [ ] No new console errors or warnings
- [ ] Code follows existing patterns and conventions
- [ ] Comments added for non-obvious changes

### Functionality
- [ ] Issue #29: Graph tab loads without errors
- [ ] Issue #34: All tabs scroll correctly when content exceeds viewport
- [ ] Issue #35: Browser tab shows correct title

### Testing
- [ ] Manual testing completed for all affected tabs
- [ ] No visual regressions detected
- [ ] Keyboard navigation works correctly
- [ ] Tested in primary browser (Chrome/Edge)

### Documentation
- [ ] Work plan followed
- [ ] Changes documented in commit messages
- [ ] PR description includes before/after screenshots (for #34)
- [ ] Testing evidence provided

---

## Next Steps After Completion

1. **Commit Changes**
   - Separate commits for each issue
   - Descriptive commit messages
   - Reference issue numbers

2. **Push to Branch**
   - Push to `sprint/dashboard-fixes` branch
   - Verify CI passes (if applicable)

3. **Create Pull Request**
   - Title: "fix(dashboard): resolve title, scroll, and graph import issues"
   - Link to issues #29, #34, #35
   - Include testing evidence
   - Add screenshots for scroll functionality

4. **Coordinate with Team**
   - Notify coordinator of completion
   - Share PR link for review
   - Address any feedback

---

## Notes

### Design Decisions

**Scroll Implementation:**
- Chose `overflow-y-auto` over `overflow-y-scroll` to hide scrollbar when not needed
- Using `max-h` with `calc()` to be consistent with existing `min-h` approach
- Kept padding intact to maintain visual consistency

**Import Organization:**
- Maintained alphabetical ordering in component imports
- Used barrel export to stay consistent with other imports

**Title Choice:**
- "Claude Learning Companion" matches project branding
- Shorter than "Claude Learning Companion Dashboard"
- Aligns with CLI name and documentation

### Future Considerations

**Potential Enhancements (Not in Scope):**
- Add smooth scrolling behavior
- Implement scroll-to-top button for long tabs
- Consider virtual scrolling for performance on large datasets
- Add loading skeletons during tab transitions

**Related Issues to Watch:**
- Performance monitoring for tabs with heavy content
- Accessibility audit for keyboard navigation
- Mobile responsiveness (not currently supported)

---

## Work Plan Status

**Status:** COMPLETED
**Reviewed By:** frontend-developer
**Approved:** Pending coordinator review
**Started:** 2025-12-20
**Completed:** 2025-12-20

### Completion Summary

All three issues successfully resolved and committed:

1. **Issue #29 (HIGH)** - KnowledgeGraph Import - FIXED
   - Commit: b532857
   - Added KnowledgeGraph to component imports in App.tsx
   - Graph tab now functional without runtime errors

2. **Issue #34 (HIGH)** - Scroll Functionality - FIXED
   - Commit: a59bfb7
   - Added max-h and overflow-y-auto to tab containers
   - All tabs now scrollable when content exceeds viewport

3. **Issue #35 (LOW)** - HTML Title - FIXED
   - Commit: 506cb87
   - Updated title to "Claude Learning Companion"
   - Browser tab displays correct branding

4. **Dependencies** - UPDATED
   - Commit: 60a6a3c
   - Updated bun.lock after dependency install
   - Build verification successful

**Branch:** sprint/dashboard-fixes
**Pushed to:** origin
**Build Status:** TypeScript compilation successful
**Ready for:** PR creation and code review
