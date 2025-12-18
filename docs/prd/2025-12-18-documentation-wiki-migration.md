---
title: "Documentation & Wiki Migration"
status: implemented
author: "Dan Haight"
created: 2025-12-18
last_updated: 2025-12-18
version: "1.0"
---

# PRD: Documentation & Wiki Migration

## Overview

### Problem Statement

The CLC repository README.md contains 11 dead links pointing to the old `Spacehunterz/Claude-Learning-Companion_CLC` repository. The actual repo is `haighd/claude-learning-companion`. Additionally, the GitHub wiki has no content despite 10 fully-written wiki pages existing locally in the `wiki/` directory.

### Opportunity

Fix all documentation to point to the correct repository, populate the GitHub wiki with existing content, and ensure all documentation accurately reflects the current CLC framework. This improves user onboarding and reduces confusion from dead links.

### Proposed Solution

1. Update all links in README.md to point to `haighd/claude-learning-companion`
2. Push all 10 wiki pages from `wiki/` directory to GitHub wiki
3. Fix GETTING_STARTED.md git clone URL
4. Audit README.md content for accuracy against current framework

## Users & Stakeholders

### Target Users

#### New CLC Users
- **Who**: Developers discovering CLC for the first time
- **Needs**: Working documentation links, clear installation instructions
- **Pain Points**: Dead links break trust and make setup confusing

#### Existing CLC Users
- **Who**: Users who want to reference documentation
- **Needs**: Accurate, up-to-date documentation
- **Pain Points**: Wiki links 404, can't find detailed guides

### Stakeholders
- **Repository Owner (Dan)**: Wants professional, accurate documentation

## User Journey

### Current State
1. User visits repo README → Sees documentation links
2. Clicks wiki link → Gets 404 (wrong repo)
3. Tries GETTING_STARTED.md → Git clone points to wrong repo
4. User frustrated, unsure if project is maintained

### Future State
1. User visits repo README → Sees documentation links
2. Clicks wiki link → Reaches populated wiki with full docs
3. Can follow installation steps with correct URLs
4. Confidence in project, smooth onboarding

## Requirements

### Functional Requirements

#### Must Have (P0)
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-001 | Fix all wiki links in README.md | All 10 wiki page links point to `haighd/claude-learning-companion/wiki/*` |
| FR-002 | Fix main wiki link in README.md | Main wiki link goes to correct repo wiki home |
| FR-003 | Fix Issues link in README.md | Issues link points to `haighd/claude-learning-companion/issues` |
| FR-004 | Fix git clone URL in GETTING_STARTED.md | Clone URL is `haighd/claude-learning-companion.git` |
| FR-005 | Push wiki content to GitHub | All 10 pages from `wiki/` appear on GitHub wiki |

#### Should Have (P1)
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-006 | Verify README feature descriptions | All features listed match actual current functionality |
| FR-007 | Update any stale screenshots if needed | Images in `assets/` match current dashboard UI |
| FR-008 | Cross-reference wiki internal links | Wiki page links to other wiki pages work |

#### Nice to Have (P2)
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-009 | Add sidebar navigation to wiki | GitHub wiki sidebar has organized link structure |

### Non-Functional Requirements

| Category | Requirement | Target |
|----------|-------------|--------|
| Accessibility | All links must be functional | 0 broken links |
| Consistency | URLs follow same pattern | All use `haighd/claude-learning-companion` |

## Scope

### In Scope
- README.md link fixes (11 links)
- GETTING_STARTED.md link fix (1 link)
- GitHub wiki population (10 pages)
- Content accuracy audit of README.md

### Out of Scope
- Rewriting wiki content (already written)
- Adding new wiki pages
- Major README restructuring
- GitHub Pages setup

### Dependencies
- GitHub wiki must be enabled on repo (confirmed: `has_wiki: true`)
- Git access to wiki repo (`haighd/claude-learning-companion.wiki.git`)

## Success Metrics

### Primary Metrics
| Metric | Baseline | Target | Stretch |
|--------|----------|--------|---------|
| Broken links in README | 11 | 0 | 0 |
| Wiki pages published | 0 | 10 | 10 |
| GETTING_STARTED broken links | 1 | 0 | 0 |

### Secondary Metrics
| Metric | Target |
|--------|--------|
| All wiki internal links working | 100% |

### Measurement Plan
- Manual link check after changes
- GitHub wiki page count verification

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Wiki push fails due to permissions | Low | Medium | Verify repo owner has wiki write access |
| Internal wiki links break | Medium | Low | Test all cross-references after push |
| README content inaccurate | Medium | Medium | Read each feature claim, verify against code |

## Open Questions

- [x] What is the correct repo URL? → `haighd/claude-learning-companion`
- [x] Does wiki content exist locally? → Yes, 10 pages in `wiki/`
- [x] Are there any other files with stale ELF/Spacehunterz references? → Yes, found and fixed in update.sh, update.ps1, FUNDING.yml, CLAUDE.md, blog-post-draft.md

## Implementation Notes

### Links to Fix in README.md

**Line 206-216 (Wiki section):**
```
OLD: https://github.com/Spacehunterz/Claude-Learning-Companion_CLC/wiki
NEW: https://github.com/haighd/claude-learning-companion/wiki
```

Each wiki page link follows same pattern:
- Installation → `/wiki/Installation`
- Configuration → `/wiki/Configuration`
- Dashboard → `/wiki/Dashboard`
- Swarm → `/wiki/Swarm`
- CLI-Reference → `/wiki/CLI-Reference`
- Golden-Rules → `/wiki/Golden-Rules`
- Migration → `/wiki/Migration`
- Architecture → `/wiki/Architecture`
- Token-Costs → `/wiki/Token-Costs`

**Line 252 (Issues link):**
```
OLD: https://github.com/Spacehunterz/Claude-Learning-Companion_CLC/issues
NEW: https://github.com/haighd/claude-learning-companion/issues
```

### Link to Fix in GETTING_STARTED.md

**Lines 59-60:**
```
OLD: git clone https://github.com/Spacehunterz/Claude-Learning-Companion_CLC.git
NEW: git clone https://github.com/haighd/claude-learning-companion.git
```

### Wiki Push Process

GitHub wikis are separate git repos. To push:
```bash
git clone https://github.com/haighd/claude-learning-companion.wiki.git
cp wiki/*.md claude-learning-companion.wiki/
cd claude-learning-companion.wiki
git add .
git commit -m "Populate wiki with CLC documentation"
git push
```

## Appendix

### Files Affected
- `README.md` - 11 link updates
- `GETTING_STARTED.md` - 1 link update
- GitHub Wiki - 10 new pages

### Local Wiki Files
```
wiki/
├── Home.md
├── Installation.md
├── Configuration.md
├── Dashboard.md
├── Swarm.md
├── CLI-Reference.md
├── Golden-Rules.md
├── Migration.md
├── Architecture.md
└── Token-Costs.md
```

### Revision History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | Dan Haight | Initial draft |
