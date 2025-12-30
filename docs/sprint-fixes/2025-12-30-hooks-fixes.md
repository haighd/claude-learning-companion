# Sprint 2025-12-30: Hooks Fixes

## Issues Addressed

### Issue #78 - SessionStart:clear Hook Error
**Problem:** The SessionStart hook in ~/.claude/settings.json had an empty matcher ("matcher": ""), which matched ALL events including /clear command. This caused the session_start_loader.py to fire erroneously on /clear.

**Root Cause:** Line 124 in settings.json had "matcher": "" instead of a specific event matcher.

**Fix Applied:** Changed "matcher": "" to "matcher": "startup" so the hook only fires on conversation startup, not on /clear.

**File Changed:** ~/.claude/settings.json (line 124)

### Issue #79 - Permission Format Issues
**Problem:** Several permission entries used Base( instead of Bash(, which is invalid and would cause permission matching to fail.

**Root Cause:** Typo in permission entries - Base( instead of Bash(.

**Locations Fixed:**
- ~/.claude/settings.json lines 4-5
- ~/.claude/settings.local.json lines 4-5

**Fix Applied:** Changed all instances of Base( to Bash( in both settings files.

## Verification

After fixes:
- grep matcher ~/.claude/settings.json shows "matcher": "startup" on line 124
- grep Base( ~/.claude/settings.json returns no matches
- grep Base( ~/.claude/settings.local.json returns no matches

## Date
2025-12-30

## Agent
debugger (hooks-fixes group)
