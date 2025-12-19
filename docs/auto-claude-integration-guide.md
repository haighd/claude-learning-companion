# Auto-Claude Integration Guide

**Purpose**: How to run Auto-Claude alongside CLC without conflicts
**Related**: [Technical Spec](implementation-plans/auto-claude-integration-spec.md) | [Issue #14](https://github.com/haighd/claude-learning-companion/issues/14)

---

## Quick Summary

| Question | Answer |
|----------|--------|
| Can I run both? | Yes, no technical conflicts |
| Do they share data? | No, completely separate storage |
| Will they interfere? | Only if CLAUDE.md instructions conflict |
| Recommended setup? | Subdirectory installation |

---

## What Each System Does

| Aspect | CLC | Auto-Claude |
|--------|-----|-------------|
| **Purpose** | Persistent knowledge accumulation | Autonomous code execution |
| **Agents** | Advisory (provide perspectives) | Executive (do the work) |
| **Memory** | Global (`~/.claude/clc/`) | Per-project (`./specs/`) |
| **Human role** | Decision-maker | Reviewer/approver |

**Key insight**: They're complementary. CLC remembers; Auto-Claude executes.

---

## Compatibility Analysis

### No Conflicts

```
CLC uses:                          Auto-Claude uses:
~/.claude/CLAUDE.md (global)       ./CLAUDE.md (project-local)
~/.claude/settings.json            ./.env
~/.claude/clc/memory/              ./specs/, ./.worktrees/
Global hooks                       Python orchestration (no hooks)
```

These are entirely separate file paths.

### Potential Issues

#### 1. CLAUDE.md Override

**Problem**: Claude Code loads global first, then local overrides. Auto-Claude's local `./CLAUDE.md` may suppress CLC's global instructions.

**Solution**: Add CLC integration to Auto-Claude's CLAUDE.md:

```markdown
# In your project's CLAUDE.md (where Auto-Claude is installed)

## CLC Integration
Before any task, query accumulated knowledge:
```bash
python ~/.claude/clc/query/query.py --context
```
This returns: golden rules, domain-specific heuristics, recent failures to avoid,
and success patterns to replicate. Apply these insights to your task approach.
```

#### 2. Learning Hook Noise

**Problem**: CLC hooks capture ALL tool usage. Auto-Claude's autonomous builds generate hundreds of calls, flooding your learning database with noise.

**Solution**: Add exclusion pattern to CLC hooks:

```python
# Edit: ~/.claude/clc/hooks/learning-loop/pre_tool_learning.py
# Add near the top:

import os
import sys
from pathlib import Path

cwd = Path(os.getcwd())

# Check for Auto-Claude marker files/directories (more robust than substring matching)
auto_claude_markers = [
    cwd / ".auto-claude",           # Subdirectory installation
    cwd / "auto-claude-framework",  # Root installation
]

# Check if we're inside a git worktree (used by Auto-Claude for isolated builds)
in_worktree = (cwd / ".git").is_file()  # Worktrees have .git as file, not directory

if any(marker.exists() for marker in auto_claude_markers) or in_worktree:
    sys.exit(0)  # Skip Auto-Claude operations
```

#### 3. Knowledge Not Shared

**Problem**: Auto-Claude agents don't query CLC. Your accumulated wisdom doesn't help autonomous builds.

**Solution**: Manual injection into specs:

```bash
# Before creating an Auto-Claude spec
python ~/.claude/clc/query/query.py --domain "react" > clc-context.txt

# Review clc-context.txt and include relevant learnings
# in your spec's requirements or constraints
```

---

## Installation Options

### Option A: Subdirectory (Recommended)

Best for: Testing Auto-Claude without disrupting existing workflow.

```bash
cd ~/Projects/my-project

# Install Auto-Claude in hidden subdirectory
git clone https://github.com/AndyMik90/Auto-Claude.git .auto-claude
cd .auto-claude
uv venv && uv pip install -r requirements.txt
cp .env.example .env
claude setup-token

# Update project .gitignore (idempotent - only add if not present)
cd ..
for item in .auto-claude/ .worktrees/ specs/; do
    grep -qxF "$item" .gitignore 2>/dev/null || echo "$item" >> .gitignore
done
```

**Directory structure after**:
```
my-project/
├── .claude/           # Existing CLC project config
├── .auto-claude/      # Auto-Claude (isolated)
│   ├── CLAUDE.md      # Doesn't affect parent
│   ├── .env
│   └── ...
├── .gitignore         # Updated
└── [your code]
```

**Usage**:
```bash
# Normal CLC workflow
cd ~/Projects/my-project
claude  # Uses .claude/ config

# Auto-Claude workflow
cd ~/Projects/my-project/.auto-claude
source .venv/bin/activate
python -m auto_claude spec create --task "Add feature X"
```

### Option B: Root Installation (Advanced)

Best for: Deep integration after you've tested Option A.

```bash
cd ~/Projects/my-project

# Clone Auto-Claude framework
git clone https://github.com/AndyMik90/Auto-Claude.git auto-claude-framework
cd auto-claude-framework && uv venv && uv pip install -r requirements.txt

# Create merged CLAUDE.md at project root (idempotent - skips if already integrated)
cd ..
if grep -qF "## CLC Integration (Always)" CLAUDE.md 2>/dev/null; then
    echo "CLC integration already present in CLAUDE.md - skipping"
else
    if [ -f CLAUDE.md ]; then
        BACKUP_NAME="CLAUDE.md.bak.$(date +%Y%m%d_%H%M%S)_${BASHPID:-$$}"
        mv CLAUDE.md "$BACKUP_NAME" || { echo 'Failed to back up CLAUDE.md. Aborting.' >&2; exit 1; }
        echo "Backed up existing CLAUDE.md to $BACKUP_NAME"
    fi
    { cat << 'EOF'
# Project Instructions

## CLC Integration (Always)
Before any task:
```bash
python ~/.claude/clc/query/query.py --context
```
Apply golden rules. Record learnings when done.

## Auto-Claude (For Autonomous Builds)
For complex features, use Auto-Claude:
- Framework: `./auto-claude-framework/`
- Specs: `./specs/`
- Builds: `./.worktrees/`

## Project-Specific Rules
EOF
    # Append existing project config if present
    # First, check for backed-up root CLAUDE.md (from our backup above)
    if [ -n "$BACKUP_NAME" ] && [ -f "$BACKUP_NAME" ]; then
      echo ""
      echo "# --- Appended from existing CLAUDE.md ---"
      cat "$BACKUP_NAME"
    # Otherwise, check for project-local .claude/CLAUDE.md
    elif [ -f .claude/CLAUDE.md ]; then
      echo ""
      echo "# --- Appended from .claude/CLAUDE.md ---"
      cat .claude/CLAUDE.md
    fi
    } > CLAUDE.md
fi

# Update .gitignore (idempotent - only add if not present)
for item in auto-claude-framework/ specs/ .worktrees/; do
    grep -qxF "$item" .gitignore 2>/dev/null || echo "$item" >> .gitignore
done
```

---

## Hybrid Workflow

The recommended way to use both systems together:

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: PLANNING (CLC)                                        │
│                                                                 │
│  $ python ~/.claude/clc/query/query.py --context               │
│                                                                 │
│  Review:                                                        │
│  - Relevant golden rules                                        │
│  - Domain heuristics                                            │
│  - Past failures to avoid                                       │
│  - Past successes to replicate                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: SPEC CREATION (Auto-Claude)                           │
│                                                                 │
│  $ cd .auto-claude                                              │
│  $ python -m auto_claude spec create \                          │
│      --task "Add dark mode" \                                   │
│      --complexity standard                                      │
│                                                                 │
│  Inject CLC learnings into spec requirements!                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: AUTONOMOUS BUILD (Auto-Claude)                        │
│                                                                 │
│  $ python -m auto_claude build start --spec 001-dark-mode       │
│                                                                 │
│  Agents work in isolated .worktrees/ directory                  │
│  - Planner creates subtasks                                     │
│  - Coder implements                                             │
│  - QA validates                                                 │
│  - Fixer resolves issues (up to 50 iterations)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: REVIEW & MERGE (Your Existing PR Workflow)            │
│                                                                 │
│  $ python -m auto_claude build merge --spec 001-dark-mode       │
│  $ git checkout -b feature/dark-mode                            │
│  $ gh pr create --title "Add dark mode"                         │
│                                                                 │
│  Then use your normal workflow:                                 │
│  - /gemini review                                               │
│  - Address feedback                                             │
│  - /run-ci                                                      │
│  - Wait for CEO to merge                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5: LEARNING CAPTURE (CLC)                                │
│                                                                 │
│  Record what worked:                                            │
│  $ bash ~/.claude/clc/scripts/record-success.sh                 │
│                                                                 │
│  Record what failed:                                            │
│  $ bash ~/.claude/clc/scripts/record-failure.sh                 │
│                                                                 │
│  Extract heuristics:                                            │
│  $ bash ~/.claude/clc/scripts/record-heuristic.sh               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Task Routing Decision Tree

```
New task arrives
      │
      ▼
Is it a quick fix (< 30 min)?
      │
      ├─ YES → Use CLC + manual coding
      │        (Query CLC, fix, record learning)
      │
      └─ NO → Is it well-defined with clear acceptance criteria?
              │
              ├─ YES → Use Auto-Claude
              │        (Create spec, let agents build)
              │
              └─ NO → Use CLC to clarify first
                      (Research, plan, then decide)
```

---

## Troubleshooting

### "CLC instructions aren't being followed"

**Cause**: Project-local CLAUDE.md overriding global.

**Fix**: Ensure your project's CLAUDE.md includes CLC query instruction:
```markdown
## CLC Integration
Before any task, query accumulated knowledge:
```bash
python ~/.claude/clc/query/query.py --context
```
Apply relevant golden rules and heuristics.
```

### "Learning database is huge after Auto-Claude build"

**Cause**: CLC hooks captured all Auto-Claude tool calls.

**Fix**: Add exclusion to hooks (see Issue 2 above).

### "Auto-Claude keeps making the same mistakes CLC already learned about"

**Cause**: Auto-Claude doesn't query CLC automatically.

**Fix**: Manually inject CLC context into spec creation. Consider implementing the Knowledge Injection feature from [Issue #14](https://github.com/haighd/claude-learning-companion/issues/14).

---

## Future Integration Ideas

These are tracked in [GitHub Issue #14](https://github.com/haighd/claude-learning-companion/issues/14):

1. **Automatic CLC query in Auto-Claude specs** - Inject heuristics automatically
2. **Learning capture from builds** - Auto-record outcomes after merge
3. **Shared memory layer** - Graph database for both systems
4. **Unified dashboard** - See CLC analytics + Auto-Claude progress

---

## References

- [Technical Spec](implementation-plans/auto-claude-integration-spec.md)
- [Auto-Claude Repository](https://github.com/AndyMik90/Auto-Claude)
- [Enhancement Tracking Issue](https://github.com/haighd/claude-learning-companion/issues/14)

---

*Last updated: 2025-12-18*
