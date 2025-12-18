# Product/Feature Development Workflow

A comprehensive guide to the full lifecycle of product and feature development using CLC slash commands and agents.

---

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PRODUCT/FEATURE LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. CONCEPTION        2. DEFINITION       3. PLANNING       4. EXECUTION   │
│  ───────────────      ─────────────       ───────────       ────────────   │
│  • Research           • PRD               • Tech Plan       • Development  │
│  • Discovery          • Requirements      • Architecture    • Testing      │
│  • Validation         • Scope             • Tasks           • Review       │
│                                                                             │
│        ↓                    ↓                   ↓                 ↓         │
│  /vendor-research     /create-prd         /create-plan      /start-from-   │
│  /research-codebase                       /init-project         issue      │
│  WebSearch/Fetch                                            /debug         │
│                                                             /commit        │
│                                                                             │
│  5. DELIVERY          6. ITERATION                                          │
│  ─────────────        ────────────                                          │
│  • PR Creation        • Feedback                                            │
│  • CI/CD              • Refinement                                          │
│  • Merge              • Learning                                            │
│                                                                             │
│        ↓                    ↓                                               │
│  /describe-pr         /review-learnings                                     │
│  /commit              /capture-learnings                                    │
│                       /clc:query                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Conception (Research & Discovery)

**Goal:** Understand the problem space, validate the opportunity, gather evidence.

### When to Use Each Tool

| Scenario | Command/Tool | Output |
|----------|--------------|--------|
| External vendor selection | `/vendor-research` | Research document in `docs/research/` |
| Market/competitive analysis | `WebSearch` + `WebFetch` | Ad-hoc or research doc |
| Understanding existing codebase | `/research-codebase` | Codebase analysis |
| Technical feasibility | `Task` with `Explore` agent | Exploration findings |
| User research synthesis | Product Manager agent | Insights summary |

### Example: Starting a New Feature

```bash
# Option 1: You need external vendor research
/vendor-research
> "print-on-demand services for professional photography"

# Option 2: You need to understand existing code
/research-codebase
> "How does the current payment system work?"

# Option 3: General market/competitive research
# Use WebSearch directly with clear research questions
```

### Deliverables from Phase 1
- Research document(s) in `docs/research/`
- Understanding of problem space
- Evidence for decision-making
- Competitive landscape awareness

---

## Phase 2: Definition (PRD)

**Goal:** Define WHAT we're building, for WHOM, and HOW we'll measure success.

### Command

```bash
/create-prd
```

### Inputs
- Problem statement
- Target users
- Research documents (from Phase 1)
- Related GitHub issues

### Flags
- `--research docs/research/xyz.md` - Link to existing research
- `--issue 42` - Link to GitHub issue

### Interactive Process
1. Problem discovery - clarify the pain point
2. User analysis - define personas and journeys
3. Requirements gathering - functional and non-functional
4. Success metrics - how we measure impact
5. Scope definition - what's in, what's out

### Output
- PRD document in `docs/prd/YYYY-MM-DD-feature-name.md`
- Clear requirements with acceptance criteria
- Success metrics with targets
- Scope boundaries

### Example

```bash
# With research context
/create-prd --research docs/research/2025-01-10-pod-vendor-selection.md

# From a GitHub issue
/create-prd --issue 42

# Starting fresh
/create-prd "Add subscription billing to the platform"
```

---

## Phase 3: Planning (Technical Design)

**Goal:** Define HOW we'll build it technically.

### Command

```bash
/create-plan
```

### Inputs
- Approved PRD (from Phase 2)
- Technical constraints
- Existing codebase patterns

### Flags
- `--prd docs/prd/xyz.md` - Link to PRD (NEW - add this connection)
- `--issue 42` - Link to GitHub issue
- `--with-templates` - Create context and task tracking files

### Interactive Process
1. Read PRD and codebase
2. Research existing patterns
3. Design technical approach
4. Define implementation phases
5. Set success criteria (automated + manual)

### Output
- Implementation plan in `docs/implementation-plans/`
- Phase breakdown with dependencies
- File-level change specifications
- Test strategy

### Example

```bash
# From PRD
/create-plan --prd docs/prd/2025-01-15-subscription-billing.md

# With task templates
/create-plan --with-templates --issue 42
```

---

## Phase 4: Execution (Development)

**Goal:** Build the thing.

### Starting Work

```bash
# Start from a GitHub issue (recommended)
/start-from-issue 42

# Or use the intelligent router
/start
```

### During Development

| Situation | Command/Tool |
|-----------|--------------|
| Writing code | Direct coding with Claude |
| Debugging issues | `/debug` |
| Running tests | `npm run test` / `bun test` |
| Creating commits | `/commit` |
| Stuck on a problem | `Task` with specialist agent |

### Specialist Agents for Development

Use `Task` tool with appropriate `subagent_type`:

| Agent | Use Case |
|-------|----------|
| `frontend-developer` | React, UI components |
| `backend-developer` | APIs, server logic |
| `fullstack-developer` | End-to-end features |
| `test-automator` | Writing test suites |
| `code-reviewer` | Pre-commit review |
| `debugger` | Complex issue diagnosis |
| `performance-engineer` | Optimization |

### Example Development Flow

```bash
# 1. Start from issue
/start-from-issue 42

# 2. Work iteratively (Claude writes code)
# ... coding happens ...

# 3. Debug if needed
/debug
> "The subscription isn't persisting after refresh"

# 4. Commit changes
/commit
```

---

## Phase 5: Delivery (PR & Merge)

**Goal:** Get code reviewed, tested, and merged.

### Creating PRs

```bash
# Generate PR description
/describe-pr

# Or create PR directly with gh
gh pr create --title "feat: add subscription billing" --body "..."
```

### PR Workflow (from CLAUDE.md)

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: REVIEW                                                │
├─────────────────────────────────────────────────────────────────┤
│  Push → /gemini review → Address comments → Repeat              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                        /run-ci
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: CI TESTING                                            │
├─────────────────────────────────────────────────────────────────┤
│  Lint → Build → Unit Tests → E2E Tests                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                        Ready to Merge
```

### Commands in PR Phase

| Action | Command |
|--------|---------|
| Push changes | `git push origin feature-branch` |
| Request review | `gh pr comment <PR> --body "/gemini review"` |
| Trigger CI | `gh pr comment <PR> --body "/run-ci"` |
| Check status | `gh pr checks <PR>` |

---

## Phase 6: Iteration (Learning & Improvement)

**Goal:** Learn from the work, improve for next time.

### Capturing Learnings

```bash
# Review what CLC learned during the session
/review-learnings

# Manually capture a specific learning
/capture-learnings

# Query CLC for context on future work
/clc:query
```

### What Gets Captured Automatically
- Workflow successes and failures
- Heuristics from problem-solving
- Patterns that worked

### What to Capture Manually
- Significant architectural decisions
- Hard-won debugging insights
- Process improvements
- Reusable patterns

---

## Quick Reference: Full Workflow

```bash
# ═══════════════════════════════════════════════════════════════
# PHASE 1: CONCEPTION
# ═══════════════════════════════════════════════════════════════

# Research (choose based on need)
/vendor-research           # External vendor selection
/research-codebase         # Understand existing code
# WebSearch/WebFetch       # Market research

# ═══════════════════════════════════════════════════════════════
# PHASE 2: DEFINITION
# ═══════════════════════════════════════════════════════════════

/create-prd --research docs/research/[research-doc].md
# Interactive PRD creation → outputs to docs/prd/

# ═══════════════════════════════════════════════════════════════
# PHASE 3: PLANNING
# ═══════════════════════════════════════════════════════════════

/create-plan --prd docs/prd/[prd-doc].md --with-templates
# Technical planning → outputs to docs/implementation-plans/

# ═══════════════════════════════════════════════════════════════
# PHASE 4: EXECUTION
# ═══════════════════════════════════════════════════════════════

/start-from-issue [issue-number]
# or
/implement-plan docs/implementation-plans/[plan-doc].md

# During development:
/debug                     # When stuck
/commit                    # Save progress

# ═══════════════════════════════════════════════════════════════
# PHASE 5: DELIVERY
# ═══════════════════════════════════════════════════════════════

/describe-pr               # Generate PR description
gh pr create ...           # Create the PR
gh pr comment X --body "/gemini review"   # Request review
# Address feedback
gh pr comment X --body "/run-ci"          # Trigger CI
# Wait for merge

# ═══════════════════════════════════════════════════════════════
# PHASE 6: ITERATION
# ═══════════════════════════════════════════════════════════════

/review-learnings          # See what was learned
/capture-learnings         # Add manual learnings
/clc:query                 # Query for future work
```

---

## Command Reference

| Command | Phase | Purpose |
|---------|-------|---------|
| `/vendor-research` | 1 | External vendor analysis |
| `/research-codebase` | 1 | Codebase exploration |
| `/create-prd` | 2 | Product requirements |
| `/create-plan` | 3 | Technical planning |
| `/init-project` | 3 | New project setup |
| `/start-from-issue` | 4 | Begin work from issue |
| `/start` | 4 | Intelligent work router |
| `/implement-plan` | 4 | Execute a plan |
| `/debug` | 4 | Troubleshooting |
| `/commit` | 4-5 | Git commits |
| `/describe-pr` | 5 | PR descriptions |
| `/review-learnings` | 6 | Review session learnings |
| `/capture-learnings` | 6 | Manual learning capture |
| `/clc:query` | Any | Query CLC context |
| `/clc:health` | Any | Check CLC status |

---

## Tips

1. **Don't skip phases** - Research informs PRD, PRD informs planning, planning enables clean execution.

2. **Link artifacts** - Use `--research`, `--prd`, `--issue` flags to maintain traceability.

3. **Query CLC first** - Always `python ~/.claude/clc/query/query.py --context` before starting work.

4. **Capture learnings** - The system only improves if you feed it. Don't forget Phase 6.

5. **Use specialist agents** - For complex work, spawn the right specialist via `Task` tool.

6. **Iterate, don't waterfall** - Each phase is interactive. Get feedback early and often.
