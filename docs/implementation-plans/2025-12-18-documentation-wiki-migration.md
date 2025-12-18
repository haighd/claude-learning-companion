---
title: "Documentation & Wiki Migration"
status: draft
author: "Dan Haight"
created: 2025-12-18
last_updated: 2025-12-18
version: "1.0"
related_prd: "docs/prd/2025-12-18-documentation-wiki-migration.md"
---

# Implementation Plan: Documentation & Wiki Migration

## Overview

Fix all dead links pointing to the old `Spacehunterz/Claude-Learning-Companion_CLC` repository, populate the GitHub wiki with existing content, and update related files to reference the correct `haighd/claude-learning-companion` repository.

## Current State Analysis

### Files Requiring Updates

| File | Line(s) / Variable | Issue |
|------|---------|-------|
| `README.md` | 206-216, 252 | 11 wiki/issues links to wrong repo |
| `GETTING_STARTED.md` | 59, 60 | Git clone URL and cd command wrong |
| `update.sh` | 31 | `GITHUB_REPO` variable wrong |
| `update.ps1` | 36 | `$GithubRepo` variable wrong |
| `.github/FUNDING.yml` | 3, 13 | GitHub sponsor username wrong |
| `docs/blog-post-draft.md` | 99 | Old ELF repo reference |
| `CLAUDE.md` | 48 | Repo name in git remotes section |

### Wiki Content Ready to Deploy

All 10 wiki pages exist in `wiki/` directory:
- `Home.md` - Uses relative internal links (correct format)
- `Installation.md`
- `Configuration.md`
- `Dashboard.md`
- `Swarm.md`
- `CLI-Reference.md`
- `Golden-Rules.md`
- `Migration.md`
- `Architecture.md`
- `Token-Costs.md`

## Desired End State

1. All links in documentation point to `haighd/claude-learning-companion`
2. GitHub wiki is populated with all 10 pages
3. Update scripts fetch from correct repository
4. All internal wiki links work correctly

## What We're NOT Doing

- Rewriting or restructuring wiki content
- Adding new wiki pages
- Setting up GitHub Pages
- Major README restructuring
- Changing wiki page filenames (they already match GitHub's expected format)

## Implementation Approach

Sequential phases to minimize risk of broken state.

---

## Phase 1: Update README.md Links

**Goal:** Fix all 11 dead links in README.md

### Tasks

1.1. Replace all wiki links (lines 206-216):
```
OLD: https://github.com/Spacehunterz/Claude-Learning-Companion_CLC/wiki
NEW: https://github.com/haighd/claude-learning-companion/wiki
```

1.2. Replace issues link (line 252):
```
OLD: https://github.com/Spacehunterz/Claude-Learning-Companion_CLC/issues
NEW: https://github.com/haighd/claude-learning-companion/issues
```

### Success Criteria

**Automated:**
```bash
# Zero matches for old repo in README
grep -Ec "Spacehunterz|Claude-Learning-Companion_CLC" README.md
# Expected: 0
```

**Manual:**
- Click each wiki link, verify 404 until wiki is populated (Phase 3)

---

## Phase 2: Update GETTING_STARTED.md

**Goal:** Fix git clone instructions

### Tasks

2.1. Replace clone URL (line 59):
```
OLD: git clone https://github.com/Spacehunterz/Claude-Learning-Companion_CLC.git
NEW: git clone https://github.com/haighd/claude-learning-companion.git
```

2.2. Replace cd command (line 60):
```
OLD: cd Claude-Learning-Companion_CLC
NEW: cd claude-learning-companion
```

### Success Criteria

**Automated:**
```bash
grep -Ec "Spacehunterz|Claude-Learning-Companion_CLC" GETTING_STARTED.md
# Expected: 0
```

---

## Phase 3: Populate GitHub Wiki

**Goal:** Push all 10 wiki pages to GitHub wiki

### Tasks

3.1. Clone the wiki repository:
```bash
git clone https://github.com/haighd/claude-learning-companion.wiki.git
```

3.2. Copy wiki content:
```bash
cp wiki/*.md claude-learning-companion.wiki/
```

3.3. Commit and push:
```bash
cd claude-learning-companion.wiki
git add .
git commit -m "Populate wiki with CLC documentation"
git push
cd ..
```

3.4. Clean up:
```bash
rm -rf claude-learning-companion.wiki
```

### Success Criteria

**Automated:**
```bash
# Clone wiki and verify page count
git clone --depth 1 https://github.com/haighd/claude-learning-companion.wiki.git /tmp/wiki-check 2>/dev/null && \
  ls /tmp/wiki-check/*.md | wc -l && \
  rm -rf /tmp/wiki-check
# Expected: 10
```

**Manual:**
- Visit https://github.com/haighd/claude-learning-companion/wiki
- Verify Home page loads
- Click through to each linked page from Home
- Verify internal links work (Installation, Configuration, etc.)

---

## Phase 4: Update Update Scripts

**Goal:** Fix update.sh and update.ps1 to fetch from correct repo

### Tasks

4.1. Update `update.sh` (line 31):
```bash
OLD: GITHUB_REPO="Spacehunterz/Claude-Learning-Companion_CLC"
NEW: GITHUB_REPO="haighd/claude-learning-companion"
```

4.2. Update `update.ps1` (line 36):
```powershell
OLD: $GithubRepo = "Spacehunterz/Claude-Learning-Companion_CLC"
NEW: $GithubRepo = "haighd/claude-learning-companion"
```

### Success Criteria

**Automated:**
```bash
grep -Ec "Spacehunterz|Claude-Learning-Companion_CLC" update.sh update.ps1
# Expected: 0
```

---

## Phase 5: Update Supporting Files

**Goal:** Fix remaining stale references

### Tasks

5.1. Update `.github/FUNDING.yml`:
```yaml
# Line 3
OLD: github: Spacehunterz
NEW: github: haighd

# Line 13
OLD: buy_me_a_coffee: spacehunterz
NEW: buy_me_a_coffee: # (remove or update to correct username)
```

5.2. Update `CLAUDE.md` (line 48):
```markdown
OLD: - `origin` = **PUBLIC REPO** (Claude-Learning-Companion_CLC) - PUSH HERE
NEW: - `origin` = **PUBLIC REPO** (claude-learning-companion) - PUSH HERE
```

5.3. Update `docs/blog-post-draft.md` (line 99):
```markdown
OLD: GitHub: [https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF](...)
NEW: GitHub: [https://github.com/haighd/claude-learning-companion](https://github.com/haighd/claude-learning-companion)
```

### Success Criteria

**Automated:**
```bash
# Comprehensive check - should only match PRD (which documents the old links)
grep -Er "Spacehunterz|Claude-Learning-Companion_CLC" --include="*.md" --include="*.sh" --include="*.ps1" --include="*.yml" . | grep -Ev "prd/|implementation-plans/"
# Expected: 0 matches (excluding prd/implementation-plans which document the change)
```

---

## Phase 6: Verification

**Goal:** Confirm all changes are correct

### Tasks

6.1. Run comprehensive grep to find any remaining stale references:
```bash
grep -Ern "Spacehunterz|Claude-Learning-Companion_CLC" --include="*.md" --include="*.sh" --include="*.ps1" --include="*.yml" --include="*.py" . | grep -Ev "prd/|implementation-plans/"
```

6.2. Manual link verification:
- Open README.md on GitHub
- Click each wiki link, verify loads
- Click Issues link, verify loads
- Test GETTING_STARTED.md clone instructions match repo

### Success Criteria

**Automated:**
```bash
# Final verification - zero stale references outside docs
grep -Er "Spacehunterz|Claude-Learning-Companion_CLC" --include="*.md" --include="*.sh" --include="*.ps1" --include="*.yml" . 2>/dev/null | grep -Ev "docs/prd|docs/implementation-plans" | wc -l
# Expected: 0
```

**Manual:**
- All README wiki links resolve to populated pages
- Issues link works
- Clone instructions in GETTING_STARTED.md work

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Wiki push fails | Verify write access first with `gh repo view haighd/claude-learning-companion --json hasWikiEnabled` |
| Missed stale references | Use comprehensive grep in Phase 6 |
| FUNDING.yml breaks sponsor button | Verify `haighd` has GitHub Sponsors enabled, or comment out |

## Dependencies

- Git write access to main repo
- Git write access to wiki repo (separate from main)
- GitHub CLI (`gh`) installed for verification

## Rollback Plan

All changes are in-repo text edits. Rollback via:
```bash
# Revert modified files
git checkout HEAD~1 -- README.md GETTING_STARTED.md update.sh update.ps1 .github/FUNDING.yml CLAUDE.md docs/blog-post-draft.md

# Remove new documentation files added in this PR
rm -f docs/prd/2025-12-18-documentation-wiki-migration.md
rm -f docs/implementation-plans/2025-12-18-documentation-wiki-migration.md
```

Wiki can be manually edited or re-cloned and modified.

---

## Summary

| Phase | Files | Changes |
|-------|-------|---------|
| 1 | README.md | 11 link updates |
| 2 | GETTING_STARTED.md | 2 line updates |
| 3 | GitHub Wiki | 10 pages pushed |
| 4 | update.sh, update.ps1 | 2 variable updates |
| 5 | FUNDING.yml, CLAUDE.md, blog-post-draft.md | 4 reference updates |
| 6 | All | Verification |

**Total: 19 discrete changes + wiki deployment**
