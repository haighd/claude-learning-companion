---
title: "Unified CI/CD Workflow with Dual AI Reviewers"
status: draft
author: "Dan Haight"
created: 2025-12-22
last_updated: 2025-12-22
version: "1.0"
related_issue: 49
related_research: "docs/research/2025-12-22-cicd-workflow-comprehensive-analysis.md"
---

# PRD: Unified CI/CD Workflow with Dual AI Reviewers

## Overview

### Problem Statement

The current PR workflow requires 6+ manual steps, wastes CI resources by running before reviews are complete, relies on a single AI reviewer (missing complementary coverage), and creates a bottleneck where the CEO must manually approve every PR. This slows development velocity, increases cognitive load on all participants, and results in inefficient use of GitHub Actions minutes.

### Opportunity

By implementing a unified, automated CI/CD pipeline that leverages both AI reviewers (Gemini for best practices, Copilot for bug detection), gates CI on review completion, and enables bot-based auto-approval, we can:
- Reduce manual steps from 6+ to 2
- Cut CI runs per PR from ~5 to ~2
- Improve code quality through dual-reviewer coverage
- Free CEO time for high-value decisions only

### Proposed Solution

A 6-phase automated pipeline that:
1. Auto-triggers both AI reviewers on PR creation
2. Triages findings by severity
3. Requires human attention only for critical/high issues
4. Gates CI on thread resolution
5. Auto-approves via dedicated bot account when conditions met
6. Signals readiness for CEO's final merge decision

---

## Users & Stakeholders

### Target Users

#### Claude Agents (Primary)
- **Who**: AI agents implementing features, fixes, and improvements
- **Needs**: Clear workflow with minimal manual steps, fast feedback loops, predictable process
- **Pain Points**:
  - Must manually trigger `/gemini review`
  - Must individually resolve 10+ threads per PR
  - Must manually trigger `/run-ci`
  - Unclear when PR is actually ready

#### CEO - Dan (Primary)
- **Who**: Final authority on all code merges
- **Needs**: Quick visibility into PR readiness, confidence that quality gates passed, minimal review burden for routine PRs
- **Pain Points**:
  - Must manually approve every PR
  - Must review all thread resolutions
  - Email/GH notification overload
  - Bottleneck for entire development process

### Secondary Users

#### Future Contributors
- **Who**: Potential external contributors to the project
- **Needs**: Clear documentation, predictable process, reasonable review expectations

#### AI Reviewers (Gemini & Copilot)
- **Who**: Automated code review tools
- **Needs**: Proper triggering, feedback acknowledged and acted upon

### Stakeholders

| Role | Interest/Concern |
|------|------------------|
| Development velocity | Faster PR throughput |
| Code quality | Maintain/improve quality standards |
| Cost efficiency | Reduce GitHub Actions spend |
| Security | Bot account PAT management |

---

## User Journey

### Current State

```
Agent pushes code
    ↓
Agent creates PR
    ↓
Agent manually comments "/gemini review"  ← MANUAL STEP
    ↓
Wait for Gemini to review (variable time)
    ↓
Gemini creates 10-15 threads (avg)
    ↓
Agent addresses each thread  ← MANUAL STEP (repeated)
    ↓
Agent resolves each thread  ← MANUAL STEP (repeated)
    ↓
Agent manually comments "/run-ci"  ← MANUAL STEP
    ↓
CI runs (may fail, restart cycle)
    ↓
Agent waits for CI
    ↓
CEO reviews all threads  ← MANUAL STEP
    ↓
CEO manually approves  ← MANUAL STEP
    ↓
CEO merges  ← MANUAL STEP
```

**Pain Points:**
- 6+ manual steps minimum
- Single reviewer (missing Copilot's bug detection)
- CI often runs before reviews addressed (wasted minutes)
- High thread volume creates fatigue
- CEO is bottleneck for every PR
- Notification overload

### Future State

```
Agent pushes code
    ↓
Agent creates PR
    ↓
[AUTOMATED] Both Gemini & Copilot triggered
    ↓
[AUTOMATED] Findings categorized by severity
    ↓
[AUTOMATED] Outdated threads auto-resolved
    ↓
Agent addresses only critical/high findings  ← MANUAL STEP (reduced)
    ↓
[AUTOMATED] CI runs when threads resolved
    ↓
[AUTOMATED] Bot approves when CI passes
    ↓
[AUTOMATED] "ready-to-merge" label added
    ↓
[AUTOMATED] CEO notified (consolidated)
    ↓
CEO scans and merges  ← MANUAL STEP (streamlined)
```

**Benefits:**
- 2 manual steps (address critical findings + CEO merge)
- Dual reviewer coverage
- No wasted CI runs
- Reduced thread fatigue
- CEO sees only ready PRs
- Consolidated notifications

---

## Requirements

### Functional Requirements

#### Must Have (P0)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-001 | Auto-trigger Gemini review on PR creation/update | Gemini review starts within 2 min of PR event without manual trigger |
| FR-002 | Auto-trigger Copilot review on PR creation/update | Copilot review starts within 2 min of PR event without manual trigger |
| FR-003 | Block CI until all review threads are resolved | `/run-ci` fails with clear message if unresolved threads exist |
| FR-004 | Create dedicated bot account (`haighd-bot`) for automated PR approval | Bot account exists with appropriate permissions and PAT |
| FR-005 | Auto-approve when: all threads resolved AND CI passes AND no critical findings | Bot posts approval within 5 min of conditions being met |
| FR-006 | Add `ready-to-merge` label after approval | Label appears automatically after bot approval |
| FR-007 | CEO retains exclusive merge authority | Only CEO can click merge button; no auto-merge |

#### Should Have (P1)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-008 | Auto-resolve outdated threads | Threads marked "outdated" by GitHub are auto-resolved with acknowledgment comment |
| FR-009 | Categorize findings by severity (critical/high/medium/low) | Each finding tagged with severity based on reviewer priority badges |
| FR-010 | Require human attention for critical/high findings only | Critical+High block auto-approval; Medium/Low can be batch-resolved |
| FR-011 | Notification to CEO when PR is ready-to-merge | Single notification per PR when ready-to-merge label added |

#### Nice to Have (P2)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-012 | TP/FP tracking for reviewer comments | System records whether each comment led to fix or was dismissed |
| FR-013 | Reviewer confidence scoring based on TP rates | Dashboard shows TP% per reviewer, updated weekly |
| FR-014 | Custom Gemini configuration to reduce noise | `.gemini/` config reduces style-only comments by 50% |
| FR-015 | Dashboard showing PR pipeline status | CLC dashboard shows all open PRs with current phase |
| FR-016 | Slack notifications for PR status changes | Slack webhook posts key status changes to configured channel |

### Non-Functional Requirements

| Category | Requirement | Target |
|----------|-------------|--------|
| Performance | Review triggers complete within 5 minutes | 95% of triggers start reviews in <5 min |
| Performance | Auto-approval within 5 minutes of conditions met | 95% of approvals in <5 min |
| Security | Bot PAT stored as GitHub secret | No plaintext credentials |
| Security | Bot PAT rotated quarterly | Rotation process documented |
| Reliability | Handle GitHub API rate limits | Exponential backoff retry, max 3 attempts |
| Reliability | Graceful degradation if reviewer unavailable | Skip unavailable reviewer, log warning, continue |
| Auditability | All auto-approvals logged | Log includes: PR#, conditions met, timestamp, bot account |
| Auditability | All auto-resolutions logged | Log includes: thread ID, reason, timestamp |

---

## Scope

### In Scope

- Auto-triggering Gemini and Copilot reviews
- Thread resolution automation (outdated threads)
- CI gating on thread status
- Bot account setup and auto-approval workflow
- Ready-to-merge labeling
- Basic severity categorization
- CONTRIBUTING.md documentation update
- Slack notification integration (P2)

### Out of Scope

| Item | Reason |
|------|--------|
| Auto-merge | CEO retains merge authority per policy decision |
| Custom ML classification | Too complex for v1; use reviewer priority badges |
| Multi-repo support | Focus on CLC repo first; generalize later |
| Email notification customization | Reduce email, use Slack instead |
| Real-time dashboard updates | Polling-based updates sufficient for v1 |

### Dependencies

| Dependency | Description | Status |
|------------|-------------|--------|
| GitHub Bot Account | Create `haighd-bot` user account | Not started |
| Bot PAT | PAT with `repo` scope for `haighd-bot` | Not started |
| PAT Rotation Workflow | GitHub Actions workflow to auto-rotate PAT quarterly | Not started |
| Copilot Ruleset | Configure automatic review via repository ruleset | Not started |
| Gemini access | Already configured via `/gemini review` | Active |
| PR #50 scripts | Thread check/resolve scripts | In PR, ready to merge |

---

## Success Metrics

### Primary Metrics

| Metric | Baseline | Target | Stretch | Measurement |
|--------|----------|--------|---------|-------------|
| Manual steps per PR | 6+ | 2 | 1 | Count manual triggers/actions per PR |
| CI runs per PR | ~5 | ~2 | 1 | GitHub Actions history |
| Time: push to ready-to-merge | Hours | <30 min | <15 min | PR timeline analysis |
| CEO time per PR | 10-15 min | 2-3 min | <1 min | Self-reported estimate |

### Secondary Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Dual reviewer coverage | 100% of PRs | Both reviewers comment on every PR |
| GitHub Actions minutes saved | 40% reduction | Compare monthly usage |
| Auto-approval rate | >80% of PRs | PRs auto-approved / total PRs |
| Critical findings caught | Improve from baseline | Track critical findings per PR |

### Quality Metrics (Long-term)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Gemini TP rate | Track and report | Comments leading to fixes / total comments |
| Copilot TP rate | Track and report | Comments leading to fixes / total comments |
| Post-merge bug rate | Reduce from baseline | Bugs discovered after merge |

### Measurement Plan

- **Weekly**: PR throughput, CI runs, auto-approval rate via GitHub API queries
- **Monthly**: GitHub Actions minutes comparison, reviewer TP rates
- **Quarterly**: Comprehensive quality review, process retrospective

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Bot PAT compromise | Low | High | Store in GitHub Secrets, rotate quarterly, audit logs |
| Reviewer unavailable (outage) | Medium | Medium | Graceful degradation: continue without failed reviewer |
| False auto-resolution | Medium | Medium | Only auto-resolve "outdated" threads; require ack comment |
| Over-automation reduces quality | Low | High | CEO retains merge authority; track post-merge bugs |
| GitHub API rate limits | Medium | Low | Exponential backoff, request batching |
| Copilot duplicate comments | Medium | Low | Dedupe logic before processing |
| Gemini false positives | Medium | Low | TP/FP tracking; confidence scoring over time |

---

## Open Questions

- [x] Auto-merge policy → **Resolved: CEO always merges**
- [x] Primary goal priority → **Resolved: All four goals equally important**
- [x] Notification platform → **Resolved: Slack (P2)**
- [x] Bot account naming convention → **Resolved: `haighd-bot`**
- [x] PAT rotation process owner → **Resolved: Automated via GitHub Actions**
- [x] Severity threshold for blocking → **Resolved: Critical + High require human attention; Medium/Low can be batch-resolved**
- [x] Copilot trigger method → **Resolved: Repository ruleset with automatic review (see below)**

### Copilot Configuration Details

Per [GitHub documentation](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/configure-automatic-review):

**Setup:** Repository Settings → Rules → Rulesets → Add Copilot automatic review rule

**Options to enable:**
- Review on PR creation (required)
- Review new pushes (recommended - re-reviews on each commit)
- Review draft PRs (optional - for early feedback)

**Note:** Uses the [new independent repository rule](https://github.blog/changelog/2025-09-10-copilot-code-review-independent-repository-rule-for-automatic-reviews/) (2025) - not tied to "Require PR before merge" setting.

---

## Implementation Phases

### Phase 1: Foundation (P0 Core)
**Deliverables:**
- Merge PR #50 (thread check/resolve scripts)
- Create bot account and PAT
- Auto-trigger both reviewers on PR events
- CI gating on thread status

**Exit Criteria:**
- Both reviewers auto-triggered on test PR
- CI blocked when threads unresolved
- CI proceeds when threads resolved

### Phase 2: Auto-Approval (P0 Complete)
**Deliverables:**
- Bot auto-approval workflow
- Ready-to-merge labeling
- CEO notification consolidation

**Exit Criteria:**
- Bot approves PR meeting all conditions
- Label appears after approval
- CEO receives single notification per ready PR

### Phase 3: Smart Triage (P1)
**Deliverables:**
- Severity categorization
- Auto-resolve outdated threads
- Reduced human attention for medium/low

**Exit Criteria:**
- Findings tagged by severity
- Outdated threads auto-resolved
- Agent only addresses critical/high

### Phase 4: Quality & Polish (P2)
**Deliverables:**
- TP/FP tracking system
- Slack notifications
- Dashboard integration
- Gemini config optimization

**Exit Criteria:**
- TP rates visible in dashboard
- Slack notifications working
- Gemini comment volume reduced

---

## Appendix

### Related Documents

- [Comprehensive CI/CD Research](docs/research/2025-12-22-cicd-workflow-comprehensive-analysis.md)
- [PR Workflow Efficiency Research](docs/research/2025-12-22-issue-49-pr-workflow-efficiency.md)
- [Issue #49: PR Workflow Improvements](https://github.com/haighd/claude-learning-companion/issues/49)
- [PR #50: Thread Check Scripts](https://github.com/haighd/claude-learning-companion/pull/50)

### Glossary

| Term | Definition |
|------|------------|
| **Thread** | A review comment chain on a PR that must be resolved |
| **Outdated thread** | Thread on code that has since been changed |
| **TP/FP** | True Positive / False Positive - whether reviewer finding was valid |
| **Bot account** | Dedicated GitHub user for automated actions |
| **PAT** | Personal Access Token - authentication for bot |

### Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-22 | Dan Haight | Initial draft |
