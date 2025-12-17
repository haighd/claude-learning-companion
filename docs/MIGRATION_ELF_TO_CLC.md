# Migrating from ELF (Emergent Learning Framework) to CLC

This guide covers converting existing projects that use the old `emergent-learning` or `elf` paths to the new `clc` (Claude Learning Companion) structure.

## Prerequisites

Before you begin, ensure you have cloned the new Claude Learning Companion (CLC) repository. The recommended location is `~/.claude/clc`. If you haven't, you can clone it via:

```bash
# Ensure the parent directory exists
mkdir -p ~/.claude

# Clone the repository
git clone <your-clc-repo-url> ~/.claude/clc
```

This guide assumes the CLC code is available at `~/.claude/clc`.

## Quick Summary

| Old Path/Reference | New Path/Reference |
|-------------------|-------------------|
| `~/.claude/emergent-learning/` | `~/.claude/clc/` |
| `~/.claude/elf/` | `~/.claude/clc/` |
| `emergent-learning` | `clc` |
| `ELF` | `CLC` |

## Step 1: Update ~/.claude/settings.json

Your hooks should point to the new CLC location. Replace `<HOME>` with your full home directory path (e.g., `/Users/username` on macOS, `/home/username` on Linux).

**On Windows:** The path must use double backslashes (`\\`) as path separators. A correct path would look like:
`"C:\\Users\\username\\.claude\\clc\\hooks\\learning-loop\\pre_tool_learning.py"`
We strongly recommend using the automated fix below to ensure paths are set correctly.

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

**Mac/Linux**
```bash
# Re-run install to update settings.json
bash ~/.claude/clc/setup/install.sh --mode merge
```

**Windows (PowerShell)**
```powershell
# Re-run install to update settings.json
# Run from within the clc repository directory
.\setup\install.ps1 --mode merge
```

## Step 2: Update Global CLAUDE.md

Check `~/.claude/CLAUDE.md` for any old references:

```bash
grep -nE "emergent-learning|\.claude/elf" ~/.claude/CLAUDE.md
```

Replace:
- `~/.claude/emergent-learning/` → `~/.claude/clc/`
- `~/.claude/elf/` → `~/.claude/clc/`
- `emergent-learning` → `clc`
- `ELF` → `CLC`

**Automated replacement (Mac/Linux):**
```bash
# Backup the file first, just in case
cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.migration-backup

# Run replacements
sed -i '.bak' -E \
  -e 's|~/.claude/emergent-learning/|~/.claude/clc/|g' \
  -e 's|~/.claude/elf/|~/.claude/clc/|g' \
  -e 's|\bemergent-learning\b|clc|g' \
  -e 's|Emergent Learning Framework|Claude Learning Companion|g' \
  -e 's|\bELF\b|CLC|g' \
  -e 's|\belf\b|clc|g' ~/.claude/CLAUDE.md
```

## Step 3: Update Project CLAUDE.md Files

For each project that references ELF/emergent-learning:

```bash
# Find and automatically update all project CLAUDE.md files
# Replace ~/Projects with the actual path to your projects directory
find ~/Projects -name "CLAUDE.md" -type f -print0 | xargs -0 sed -i '.bak' -E \
  -e 's|~/.claude/emergent-learning/|~/.claude/clc/|g' \
  -e 's|~/.claude/elf/|~/.claude/clc/|g' \
  -e 's|\bemergent-learning\b|clc|g' \
  -e 's|Emergent Learning Framework|Claude Learning Companion|g' \
  -e 's|\bELF\b|CLC|g' \
  -e 's|\belf\b|clc|g'
```

## Step 4: Update Slash Commands

Check and update `~/.claude/commands/` for old paths:

```bash
# Find and automatically update slash commands
find ~/.claude/commands/ -type f -name "*.md" -print0 | xargs -0 sed -i '.bak' -E \
  -e 's|~/.claude/emergent-learning/|~/.claude/clc/|g' \
  -e 's|~/.claude/elf/|~/.claude/clc/|g' \
  -e 's|\bemergent-learning\b|clc|g' \
  -e 's|Emergent Learning Framework|Claude Learning Companion|g' \
  -e 's|\bELF\b|CLC|g' \
  -e 's|\belf\b|clc|g'
```

**Windows users:** Use VS Code or another editor with global search-and-replace to perform these replacements across your files. Search for `emergent-learning`, `ELF`, `elf`, and `Emergent Learning Framework` and replace with the corresponding CLC terms.

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

**Mac/Linux**
```bash
bash ~/.claude/clc/dashboard-app/run-dashboard.sh
```

**Windows (PowerShell)**
```powershell
# Run from within the clc repository directory
.\dashboard-app\run-dashboard.ps1
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
