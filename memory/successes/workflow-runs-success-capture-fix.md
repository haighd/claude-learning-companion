# Success: Fixed ELF Workflow Runs Success Capture

**Date**: 2025-12-15
**Domain**: hooks, ELF

## What Worked

Deep investigation using parallel Explore agents found the root cause of why all 462+ workflow_runs had `status='failed'` with error "No output to analyze".

### Root Cause
The bug was in `~/.claude/hooks/learning-loop/post_tool_learning.py`:
- `determine_outcome()` returns "unknown" when tool_output is empty
- Empty output is common with Task tool using `run_in_background=true`
- The if/else logic treated "unknown" the same as "failure"

### The Fix
Changed from success-first to failure-first logic:
```python
# Before (buggy)
if outcome == 'success':
    mark_completed()
else:  # 'unknown' falls here!
    mark_failed()

# After (fixed)
if outcome == 'failure':
    mark_failed()
else:  # 'success' OR 'unknown'
    mark_completed()
```

## Why It Worked

1. **Optimistic approach**: Learning systems should assume success unless failure is explicit
2. **Background tasks**: Task tool with `run_in_background=true` returns empty output initially
3. **The actual result comes later**: Via TaskOutput when blocking for the result

## Validation

- Before fix: 0 completed, 462+ failed
- After fix: New runs correctly marked as 'completed'
- Test confirmed: 3 new completed entries after fix

## Transferable Heuristic

> When detecting outcome from tool output, use failure-first logic. Treat 'unknown' as success, not failure. Most tasks complete successfully; only explicit failures should be marked as failed.

## Related

- PR #24 to upstream ELF repo
- auto_capture.py success capture job now functional
