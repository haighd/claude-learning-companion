# Research: PR Review and CI/CD Workflow Infrastructure

**Date:** 2025-12-22
**Issue:** #49 - Improve GitHub PR review and CI/CD workflow efficiency
**Status:** Complete

---

## Executive Summary

Research into the existing PR review and CI/CD workflow infrastructure reveals a well-documented two-phase workflow (Review → CI) with clear gaps in enforcement tooling. The infrastructure supports GraphQL API operations but lacks scripts to automate thread management and CI gating.

---

## 1. Current Infrastructure

### GitHub Actions Workflows

| Workflow | File | Purpose |
|----------|------|---------|
| Gemini Review Check | `.github/workflows/gemini-review-check.yml` | Ensures `/gemini review` is posted on PRs |
| Run CI | `.github/workflows/run-ci.yml` | Multi-job CI pipeline triggered by `/run-ci` comment |

#### Run CI Pipeline Structure
```
check-trigger → python-checks → run-tests → finalize
     ↓              ↓               ↓           ↓
Permission     Syntax check     Pytest     Add label +
  check          Python         suite      status comment
```

### Documented Workflow (CLAUDE.md)

**Two-Phase Model:**
1. **Phase 1 (Review)**: Push → `/gemini review` → Address feedback → Resolve threads → Repeat until clean
2. **Phase 2 (CI)**: `/run-ci` → Tests run → `ready-to-merge` label added

**Key Rules:**
- Never resolve threads without addressing feedback
- "Outdated" threads must still be acknowledged and resolved
- Agent (not user) triggers `/run-ci`
- No premature CI triggering while reviews active

### GraphQL API (Documented)
```bash
gh api graphql -f query='
  mutation {
    resolveReviewThread(input: {threadId: "THREAD_ID"}) {
      thread { isResolved }
    }
  }
'
```

---

## 2. Gap Analysis

| Issue #49 Requirement | Current Status | Priority |
|----------------------|----------------|----------|
| CI gate (check unresolved threads before `/run-ci`) | Not implemented | High |
| Bulk thread resolution script | Not implemented | High |
| Two-phase workflow documentation | Exists in CLAUDE.md | Low (enhance) |
| Auto-comment thread status after push | Not implemented | Medium |
| Auto-resolve outdated threads | Not implemented | Medium |

---

## 3. Available API Patterns

### REST API (Currently Used)
- `github.rest.issues.listComments()` - List PR comments
- `github.rest.pulls.listReviewComments()` - List review threads
- `github.rest.issues.createComment()` - Post comments
- `github.rest.repos.getCollaboratorPermissionLevel()` - Permission checks
- `github.rest.issues.addLabels()` - Label management

### GraphQL API (Available, Not Yet Implemented)
- `resolveReviewThread(input: {threadId: "..."})` - Resolve single thread
- Can be batched for bulk operations
- Accessible via `gh api graphql` in both workflows and scripts

---

## 4. Implementation Recommendations

### Short-term (Issue #49 Quick Wins)

1. **CI Gate Script** (`scripts/check-unresolved-threads.sh`)
   - Query PR for unresolved review threads via GraphQL
   - Return exit code 1 if threads remain
   - Integrate into `run-ci.yml` check-trigger job

2. **Bulk Thread Resolution** (`scripts/resolve-threads.sh`)
   - Accept PR number as argument
   - Fetch all thread IDs via GraphQL query
   - Resolve each thread via GraphQL mutation
   - Support optional filtering by status (e.g., only "outdated")

3. **Documentation** (`CONTRIBUTING.md` or `docs/PR-WORKFLOW.md`)
   - Visual workflow diagram
   - Script usage examples
   - Troubleshooting guide

### Medium-term Enhancements

4. **Thread Status Bot** (enhance `gemini-review-check.yml`)
   - After each push, comment thread status summary
   - List unresolved threads with links

5. **Auto-resolve Outdated** (new workflow or script)
   - Detect threads on modified lines
   - Auto-resolve with acknowledgment comment

---

## 5. File Locations

| Component | Current Location |
|-----------|-----------------|
| CI Workflow | `.github/workflows/run-ci.yml` |
| Review Check | `.github/workflows/gemini-review-check.yml` |
| Workflow Docs | `~/.claude/CLAUDE.md` (lines 29-154) |
| Scripts Dir | `scripts/` (no PR scripts yet) |

---

## 6. Risks and Considerations

1. **API Rate Limits**: GraphQL has rate limits; bulk operations should be batched carefully
2. **Permissions**: Scripts need appropriate GitHub token permissions
3. **False Positives**: CI gate might block legitimate cases; need override mechanism
4. **Backward Compatibility**: Existing workflow patterns in CLAUDE.md should remain valid

---

## Next Steps

1. Create implementation plan for short-term quick wins
2. Prioritize CI gate script (highest impact on wasted CI minutes)
3. Bulk resolution script (second priority for developer experience)
4. Documentation updates (can be done alongside scripts)
