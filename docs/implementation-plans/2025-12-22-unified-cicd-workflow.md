---
title: "Unified CI/CD Workflow with Dual AI Reviewers"
created: 2025-12-22
status: draft
related_prd: "docs/prd/2025-12-22-unified-cicd-workflow.md"
related_issue: 49
author: Claude Agent
---

# Implementation Plan: Unified CI/CD Workflow

## Overview

Implement a 4-phase automated CI/CD pipeline that leverages dual AI reviewers (Gemini + Copilot), gates CI on review thread resolution, enables bot-based auto-approval, and includes disk space management for reliable CI execution.

**Goals:**
- Reduce manual steps from 6+ to 2
- Cut CI runs per PR from ~5 to ~2
- Improve code quality through dual-reviewer coverage
- Free CEO time for high-value decisions only
- Prevent CI failures due to disk exhaustion

---

## Current State Analysis

### Existing Infrastructure

| Component | Location | Status |
|-----------|----------|--------|
| Gemini review trigger | `.github/workflows/gemini-review-check.yml` | Active - auto-posts `/gemini review` marker |
| CI pipeline | `.github/workflows/run-ci.yml` | Active - triggered by `/run-ci` comment |
| Thread check script | PR #50 `scripts/check-unresolved-threads.sh` | Not merged |
| Thread resolve script | PR #50 `scripts/resolve-threads.sh` | Not merged |
| Copilot integration | Not configured | Needs repository ruleset |
| Bot account | Does not exist | Needs creation |

### Current Workflow Pain Points

1. Manual `/gemini review` trigger (partially automated via reminder comment)
2. No Copilot in workflow (missing bug detection coverage)
3. Manual thread resolution (442 threads across 7 recent PRs)
4. No CI gating on thread status (wasted Actions minutes)
5. No automated approval path (CEO bottleneck)
6. Disk space exhaustion in CI (reported by other agents)

---

## Desired End State

```
PR Created/Updated
       │
       ▼
[AUTO] Both Gemini & Copilot triggered
       │
       ▼
[AUTO] Disk space freed before heavy jobs
       │
       ▼
[AUTO] Findings categorized by severity
       │
       ▼
[AUTO] Outdated threads auto-resolved
       │
       ▼
Agent addresses only critical/high findings  ← MANUAL (reduced)
       │
       ▼
[AUTO] CI runs when all threads resolved
       │
       ▼
[AUTO] Bot approves when CI passes
       │
       ▼
[AUTO] "ready-to-merge" label added
       │
       ▼
[AUTO] CEO notified (consolidated)
       │
       ▼
CEO scans and merges  ← MANUAL (streamlined)
```

---

## What We're NOT Doing

| Exclusion | Reason |
|-----------|--------|
| Auto-merge | CEO retains merge authority per policy |
| Custom ML classification | Too complex for v1; use reviewer priority badges |
| Multi-repo support | Focus on CLC repo first |
| Email notifications | Reduce email; use Slack instead (P2) |
| Real-time dashboard updates | Polling sufficient for v1 |

---

## Implementation Approach

### Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Disk cleanup | `jlumbroso/free-disk-space` action | Well-maintained, configurable, recovers 20-30GB |
| Auto-approval | `hmarr/auto-approve-action@v4` | Simple, widely used, PAT-based |
| Thread checking | Custom bash script (PR #50) | Already written, tailored to our needs |
| Copilot trigger | Repository ruleset | GitHub's recommended approach (2025) |
| Notifications | GitHub API + Slack webhook | Standard integrations |

### Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| Merge PR #50 | CEO | Ready to merge |
| Create `haighd-bot` account | CEO | Not started |
| Bot PAT generation | CEO | Not started |
| Copilot ruleset config | CEO (repo settings) | Not started |

---

## Phase 1: Foundation (P0 Core)

**Goal:** Establish infrastructure for dual-reviewer workflow with CI gating and disk management

### Task 1.1: Merge PR #50

**Description:** Merge the existing thread check/resolve scripts into main

**Files involved:**
- `scripts/check-unresolved-threads.sh` (from PR #50)
- `scripts/resolve-threads.sh` (from PR #50)
- `CONTRIBUTING.md` (from PR #50)

**Actions:**
1. CEO merges PR #50
2. Verify scripts are accessible in main branch

**Success criteria:**
- [ ] `scripts/check-unresolved-threads.sh` exists in main
- [ ] `scripts/resolve-threads.sh` exists in main
- [ ] Scripts execute without error: `bash scripts/check-unresolved-threads.sh --help`

---

### Task 1.2: Add Disk Cleanup to CI Workflow

**Description:** Add disk space management to prevent CI failures from exhaustion

**File:** `.github/workflows/run-ci.yml`

**Changes:**

Add as first step in jobs that need disk space (before checkout):

```yaml
jobs:
  python-checks:
    runs-on: ubuntu-latest
    steps:
      - name: Free disk space
        uses: jlumbroso/free-disk-space@main
        with:
          tool-cache: false      # Keep for faster subsequent runs
          android: true          # Remove Android SDK (~10GB)
          dotnet: true           # Remove .NET SDK (~2GB)
          haskell: true          # Remove Haskell (~5GB)
          large-packages: true   # Remove large packages (~5GB)
          docker-images: false   # Keep if using Docker
          swap-storage: false    # Keep swap for memory-heavy tasks

      - name: Check available disk space
        run: |
          echo "Available disk space:"
          df -h /
          AVAIL=$(df / | awk 'NR==2 {print $4}' | sed 's/G//')
          if (( $(echo "$AVAIL < 10" | bc -l) )); then
            echo "::error::Less than 10GB available. Failing early."
            exit 1
          fi

      - uses: actions/checkout@v4
      # ... rest of job
```

**Success criteria:**
- [ ] Disk cleanup step runs before heavy operations
- [ ] Disk space check fails fast if below 10GB threshold
- [ ] CI completes successfully with adequate disk space

---

### Task 1.3: Configure Copilot Automatic Review

**Description:** Enable GitHub Copilot to automatically review PRs via repository ruleset

**Location:** Repository Settings → Rules → Rulesets

**Actions:**
1. Navigate to repo settings → Rules → Rulesets
2. Create new ruleset or edit existing
3. Add rule: "Copilot automatic review"
4. Enable options:
   - [x] Review on PR creation
   - [x] Review new pushes
   - [ ] Review draft PRs (optional)

**Success criteria:**
- [ ] Copilot automatically comments on new PRs within 5 minutes
- [ ] Copilot re-reviews on subsequent pushes
- [ ] No manual trigger needed

---

### Task 1.4: Update Gemini Workflow for Dual-Reviewer Awareness

**Description:** Modify `gemini-review-check.yml` to verify both reviewers are triggered

**File:** `.github/workflows/gemini-review-check.yml`

**Changes:**

Update the workflow to check for both reviewer markers:

```yaml
- name: Check for AI reviewer activity
  uses: actions/github-script@v7
  with:
    script: |
      const { data: comments } = await github.rest.issues.listComments({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: context.payload.pull_request.number,
        per_page: 100
      });

      const { data: reviews } = await github.rest.pulls.listReviews({
        owner: context.repo.owner,
        repo: context.repo.repo,
        pull_number: context.payload.pull_request.number
      });

      const geminiActive = comments.some(c =>
        c.body?.toLowerCase().includes('/gemini review') ||
        c.user?.login?.includes('gemini')
      );

      const copilotActive = reviews.some(r =>
        r.user?.login === 'github-actions[bot]' ||
        r.user?.login?.includes('copilot')
      ) || comments.some(c =>
        c.user?.login?.includes('copilot')
      );

      console.log(`Gemini active: ${geminiActive}`);
      console.log(`Copilot active: ${copilotActive}`);

      if (!geminiActive) {
        // Post Gemini trigger (existing logic)
      }

      // Copilot is auto-triggered via ruleset, just log status
      core.setOutput('both_active', geminiActive && copilotActive);
```

**Success criteria:**
- [ ] Workflow logs show both reviewer statuses
- [ ] Gemini trigger still works if missing
- [ ] No false negatives on Copilot detection

---

### Task 1.5: Integrate Thread Check into CI Gate

**Description:** Block `/run-ci` if unresolved threads exist

**File:** `.github/workflows/run-ci.yml`

**Changes:**

Add thread check job before python-checks:

```yaml
jobs:
  check-trigger:
    # ... existing trigger logic

  check-threads:
    needs: check-trigger
    if: needs.check-trigger.outputs.should_run == 'true'
    runs-on: ubuntu-latest
    outputs:
      threads_resolved: ${{ steps.check.outputs.resolved }}
    steps:
      - uses: actions/checkout@v4

      - name: Check for unresolved threads
        id: check
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          PR_NUMBER=${{ needs.check-trigger.outputs.pr_number }}

          # Use the merged script from PR #50
          UNRESOLVED=$(bash scripts/check-unresolved-threads.sh $PR_NUMBER 2>/dev/null || echo "0")

          if [ "$UNRESOLVED" -gt 0 ]; then
            echo "resolved=false" >> $GITHUB_OUTPUT
            echo "::error::$UNRESOLVED unresolved review threads. Please address all feedback before running CI."
          else
            echo "resolved=true" >> $GITHUB_OUTPUT
            echo "All review threads resolved."
          fi

      - name: Post thread status
        if: steps.check.outputs.resolved == 'false'
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: ${{ needs.check-trigger.outputs.pr_number }},
              body: '⚠️ CI blocked: There are unresolved review threads.\n\nPlease address all reviewer feedback and resolve the threads, then run `/run-ci` again.'
            });

  python-checks:
    needs: [check-trigger, check-threads]
    if: needs.check-threads.outputs.threads_resolved == 'true'
    # ... rest of existing job with disk cleanup added
```

**Success criteria:**
- [ ] CI fails with clear message if threads unresolved
- [ ] CI proceeds normally when all threads resolved
- [ ] Error message posted to PR as comment

---

### Phase 1 Exit Criteria

| Criterion | Verification |
|-----------|--------------|
| PR #50 merged | `ls scripts/check-unresolved-threads.sh` returns file |
| Disk cleanup active | CI logs show "Free disk space" step completing |
| Copilot auto-reviews | New PR receives Copilot comment within 5 min |
| Thread gating works | `/run-ci` blocked when threads unresolved |
| Thread gating passes | `/run-ci` proceeds when threads resolved |

---

## Phase 2: Auto-Approval (P0 Complete)

**Goal:** Enable automated PR approval via dedicated bot account

### Task 2.1: Create Bot Account and PAT

**Description:** Create `haighd-bot` GitHub account with appropriate permissions

**Actions (CEO):**
1. Create new GitHub account: `haighd-bot`
2. Add `haighd-bot` as repository collaborator with write access
3. Generate PAT for `haighd-bot`:
   - Scope: `repo` (full control)
   - Expiration: 90 days (quarterly rotation)
4. Add PAT as repository secret: `BOT_PAT`

**Success criteria:**
- [ ] `haighd-bot` account exists
- [ ] Account has write access to repository
- [ ] `BOT_PAT` secret configured in repository settings

---

### Task 2.2: Create Auto-Approval Workflow

**Description:** Workflow that approves PRs when all conditions are met

**File:** `.github/workflows/auto-approve.yml` (new file)

```yaml
name: Auto Approve PR

on:
  workflow_run:
    workflows: ["Run CI"]
    types: [completed]

jobs:
  auto-approve:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'success'

    steps:
      - name: Get PR number from workflow run
        id: get-pr
        uses: actions/github-script@v7
        with:
          script: |
            const { data: { pull_requests } } = await github.rest.actions.getWorkflowRun({
              owner: context.repo.owner,
              repo: context.repo.repo,
              run_id: context.payload.workflow_run.id
            });

            if (pull_requests.length === 0) {
              core.setFailed('No PR associated with this workflow run');
              return;
            }

            const prNumber = pull_requests[0].number;
            core.setOutput('pr_number', prNumber);
            console.log(`PR number: ${prNumber}`);

      - name: Check approval conditions
        id: conditions
        uses: actions/github-script@v7
        with:
          script: |
            const prNumber = ${{ steps.get-pr.outputs.pr_number }};

            // Check for unresolved threads
            const { data: reviews } = await github.rest.pulls.listReviews({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: prNumber
            });

            // Check for existing approvals (don't double-approve)
            const hasApproval = reviews.some(r => r.state === 'APPROVED');
            if (hasApproval) {
              console.log('PR already has an approval');
              core.setOutput('should_approve', 'false');
              return;
            }

            // Check labels for any blocking conditions
            const { data: pr } = await github.rest.pulls.get({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: prNumber
            });

            const hasBlockingLabel = pr.labels.some(l =>
              ['do-not-merge', 'needs-discussion', 'blocked'].includes(l.name.toLowerCase())
            );

            if (hasBlockingLabel) {
              console.log('PR has blocking label');
              core.setOutput('should_approve', 'false');
              return;
            }

            core.setOutput('should_approve', 'true');

      - name: Approve PR
        if: steps.conditions.outputs.should_approve == 'true'
        uses: hmarr/auto-approve-action@v4
        with:
          github-token: ${{ secrets.BOT_PAT }}
          pull-request-number: ${{ steps.get-pr.outputs.pr_number }}

      - name: Add ready-to-merge label
        if: steps.conditions.outputs.should_approve == 'true'
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.addLabels({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: ${{ steps.get-pr.outputs.pr_number }},
              labels: ['ready-to-merge']
            });

      - name: Notify PR
        if: steps.conditions.outputs.should_approve == 'true'
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: ${{ steps.get-pr.outputs.pr_number }},
              body: '✅ **Auto-approved by haighd-bot**\n\nAll conditions met:\n- CI passed\n- All review threads resolved\n- No blocking labels\n\nThis PR is ready for @haighd to merge.'
            });
```

**Success criteria:**
- [ ] Workflow triggers after successful CI run
- [ ] Bot approval appears on PR
- [ ] `ready-to-merge` label added
- [ ] Notification comment posted

---

### Task 2.3: Update run-ci.yml to Remove Duplicate Labeling

**Description:** Remove `ready-to-merge` labeling from run-ci.yml since auto-approve handles it

**File:** `.github/workflows/run-ci.yml`

**Changes:**
- Remove the `addLabels` call from the finalize job
- Keep the success/failure comments

**Success criteria:**
- [ ] No duplicate `ready-to-merge` labels
- [ ] Label only added after bot approval

---

### Phase 2 Exit Criteria

| Criterion | Verification |
|-----------|--------------|
| Bot account active | `haighd-bot` visible as collaborator |
| Auto-approval works | Bot approves test PR meeting conditions |
| Label applied | `ready-to-merge` appears after approval |
| CEO notified | Comment mentions @haighd |
| No double-labeling | Label only from auto-approve workflow |

---

## Phase 3: Smart Triage (P1)

**Goal:** Reduce manual thread resolution burden through intelligent automation

### Task 3.1: Implement Severity Detection

**Description:** Parse reviewer comments to extract severity levels

**File:** `scripts/categorize-findings.py` (new file)

```python
#!/usr/bin/env python3
"""Categorize review findings by severity based on priority badges."""

import re
import json
import subprocess
import sys

SEVERITY_PATTERNS = {
    'critical': [r'!\[critical\]', r'\*\*critical\*\*', r'🔴'],
    'high': [r'!\[high\]', r'\*\*high\*\*', r'🟠'],
    'medium': [r'!\[medium\]', r'\*\*medium\*\*', r'🟡'],
    'low': [r'!\[low\]', r'\*\*low\*\*', r'🟢', r'nit:', r'nitpick:'],
}

def get_pr_comments(pr_number: int) -> list:
    """Fetch all review comments for a PR."""
    cmd = f'gh api repos/:owner/:repo/pulls/{pr_number}/comments --paginate'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return json.loads(result.stdout) if result.returncode == 0 else []

def categorize_comment(body: str) -> str:
    """Determine severity of a comment based on content."""
    body_lower = body.lower()
    for severity, patterns in SEVERITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, body_lower):
                return severity
    return 'medium'  # Default to medium if no pattern matched

def main(pr_number: int):
    comments = get_pr_comments(pr_number)

    categorized = {'critical': [], 'high': [], 'medium': [], 'low': []}

    for comment in comments:
        severity = categorize_comment(comment.get('body', ''))
        categorized[severity].append({
            'id': comment['id'],
            'path': comment.get('path', 'N/A'),
            'body': comment.get('body', '')[:100],
            'user': comment.get('user', {}).get('login', 'unknown')
        })

    print(json.dumps({
        'summary': {s: len(v) for s, v in categorized.items()},
        'requires_attention': len(categorized['critical']) + len(categorized['high']),
        'can_batch_resolve': len(categorized['medium']) + len(categorized['low']),
        'details': categorized
    }, indent=2))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: categorize-findings.py <pr_number>")
        sys.exit(1)
    main(int(sys.argv[1]))
```

**Success criteria:**
- [ ] Script correctly identifies severity badges
- [ ] Output shows breakdown by severity level
- [ ] Default to medium for unclassified comments

---

### Task 3.2: Auto-Resolve Outdated Threads

**Description:** Workflow to automatically resolve threads marked as outdated by GitHub

**File:** `.github/workflows/auto-resolve-outdated.yml` (new file)

```yaml
name: Auto-Resolve Outdated Threads

on:
  pull_request:
    types: [synchronize]  # Triggers on new commits

jobs:
  resolve-outdated:
    runs-on: ubuntu-latest
    steps:
      - name: Resolve outdated review threads
        uses: actions/github-script@v7
        with:
          script: |
            const prNumber = context.payload.pull_request.number;

            // Get all review threads
            const query = `
              query($owner: String!, $repo: String!, $pr: Int!) {
                repository(owner: $owner, name: $repo) {
                  pullRequest(number: $pr) {
                    reviewThreads(first: 100) {
                      nodes {
                        id
                        isResolved
                        isOutdated
                        comments(first: 1) {
                          nodes {
                            body
                            author { login }
                          }
                        }
                      }
                    }
                  }
                }
              }
            `;

            const result = await github.graphql(query, {
              owner: context.repo.owner,
              repo: context.repo.repo,
              pr: prNumber
            });

            const threads = result.repository.pullRequest.reviewThreads.nodes;
            const outdatedUnresolved = threads.filter(t => t.isOutdated && !t.isResolved);

            console.log(`Found ${outdatedUnresolved.length} outdated unresolved threads`);

            for (const thread of outdatedUnresolved) {
              // Add acknowledgment comment
              await github.graphql(`
                mutation($threadId: ID!, $body: String!) {
                  addPullRequestReviewThreadReply(input: {
                    pullRequestReviewThreadId: $threadId,
                    body: $body
                  }) {
                    comment { id }
                  }
                }
              `, {
                threadId: thread.id,
                body: "Auto-acknowledged: This thread is outdated (code has changed). Resolving automatically."
              });

              // Resolve the thread
              await github.graphql(`
                mutation($threadId: ID!) {
                  resolveReviewThread(input: {threadId: $threadId}) {
                    thread { isResolved }
                  }
                }
              `, { threadId: thread.id });

              console.log(`Resolved outdated thread: ${thread.id}`);
            }

            if (outdatedUnresolved.length > 0) {
              await github.rest.issues.createComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: prNumber,
                body: `🔄 Auto-resolved ${outdatedUnresolved.length} outdated review thread(s).\n\nThese threads were on code that has since been modified.`
              });
            }
```

**Success criteria:**
- [ ] Outdated threads auto-resolved on new commits
- [ ] Acknowledgment comment added before resolution
- [ ] Summary comment posted to PR

---

### Task 3.3: Update Thread Check for Severity Awareness

**Description:** Modify CI gate to only block on critical/high findings

**File:** `.github/workflows/run-ci.yml` (update check-threads job)

**Changes:**

```yaml
- name: Check for blocking threads
  id: check
  run: |
    PR_NUMBER=${{ needs.check-trigger.outputs.pr_number }}

    # Get severity breakdown
    FINDINGS=$(python3 scripts/categorize-findings.py $PR_NUMBER)
    CRITICAL=$(echo $FINDINGS | jq '.summary.critical')
    HIGH=$(echo $FINDINGS | jq '.summary.high')
    BLOCKING=$((CRITICAL + HIGH))

    if [ "$BLOCKING" -gt 0 ]; then
      echo "resolved=false" >> $GITHUB_OUTPUT
      echo "::error::$BLOCKING critical/high findings require attention"
    else
      echo "resolved=true" >> $GITHUB_OUTPUT
    fi
```

**Success criteria:**
- [ ] Critical/high findings block CI
- [ ] Medium/low findings do not block CI
- [ ] Clear message about what requires attention

---

### Task 3.4: Update CONTRIBUTING.md

**Description:** Document the new automated workflow for contributors

**File:** `CONTRIBUTING.md`

**Add section:**

```markdown
## PR Review Workflow

This repository uses an automated CI/CD pipeline with dual AI reviewers.

### What Happens Automatically

1. **AI Reviews**: Both Gemini Code Assist and GitHub Copilot automatically review your PR
2. **Outdated Threads**: Threads on modified code are auto-resolved with acknowledgment
3. **CI Gating**: CI only runs after critical/high findings are addressed
4. **Auto-Approval**: Bot approves when all conditions are met
5. **Ready Label**: `ready-to-merge` label added when ready for final merge

### What You Need to Do

1. **Push your changes** - Reviews trigger automatically
2. **Address critical/high findings** - These block CI
3. **Medium/low are optional** - Can be batch-resolved if appropriate
4. **Wait for approval** - Bot approves when conditions met
5. **CEO merges** - Final merge requires human approval

### Severity Levels

| Level | Action Required |
|-------|-----------------|
| Critical | Must fix before CI |
| High | Must fix before CI |
| Medium | Recommended but optional |
| Low/Nit | Optional improvement |
```

**Success criteria:**
- [ ] CONTRIBUTING.md updated with workflow documentation
- [ ] Severity levels clearly explained
- [ ] Agent responsibilities documented

---

### Phase 3 Exit Criteria

| Criterion | Verification |
|-----------|--------------|
| Severity detection works | `python3 scripts/categorize-findings.py <PR>` returns breakdown |
| Outdated auto-resolved | Push to PR with outdated threads → threads resolved |
| CI gates correctly | Critical/high block; medium/low pass |
| Documentation updated | CONTRIBUTING.md has new workflow section |

---

## Phase 4: Quality & Polish (P2)

**Goal:** Add quality tracking, external notifications, and configuration optimization

### Task 4.1: TP/FP Tracking System

**Description:** Track whether reviewer comments led to fixes or were dismissed

**Implementation approach:**
1. Create `scripts/track-finding-outcomes.py` to analyze PR history
2. Store outcomes in `data/reviewer-metrics.json`
3. Calculate TP rate per reviewer

**Data structure:**
```json
{
  "gemini": {
    "total_comments": 135,
    "led_to_fix": 89,
    "dismissed": 46,
    "tp_rate": 0.66
  },
  "copilot": {
    "total_comments": 63,
    "led_to_fix": 51,
    "dismissed": 12,
    "tp_rate": 0.81
  }
}
```

**Success criteria:**
- [ ] Script analyzes comment → resolution → subsequent commit pattern
- [ ] TP rates calculated and stored
- [ ] Can query historical data

---

### Task 4.2: Slack Notifications

**Description:** Webhook integration for PR status changes

**File:** `.github/workflows/notify-slack.yml` (new file)

**Events to notify:**
- PR ready-to-merge (consolidated, not per-step)
- CI failure requiring attention
- Critical findings detected

**Success criteria:**
- [ ] Slack webhook configured as repository secret
- [ ] Notifications post to configured channel
- [ ] No notification spam (consolidated messages)

---

### Task 4.3: Dashboard Integration

**Description:** Add PR pipeline status to CLC dashboard

**Implementation:**
- Add `/api/pr-status` endpoint
- Query GitHub API for open PRs
- Display current phase for each PR

**Success criteria:**
- [ ] Dashboard shows all open PRs
- [ ] Each PR shows current pipeline phase
- [ ] Status updates on refresh

---

### Task 4.4: Gemini Configuration Optimization

**Description:** Create `.gemini/` config to reduce noise and focus on high-value feedback

**File:** `.gemini/config.yaml` (new file)

```yaml
# Gemini Code Assist configuration
review:
  focus_areas:
    - security
    - performance
    - correctness

  reduce_emphasis:
    - style  # We have prettier/eslint
    - documentation  # Separate concern

  severity_threshold: medium  # Don't comment on low-priority items

  custom_instructions: |
    Focus on:
    - Actual bugs and logic errors
    - Security vulnerabilities
    - Race conditions and async issues
    - Performance bottlenecks

    Skip:
    - Formatting (handled by automated tools)
    - Minor style preferences
    - Documentation suggestions
```

**Success criteria:**
- [ ] Gemini config reduces comment volume by ~30%
- [ ] Higher signal-to-noise ratio in reviews
- [ ] Critical issues still caught

---

### Phase 4 Exit Criteria

| Criterion | Verification |
|-----------|--------------|
| TP tracking works | `python3 scripts/track-finding-outcomes.py` outputs rates |
| Slack notifications | Ready-to-merge posts to Slack |
| Dashboard shows PRs | Dashboard displays open PR status |
| Gemini optimized | Fewer low-priority comments |

---

## Success Criteria Summary

### Automated Verification

```bash
# Phase 1
ls scripts/check-unresolved-threads.sh  # File exists
grep "free-disk-space" .github/workflows/run-ci.yml  # Disk cleanup present

# Phase 2
gh api repos/:owner/:repo/collaborators --jq '.[].login' | grep haighd-bot  # Bot exists

# Phase 3
python3 scripts/categorize-findings.py 50  # Returns valid JSON

# Phase 4
ls .gemini/config.yaml  # Gemini config exists
```

### Manual Verification

1. Create test PR → Both reviewers comment within 5 min
2. Leave thread unresolved → `/run-ci` fails with clear message
3. Resolve all threads → CI proceeds
4. CI passes → Bot approves, label added
5. Check Slack → Notification received
6. CEO merges → Process complete

---

## Rollback Plan

| Phase | Rollback Action |
|-------|-----------------|
| Phase 1 | Remove disk cleanup step; revert thread gating |
| Phase 2 | Delete auto-approve.yml; remove bot from collaborators |
| Phase 3 | Revert to blocking on all threads; remove categorization |
| Phase 4 | Delete .gemini config; disable Slack webhook |

All changes are additive and can be reverted by removing the added files/steps.

---

## Timeline Dependencies

```
Phase 1 ──────────────────────────────────────────────────────►
  │
  ├── Task 1.1 (PR #50 merge) ─┐
  │                             ├── Must complete before 1.5
  └── Task 1.2-1.4 (parallel) ─┘

Phase 2 ──────────────────────────────────────────────────────►
  │
  └── Task 2.1 (bot account) ─── Must complete before 2.2

Phase 3 ──────────────────────────────────────────────────────►
  │
  └── Depends on Phase 1 completion

Phase 4 ──────────────────────────────────────────────────────►
  │
  └── Independent; can start after Phase 2
```

---

## Phase 5: Workflow Portability

**Goal:** Enable easy adoption of this CI/CD workflow in other repositories (existing or new, private or public, personal or enterprise)

### Task 5.1: Create Workflow Template Repository

**Description:** Package the workflow files as a reusable template

**Deliverables:**
- Create `.github/workflow-templates/` directory with:
  - `run-ci.yml` - CI pipeline with disk cleanup and thread gating
  - `auto-approve.yml` - Bot approval workflow
  - `gemini-review-check.yml` - Dual AI reviewer trigger
- Create `workflow-templates/README.md` with setup instructions
- Create `workflow-templates/setup.sh` script for automated installation

**Setup script features:**
```bash
#!/bin/bash
# setup-cicd-workflow.sh
# Installs the unified CI/CD workflow to a target repository

TARGET_REPO="${1:?Usage: setup-cicd-workflow.sh <owner/repo>}"

# 1. Copy workflow files
# 2. Create required labels (ready-to-merge, do-not-merge, etc.)
# 3. Prompt for BOT_PAT secret configuration
# 4. Configure branch protection rules
# 5. Enable Copilot ruleset (instructions only - requires manual step)
```

**Success criteria:**
- [ ] Template files are complete and documented
- [ ] Setup script handles common scenarios
- [ ] Instructions cover both personal and enterprise GitHub

---

### Task 5.2: Document Manual Setup Process

**Description:** Comprehensive documentation for manual workflow adoption

**File:** `docs/guides/cicd-workflow-setup.md`

**Contents:**
1. **Prerequisites**
   - GitHub account with repo access
   - `gh` CLI installed and authenticated
   - Bot account created (or instructions to create)

2. **Quick Start (5 minutes)**
   - Copy workflow files
   - Add BOT_PAT secret
   - Enable Copilot ruleset

3. **Full Setup Guide**
   - Step-by-step with screenshots
   - Branch protection configuration
   - Troubleshooting common issues

4. **Customization Options**
   - Adjusting disk cleanup settings
   - Modifying approval conditions
   - Adding custom CI steps

5. **Enterprise Considerations**
   - SAML/SSO for bot account
   - Audit logging requirements
   - Compliance with org policies

**Success criteria:**
- [ ] Documentation covers all setup scenarios
- [ ] Includes troubleshooting section
- [ ] Tested on fresh repository

---

### Task 5.3: Create GitHub Actions Composite Action (Optional)

**Description:** Package core functionality as reusable composite actions

**Benefits:**
- Single source of truth for workflow logic
- Easier updates across multiple repos
- Version pinning for stability

**Actions to create:**
- `haighd/cicd-actions/check-threads@v1` - Thread status check
- `haighd/cicd-actions/auto-approve@v1` - Approval with conditions
- `haighd/cicd-actions/ai-review-status@v1` - Dual reviewer check

**Success criteria:**
- [ ] Actions published to separate repo or GitHub Marketplace
- [ ] Versioned releases (v1, v1.0.0)
- [ ] Usage examples in README

---

### Phase 5 Exit Criteria

| Criterion | Verification |
|-----------|--------------|
| Template files exist | `ls workflow-templates/*.yml` |
| Setup script works | Run on test repo successfully |
| Documentation complete | All sections written and reviewed |
| Tested on new repo | Fresh repo setup in <10 minutes |

---

## Notes

- **Architectural decision**: Using `hmarr/auto-approve-action` instead of custom GraphQL for simplicity and maintainability
- **Security consideration**: Bot PAT should be rotated quarterly; add calendar reminder
- **Future enhancement**: Consider GitHub App instead of PAT for better security model
- **Portability**: Phase 5 enables this workflow to scale to multiple repositories
