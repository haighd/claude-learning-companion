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

Your hooks should point to the new CLC location. Replace `<HOME>` with your full home directory path (e.g., `/Users/username` on macOS, `/home/username` on Linux, or `C:\Users\username` on Windows):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "python3 \"<HOME>/.claude/clc/hooks/learning-loop/pre_tool_learning.py\"",
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
            "command": "python3 \"<HOME>/.claude/clc/hooks/learning-loop/post_tool_learning.py\"",
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
grep -nE "emergent-learning|\.claude/elf" ~/.claude/CLAUDE.md
```

Replace:
- `~/.claude/emergent-learning/` → `~/.claude/clc/`
- `emergent-learning` → `clc`
- `ELF` → `CLC`

## Step 3: Update Project CLAUDE.md Files

For each project that references ELF/emergent-learning:

```bash
# Find all project CLAUDE.md files with old references
find ~/Projects -name "CLAUDE.md" -exec grep -lE "emergent-learning|\.claude/elf" {} \;
```

Update the paths in each file.

## Step 4: Update Slash Commands

Check `~/.claude/commands/` for old paths:

```bash
grep -rnE "emergent-learning|\.claude/elf" ~/.claude/commands/
```

The CLC install should have updated these, but verify:
- `checkin.md` should reference `~/.claude/clc/query/query.py`
- Other commands should use `clc` paths

## Step 5: Verify Installation

Run the CLC query to verify everything works:

```bash
python3 ~/.claude/clc/query/query.py --context
```

Expected output: Golden rules, heuristics, and recent learnings.

## Common Issues

### "Module not found" errors
The hooks can't find Python modules. Fix:
```bash
cd ~/.claude/clc
python3 -m pip install peewee  # Or other specific dependencies if needed
```

### Old dashboard still running
Kill any old processes:

**Mac/Linux**
```bash
pkill -f "emergent-learning"
pkill -f ".claude/elf"
pkill -f "dashboard-app"
```

**Windows (PowerShell)**
```powershell
# Stop processes by command line content
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*emergent-learning*' -or $_.CommandLine -like '*.claude\elf*' } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*dashboard-app*' } | Stop-Process -Force -ErrorAction SilentlyContinue
```

Then start the new dashboard:
```bash
bash ~/.claude/clc/dashboard-app/run-dashboard.sh
```

### Database migration needed
If you have existing data:
```bash
python3 ~/.claude/clc/scripts/migrate_db.py
```

## Cleanup (Optional)

After confirming CLC works, remove old installation:

```bash
# Backup first
mv ~/.claude/emergent-learning ~/.claude/emergent-learning.bak
mv ~/.claude/elf ~/.claude/elf.bak

# Or delete if you have no customizations
rm -rf ~/.claude/emergent-learning
rm -rf ~/.claude/elf
```

## Verification Checklist

- [ ] `~/.claude/settings.json` hooks point to `clc/`
- [ ] `~/.claude/CLAUDE.md` references `clc`
- [ ] Project CLAUDE.md files updated
- [ ] `python3 ~/.claude/clc/query/query.py --context` works
- [ ] Dashboard starts: `bash ~/.claude/clc/dashboard-app/run-dashboard.sh`
- [ ] Old `emergent-learning` directory removed or backed up
