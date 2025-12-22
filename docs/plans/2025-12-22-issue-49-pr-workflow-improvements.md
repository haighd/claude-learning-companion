# Implementation Plan: PR Workflow Efficiency Improvements

**Issue:** #49 - Improve GitHub PR review and CI/CD workflow efficiency
**Research:** `docs/research/2025-12-22-issue-49-pr-workflow-efficiency.md`
**Status:** Implementation complete - awaiting manual verification
**Estimated Effort:** Medium (3 deliverables)

---

## Scope

Implement **short-term quick wins** from Issue #49:

1. **CI Gate Script** - Prevent `/run-ci` when threads are unresolved
2. **Bulk Thread Resolution Script** - Resolve multiple threads efficiently
3. **Documentation** - Create CONTRIBUTING.md with workflow guide

---

## Deliverable 1: CI Gate Script

### Goal
Prevent wasted CI runs by blocking `/run-ci` until all review threads are resolved.

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `scripts/check-unresolved-threads.sh` | Create | Script to check thread status |
| `.github/workflows/run-ci.yml` | Modify | Add gate check before CI jobs |

### Implementation

#### 1.1 Create `scripts/check-unresolved-threads.sh`

```bash
#!/bin/bash
# Check for unresolved review threads on a PR
# Usage: ./check-unresolved-threads.sh <PR_NUMBER>
# Exit codes: 0 = all resolved, 1 = unresolved threads exist

PR_NUMBER="$1"
REPO="${GITHUB_REPOSITORY:-haighd/claude-learning-companion}"

if [ -z "$PR_NUMBER" ]; then
    echo "Usage: $0 <PR_NUMBER>"
    exit 2
fi

# Query for unresolved review threads
UNRESOLVED=$(gh api graphql -f query='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          isResolved
          comments(first: 1) {
            nodes { body path }
          }
        }
      }
    }
  }
}' -f owner="${REPO%/*}" -f repo="${REPO#*/}" -F pr="$PR_NUMBER" \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length')

if [ "$UNRESOLVED" -gt 0 ]; then
    echo "::error::Found $UNRESOLVED unresolved review thread(s)"
    echo ""
    echo "Please resolve all review threads before running CI."
    echo "Use: gh api graphql to resolve threads, or address the feedback first."
    exit 1
fi

echo "All review threads are resolved. CI can proceed."
exit 0
```

#### 1.2 Modify `.github/workflows/run-ci.yml`

Add thread check to the `check-trigger` job:

```yaml
check-thread-status:
  name: Check Review Threads
  runs-on: ubuntu-latest
  needs: check-trigger
  if: needs.check-trigger.outputs.should_run == 'true'
  steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Check for unresolved threads
      env:
        GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      run: |
        PR_NUMBER=$(gh pr view --json number -q .number)
        chmod +x scripts/check-unresolved-threads.sh
        ./scripts/check-unresolved-threads.sh "$PR_NUMBER"
```

### Acceptance Criteria
- [x] Script exits with code 0 when all threads resolved
- [x] Script exits with code 1 when unresolved threads exist
- [x] CI workflow blocks when threads are unresolved
- [x] Clear error message shown with count of unresolved threads

---

## Deliverable 2: Bulk Thread Resolution Script

### Goal
Enable efficient resolution of multiple review threads at once.

### Files to Create

| File | Action | Purpose |
|------|--------|---------|
| `scripts/resolve-threads.sh` | Create | Bulk thread resolution |

### Implementation

#### 2.1 Create `scripts/resolve-threads.sh`

```bash
#!/bin/bash
# Bulk resolve review threads on a PR
# Usage: ./resolve-threads.sh <PR_NUMBER> [--outdated-only] [--dry-run]

PR_NUMBER="$1"
REPO="${GITHUB_REPOSITORY:-haighd/claude-learning-companion}"
OUTDATED_ONLY=false
DRY_RUN=false

# Parse flags
shift
while [ $# -gt 0 ]; do
    case "$1" in
        --outdated-only) OUTDATED_ONLY=true ;;
        --dry-run) DRY_RUN=true ;;
    esac
    shift
done

if [ -z "$PR_NUMBER" ]; then
    echo "Usage: $0 <PR_NUMBER> [--outdated-only] [--dry-run]"
    exit 2
fi

# Fetch unresolved thread IDs
echo "Fetching unresolved threads for PR #$PR_NUMBER..."

THREADS=$(gh api graphql -f query='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          isOutdated
          comments(first: 1) {
            nodes { body path line }
          }
        }
      }
    }
  }
}' -f owner="${REPO%/*}" -f repo="${REPO#*/}" -F pr="$PR_NUMBER")

# Filter threads
if [ "$OUTDATED_ONLY" = true ]; then
    THREAD_IDS=$(echo "$THREADS" | jq -r '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false and .isOutdated == true) | .id')
else
    THREAD_IDS=$(echo "$THREADS" | jq -r '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false) | .id')
fi

COUNT=$(echo "$THREAD_IDS" | grep -c . || echo 0)

if [ "$COUNT" -eq 0 ]; then
    echo "No unresolved threads found."
    exit 0
fi

echo "Found $COUNT unresolved thread(s)."

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would resolve the following threads:"
    echo "$THREAD_IDS"
    exit 0
fi

# Resolve each thread
RESOLVED=0
FAILED=0

for THREAD_ID in $THREAD_IDS; do
    echo "Resolving thread: $THREAD_ID"
    RESULT=$(gh api graphql -f query='
      mutation($threadId: ID!) {
        resolveReviewThread(input: {threadId: $threadId}) {
          thread { isResolved }
        }
      }' -f threadId="$THREAD_ID" 2>&1)

    if echo "$RESULT" | grep -q '"isResolved":true'; then
        ((RESOLVED++))
    else
        echo "  Failed to resolve: $RESULT"
        ((FAILED++))
    fi
done

echo ""
echo "Summary: $RESOLVED resolved, $FAILED failed"
exit $FAILED
```

### Acceptance Criteria
- [x] Script resolves all unresolved threads by default
- [x] `--outdated-only` flag filters to only outdated threads
- [x] `--dry-run` flag shows what would be resolved without acting
- [x] Clear summary of resolved/failed threads

---

## Deliverable 3: Documentation

### Goal
Create clear documentation for the two-phase PR workflow.

### Files to Create

| File | Action | Purpose |
|------|--------|---------|
| `CONTRIBUTING.md` | Create | Developer workflow guide |

### Implementation

#### 3.1 Create `CONTRIBUTING.md`

```markdown
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
```

### Acceptance Criteria
- [x] Clear explanation of two-phase workflow
- [x] Visual workflow diagram
- [x] Script usage examples
- [x] Rationale for the workflow

---

## Implementation Order

1. **Bulk Thread Resolution Script** (Deliverable 2)
   - Standalone utility, no dependencies
   - Immediately useful for current workflow

2. **CI Gate Script** (Deliverable 1)
   - Depends on having thread checking logic
   - Integrates with existing workflow

3. **Documentation** (Deliverable 3)
   - Can reference the new scripts
   - Final polish on the workflow

---

## Testing Plan

### Script Testing
1. Create test PR with multiple review threads
2. Run `check-unresolved-threads.sh` - should fail
3. Run `resolve-threads.sh --dry-run` - should list threads
4. Run `resolve-threads.sh` - should resolve all
5. Run `check-unresolved-threads.sh` - should pass

### CI Integration Testing
1. Push to PR with unresolved threads
2. Comment `/run-ci` - should be blocked with error
3. Resolve all threads
4. Comment `/run-ci` - should proceed to tests

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| GraphQL rate limits | Batch queries, add retry logic |
| Token permissions | Document required scopes |
| False blocking | Add manual override flag |
| Script failures in CI | Fail gracefully with clear errors |

---

## Success Metrics (from Issue #49)

- [ ] Reduce average CI runs per PR from ~5 to ~2
- [ ] Reduce time from first push to merge by 30%
- [ ] Reduce GitHub Actions minutes usage by 40%
