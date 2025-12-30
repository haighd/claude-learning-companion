---
description: Resume work from checkpoint (auto-detects project and global sources)
model: sonnet
---

# Resume Work

Resume work after a break, context clear, or session handoff. Automatically discovers checkpoints from both project-local and global sources.

## Step 0: Discover All Checkpoints

Search for checkpoints in priority order:

```bash
CURRENT_PROJECT="$(basename "$(pwd)")"

echo "=== Scanning for checkpoints ==="

# 0. project.md - HIGHEST PRIORITY (simple project context file)
echo ""
echo "Project context file (project.md):"
if [ -f "$PWD/project.md" ]; then
  echo "  Found: $PWD/project.md"
  LAST_UPDATED=$(grep -m1 "^\*\*Last Updated\*\*" "$PWD/project.md" 2>/dev/null | sed 's/.*: //')
  echo "  Last Updated: ${LAST_UPDATED:-unknown}"
elif [ -f "$PWD/.claude/project.md" ]; then
  echo "  Found: $PWD/.claude/project.md"
  LAST_UPDATED=$(grep -m1 "^\*\*Last Updated\*\*" "$PWD/.claude/project.md" 2>/dev/null | sed 's/.*: //')
  echo "  Last Updated: ${LAST_UPDATED:-unknown}"
else
  echo "  (none found)"
fi

# 1. Project-local checkpoints
if [ -f ".claude/config.json" ] && command -v jq > /dev/null 2>&1; then
  LOCAL_CHECKPOINTS_PATH=$(jq -r '.paths.checkpoints // "docs/checkpoints"' .claude/config.json)
else
  LOCAL_CHECKPOINTS_PATH="docs/checkpoints"
fi

echo ""
echo "Project-local ($LOCAL_CHECKPOINTS_PATH):"
ls -t "$LOCAL_CHECKPOINTS_PATH"/*checkpoint*.md 2>/dev/null | head -5 | while read f; do
  echo "  $(basename "$f")"
done || echo "  (none found)"

# 2. Global checkpoints for current project
echo ""
echo "Global checkpoints for $CURRENT_PROJECT:"
ls -t ~/.claude/checkpoints/*"$CURRENT_PROJECT"*.md 2>/dev/null | head -5 | while read f; do
  echo "  $(basename "$f")"
done || echo "  (none found)"

# 3. Other recent global checkpoints
echo ""
echo "Other recent global checkpoints:"
ls -t ~/.claude/checkpoints/*.md 2>/dev/null | grep -v "$CURRENT_PROJECT" | head -5 | while read f; do
  echo "  $(basename "$f")"
done || echo "  (none found)"
```

### Auto-Selection Logic

If no argument provided, automatically select the best checkpoint:

1. **project.md** - if exists in `$PWD/project.md` or `$PWD/.claude/project.md` and < 7 days old (HIGHEST PRIORITY)
2. **Most recent project-local checkpoint** - if exists and < 7 days old
3. **Most recent global checkpoint for current project** - if exists and < 7 days old
4. **Present all options** - if no recent match or multiple candidates

If argument provided:
- Search term matches against all discovered checkpoints
- Full path used directly

## Step 1: Read and Verify Checkpoint

Once checkpoint is selected:

```bash
# Check git state
git branch --show-current
git status --short

# Check for codex review state
ls .claude/codex-review/requests 2>/dev/null || true
ls .claude/codex-review/approvals 2>/dev/null || true

# Check for project-specific learnings
if [ -d ".claude/learnings" ]; then
  echo "=== Recent Learnings for this project ==="
  ls -t .claude/learnings/*.md 2>/dev/null | head -5 | while read f; do
    title=$(grep -m1 "^# Learning:" "$f" 2>/dev/null | sed 's/^# Learning: //')
    category=$(grep -m1 "^\*\*Category:\*\*" "$f" 2>/dev/null | sed 's/\*\*Category:\*\* //')
    echo "- $title ($category)"
  done
fi

# Check for global learnings relevant to this work
if [ -d "$HOME/.claude/learnings" ]; then
  echo ""
  echo "=== Recent Global Learnings ==="
  ls -t ~/.claude/learnings/*.md 2>/dev/null | grep -v index.md | head -3 | while read f; do
    title=$(grep -m1 "^# Learning:" "$f" 2>/dev/null | sed 's/^# Learning: //')
    category=$(grep -m1 "^\*\*Category:\*\*" "$f" 2>/dev/null | sed 's/\*\*Category:\*\* //')
    echo "- $title ($category)"
  done
fi
```

Read the checkpoint completely and verify:
- Project path matches current directory (or note mismatch)
- Git branch matches checkpoint (or note discrepancy)
- Any pending codex reviews to address first

## Step 2: Build Mental Model

Based on the checkpoint, establish:
- **Primary Goal**: What is the overall objective?
- **Current State**: Where exactly did the previous session leave off?
- **Next Action**: What is the immediate next step?
- **Context**: What decisions or approaches are important to maintain?

## Step 3: Present Summary

```text
## Resuming: {checkpoint description}

**Source**: {project.md | project-local checkpoint | global checkpoint}
**Project**: {project name}
**Branch**: {branch} [matches/differs from checkpoint]

### Completed Previously
- {completed task 1}
- {completed task 2}

### Next Steps
1. **Immediate**: {next step from checkpoint}
2. {following task}
3. {subsequent task}

### Key Context
- {key decision 1}
- {key decision 2}

### Recent Learnings
{Show relevant learnings from both project and global scope}
- {learning 1 title} ({category}) - {project/global}
- {learning 2 title} ({category}) - {project/global}

### Pending Reviews
{If codex reviews pending, list them here}

### Files to Review
- {important file 1} - {why}
- {important file 2} - {why}

Ready to continue with: "{immediate next step}"?
```

## Step 4: Confirm and Begin

Ask for confirmation:
```text
Proceed with the next step, or adjust the plan?
```

On confirmation:
1. Create TodoWrite tasks from remaining items
2. Begin working on the immediate next step
3. Follow all normal development practices (TDD, git commits, etc.)

## Arguments

The command accepts an optional checkpoint identifier:

- **No argument**: Auto-select best checkpoint or present options
- **Filename**: `resume 2025-11-29-golden-paws-review-service.md`
- **Full path**: `resume ~/.claude/checkpoints/2025-11-29-golden-paws-review-service.md`
- **Search term**: `resume golden-paws` (finds most recent match across all sources)

## Cross-Project Resume

When resuming a checkpoint from a different project:

1. The checkpoint contains the project path
2. Inform user they need to switch directories:
   ```text
   This checkpoint is for project: golden-paws
   Path: /Users/dan/Projects/golden-paws-photography

   Please run in that directory:
     cd /Users/dan/Projects/golden-paws-photography
     claude
     # Then: /resume
   ```

## Important Principles

- **Assume Zero Prior Knowledge**: You have NO memory of previous conversations. Everything comes from the checkpoint.
- **Respect Documented Decisions**: Don't question past choices unless blocking
- **Ask Don't Assume**: If unclear, ask rather than guess
- **Maintain Continuity**: This is continuing work, not starting fresh
- **Surface Learnings**: Always check for relevant learnings that might help

## What NOT To Do

- Don't suggest rewriting unless checkpoint identifies a problem
- Don't question past decisions unless they block progress
- Don't read all code - use checkpoint context to focus attention
- Don't ignore "failed approaches" - they save time

## Cleanup

After successfully resuming and completing work:
```bash
# Optionally archive old checkpoint
mv ~/.claude/checkpoints/{old-checkpoint}.md ~/.claude/checkpoints/archive/
# Or for project-local
mv docs/checkpoints/{old-checkpoint}.md docs/checkpoints/archive/
```
