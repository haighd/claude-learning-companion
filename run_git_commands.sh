#!/bin/bash
# Sprint 2025-12-29 - Git commands to commit and push
# Run from: ~/.claude/clc

cd ~/.claude/clc

echo "=== Adding all files ==="
git add -A

echo "=== Committing ==="
git commit -m 'feat(sprint-2025-12-29): Complete all 11 sprint issues - hooks, query, agents, skills'

echo "=== Pushing to origin ==="
git push -u origin sprint/2025-12-29

echo "=== Creating PR ==="
gh pr create --title 'feat: Sprint 2025-12-29 - Complete 11 CLC enhancement issues' --base main --body 'Completes issues #63, #64, #65, #66, #68, #69, #71, #74 plus #58, #59, #72, #73.

New files:
- query/progressive.py - Progressive disclosure with token budgeting
- hooks/pre_clear_checkpoint.py - Pre-clear checkpoint hook
- hooks/subagent_learning.py - Subagent learning extraction
- agents/native_subagents.py - Persona to subagent mapping
- skills/clc-backend/ - Skills interface

CLAUDE.md optimized from 359 to 147 lines.'

echo "=== Requesting review ==="
# Get PR number and request review
PR_NUM=$(gh pr list --head sprint/2025-12-29 --json number -q '.[0].number')
gh pr comment "$PR_NUM" --body '/gemini review'

echo "=== Done! PR created and review requested ==="
