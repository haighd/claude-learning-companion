# Migrating from ELF (Emergent Learning Framework) to CLC

This guide covers converting existing projects that use the old `emergent-learning` or `elf` paths to the new `clc` (Claude Learning Companion) structure.

## Quick Summary

| Old Path/Reference | New Path/Reference |
|-------------------|-------------------|
| `~/.claude/emergent-learning/` | `~/.claude/clc/` |
| `~/.claude/elf/` | `~/.claude/clc/` |
| `emergent-learning` | `clc` |
| `ELF` | `CLC` |

## Step 1: Update ~/.claude/settings.json

Your hooks should point to the new CLC location:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "python3 \"~/.claude/clc/hooks/learning-loop/pre_tool_learning.py\"",
            "type": "command"
          }
        ],
        "matcher": "Task"
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "command": "python3 \"~/.claude/clc/hooks/learning-loop/post_tool_learning.py\"",
            "type": "command"
          }
        ],
        "matcher": "Task"
      }
    ]
  }
}
```

**Automated fix:**
```bash
# Re-run install to update settings.json
bash ~/.claude/clc/setup/install.sh --mode merge
```

## Step 2: Update Global CLAUDE.md

Check `~/.claude/CLAUDE.md` for any old references:

```bash
grep -n "emergent-learning\|\.claude/elf" ~/.claude/CLAUDE.md
```

Replace:
- `~/.claude/emergent-learning/` → `~/.claude/clc/`
- `emergent-learning` → `clc`
- `ELF` → `CLC`

## Step 3: Update Project CLAUDE.md Files

For each project that references ELF/emergent-learning:

```bash
# Find all project CLAUDE.md files with old references
find ~/Projects -name "CLAUDE.md" -exec grep -l "emergent-learning\|\.claude/elf" {} \;
```

Update the paths in each file.

## Step 4: Update Slash Commands

Check `~/.claude/commands/` for old paths:

```bash
grep -rn "emergent-learning" ~/.claude/commands/
```

The CLC install should have updated these, but verify:
- `checkin.md` should reference `~/.claude/clc/query/query.py`
- Other commands should use `clc` paths

## Step 5: Verify Installation

Run the CLC query to verify everything works:

```bash
python ~/.claude/clc/query/query.py --context
```

Expected output: Golden rules, heuristics, and recent learnings.

## Common Issues

### "Module not found" errors
The hooks can't find Python modules. Fix:
```bash
cd ~/.claude/clc
pip install -r requirements.txt
```

### Old dashboard still running
Kill any old processes:
```bash
pkill -f "emergent-learning"
pkill -f "dashboard-app"
```

Then start the new dashboard:
```bash
bash ~/.claude/clc/dashboard-app/run-dashboard.sh
```

### Database migration needed
If you have existing data:
```bash
python ~/.claude/clc/scripts/migrate_db.py
```

## Cleanup (Optional)

After confirming CLC works, remove old installation:

```bash
# Backup first
mv ~/.claude/emergent-learning ~/.claude/emergent-learning.bak

# Or delete if you have no customizations
rm -rf ~/.claude/emergent-learning
```

## Verification Checklist

- [ ] `~/.claude/settings.json` hooks point to `clc/`
- [ ] `~/.claude/CLAUDE.md` references `clc`
- [ ] Project CLAUDE.md files updated
- [ ] `python ~/.claude/clc/query/query.py --context` works
- [ ] Dashboard starts: `bash ~/.claude/clc/dashboard-app/run-dashboard.sh`
- [ ] Old `emergent-learning` directory removed or backed up
