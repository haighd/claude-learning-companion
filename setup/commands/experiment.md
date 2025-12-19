---
description: Manage isolated experiments for risky CLC changes using git worktrees
---

# Experiment Management

Manage isolated experiments using git worktrees. This allows testing risky changes without affecting the main CLC workspace.

## Commands

Based on the argument provided, execute the appropriate action:

### `start <description>`
Create a new isolated experiment:
```bash
python3 ~/.claude/clc/scripts/experiment.py start "$ARGUMENTS"
```

### `status` or no arguments
Show all experiments:
```bash
python3 ~/.claude/clc/scripts/experiment.py status
```

### `list`
Alias for status:
```bash
python3 ~/.claude/clc/scripts/experiment.py list
```

### `merge [exp_id]`
Merge a successful experiment back to main:
```bash
python3 ~/.claude/clc/scripts/experiment.py merge $ARGUMENTS
```

### `discard [exp_id]`
Discard a failed experiment:
```bash
python3 ~/.claude/clc/scripts/experiment.py discard $ARGUMENTS
```

### `clean`
Clean up stale worktrees and branches:
```bash
python3 ~/.claude/clc/scripts/experiment.py clean
```

## Usage Examples

```bash
# Start a new experiment
/experiment start test new heuristic promotion logic

# Check experiment status
/experiment status

# Merge successful experiment (uses active if no ID given)
/experiment merge

# Merge specific experiment
/experiment merge abc123def456

# Discard failed experiment
/experiment discard

# Clean up orphaned artifacts
/experiment clean
```

## How It Works

1. **Start**: Creates a git worktree with isolated branch and database copy
2. **Work**: Make changes in the worktree directory
3. **Merge**: If successful, merges branch back to main
4. **Discard**: If failed, removes worktree and branch cleanly

## Architecture

```
Main Workspace (~/.claude/clc/)
  └─ Protected during experiments

Worktree (~/.claude/clc/.worktrees/exp-{id}/)
  ├─ Full copy of CLC code
  ├─ Isolated database (memory/index.db)
  └─ Experiment-specific changes
```

Parse $ARGUMENTS and run the appropriate command above.
