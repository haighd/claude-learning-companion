# Contributing to Claude Learning Companion

## PR Workflow

This project uses a two-phase PR workflow to ensure quality and efficient CI usage.

### Phase 1: Review

1. **Push changes** to your feature branch
2. **Request review**: Comment `/gemini review` on the PR
3. **Address feedback**: For each review thread:
   - Implement the suggested change, OR
   - Reply explaining why you disagree
   - Mark thread as "Resolved" after addressing
4. **Repeat** until all threads are resolved

### Phase 2: CI Testing

1. **Trigger CI**: Comment `/run-ci` (only after ALL threads resolved)
2. **Wait for results**: CI runs lint, tests, and E2E checks
3. **If failed**: Fix issues → Push → Back to Phase 1
4. **If passed**: `ready-to-merge` label added automatically

### Workflow Diagram

```
┌─────────────────────────────────────┐
│  PHASE 1: REVIEW                    │
│  Push → /gemini review → Address    │
│  → Resolve threads → Repeat...      │
└─────────────┬───────────────────────┘
              │ All threads resolved
              ▼
        Comment /run-ci
              │
┌─────────────┴───────────────────────┐
│  PHASE 2: CI TESTING                │
│  Lint → Build → Tests → E2E        │
│  Failure → Fix → Back to Phase 1    │
└─────────────┬───────────────────────┘
              │ All tests pass
              ▼
┌─────────────────────────────────────┐
│  READY FOR MERGE                    │
│  → ready-to-merge label added       │
│  → Maintainer merges                │
└─────────────────────────────────────┘
```

### Helper Scripts

**Check thread status:**
```bash
./scripts/check-unresolved-threads.sh <PR_NUMBER>
```

**Bulk resolve threads:**
```bash
# Resolve all unresolved threads
./scripts/resolve-threads.sh <PR_NUMBER>

# Resolve only outdated threads
./scripts/resolve-threads.sh <PR_NUMBER> --outdated-only

# Preview without resolving
./scripts/resolve-threads.sh <PR_NUMBER> --dry-run
```

### Why This Workflow?

- **Prevents wasted CI minutes**: CI only runs when reviews are complete
- **Ensures feedback is addressed**: Threads must be resolved before CI
- **Clear progress tracking**: Labels indicate PR status
