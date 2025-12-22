# Contributing to Claude Learning Companion

## PR Workflow

This project uses an automated CI/CD pipeline with dual AI reviewers (Gemini Code Assist and GitHub Copilot).

### What Happens Automatically

1. **Dual AI Reviews**: Both Gemini and Copilot automatically review your PR
2. **Outdated Threads**: Threads on modified code are auto-resolved
3. **Severity-Based CI Gating**: CI only blocks on critical/high findings
4. **Auto-Approval**: Bot approves when all conditions are met
5. **Ready Label**: `ready-to-merge` label added when ready for final merge

### What You Need to Do

1. **Push your changes** - AI reviews trigger automatically
2. **Address critical/high findings** - These block CI (look for `![critical]` or `![high]` badges)
3. **Medium/low are optional** - CI proceeds with these unresolved
4. **Trigger CI**: Comment `/run-ci` when ready
5. **Wait for approval** - Bot approves when conditions met
6. **Maintainer merges** - Final merge requires human approval

### Severity Levels

| Level | Badge | Action Required |
|-------|-------|-----------------|
| Critical | `![critical]` | Must fix before CI |
| High | `![high]` | Must fix before CI |
| Medium | `![medium]` | Recommended but optional |
| Low/Nit | `![low]`, `nit:` | Optional improvement |

### Workflow Diagram

```
┌─────────────────────────────────────┐
│  PUSH CHANGES                       │
│  AI reviews trigger automatically   │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  ADDRESS FEEDBACK                   │
│  Critical/High → Must fix           │
│  Medium/Low → Optional              │
│  Outdated → Auto-resolved           │
└─────────────┬───────────────────────┘
              │ Critical/High resolved
              ▼
        Comment /run-ci
              │
┌─────────────┴───────────────────────┐
│  CI TESTING                         │
│  Lint → Build → Tests               │
│  Failure → Fix → Push again         │
└─────────────┬───────────────────────┘
              │ All tests pass
              ▼
┌─────────────────────────────────────┐
│  AUTO-APPROVAL                      │
│  → Bot approves PR                  │
│  → ready-to-merge label added       │
│  → Maintainer notified              │
└─────────────────────────────────────┘
```

### Helper Scripts

**Check thread status with severity:**
```bash
python3 scripts/categorize-findings.py <PR_NUMBER>
```

**Check for unresolved threads:**
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

- **Dual AI reviewers**: Catches more issues with different perspectives
- **Severity-based gating**: Focus on what matters, don't block on nits
- **Auto-resolution of outdated threads**: Reduces manual cleanup
- **Bot approval**: Removes bottleneck while maintaining quality gates
- **Clear progress tracking**: Labels indicate PR status
