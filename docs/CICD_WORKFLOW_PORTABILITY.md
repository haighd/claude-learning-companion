# CI/CD Workflow Portability Guide

This guide explains how to adopt the dual AI reviewer workflow with severity-based gating in your own repositories.

## Overview

The workflow provides:
- **Dual AI reviewers**: Gemini Code Assist + GitHub Copilot
- **Severity-based gating**: Only critical/high findings block CI
- **Auto-resolve outdated threads**: Threads on modified code resolved automatically
- **Bot auto-approval**: Automatic approval when all conditions met

## Prerequisites

1. **GitHub repository** with Actions enabled
2. **Python 3.11+** available in CI environment
3. **Bot account** (optional but recommended for auto-approval)
4. **Gemini Code Assist** installed from GitHub Marketplace
5. **GitHub Copilot** enabled for the repository

## Quick Start

### Automated Migration (Recommended)

Use the migration script to automate most steps:

```bash
# From the CLC repository
./scripts/migrate-cicd-workflow.sh /path/to/your/repo

# With bot account setup
./scripts/migrate-cicd-workflow.sh --with-bot-setup /path/to/your/repo

# Dry run to see what would change
./scripts/migrate-cicd-workflow.sh --dry-run /path/to/your/repo

# Customize bot name and maintainer
./scripts/migrate-cicd-workflow.sh --bot-name mybot --maintainer alice /path/to/your/repo
```

The script will:
- Copy all workflow files with customized usernames
- Copy and make executable the categorize-findings.py script
- Create required GitHub labels (ready-to-merge, do-not-merge)
- Optionally configure bot account and secrets

After running, follow the manual steps printed by the script.

---

### Manual Migration

If you prefer manual setup, follow these steps:

### Step 1: Copy Workflow Files

Copy these files to your repository's `.github/workflows/` directory:

```
.github/workflows/
├── run-ci.yml              # Main CI workflow with severity gating
├── auto-resolve-outdated.yml  # Auto-resolve threads on modified code
└── auto-approve.yml        # Bot auto-approval (optional)
```

### Step 2: Copy Helper Scripts

Copy these to your `scripts/` directory:

```
scripts/
└── categorize-findings.py  # Severity categorization script
```

Make the script executable:
```bash
chmod +x scripts/categorize-findings.py
```

### Step 3: Configure Repository Secrets (for auto-approval)

If using bot auto-approval:

1. Create a bot account (e.g., `yourorg-bot`)
2. Generate a PAT with `repo` scope
3. Add the bot as a collaborator with Write access
4. Add repository secret: `BOT_PAT` = the bot's PAT

### Step 4: Create Labels

Create these labels in your repository:
- `ready-to-merge` - Applied when PR is ready for final merge
- `do-not-merge` - Blocks auto-approval (optional)

## Workflow Configuration

### Customizing Severity Patterns

Edit `scripts/categorize-findings.py` to customize severity detection:

```python
SEVERITY_PATTERNS = {
    'critical': [
        r'!\[critical\]',
        r'!\[security-critical\]',
        r'\*\*critical\*\*',
        # Add your patterns here
    ],
    'high': [...],
    'medium': [...],
    'low': [...],
}
```

### Customizing CI Jobs

Edit `run-ci.yml` to add your project's build/test steps:

```yaml
python-checks:
  # Replace with your language/framework checks
  steps:
    - name: Your lint step
    - name: Your build step
    - name: Your test step
```

### Customizing Blocking Labels

Edit `auto-approve.yml` to change which labels block auto-approval:

```javascript
const blockingLabels = ['do-not-merge', 'needs-discussion', 'blocked', 'wip'];
```

## File Reference

### run-ci.yml

Triggered by `/run-ci` comment. Features:
- Permission check (only collaborators can trigger)
- Severity-based thread checking
- Configurable build/test steps
- Success/failure reporting via comments

### auto-resolve-outdated.yml

Triggered on PR `synchronize` (new commits pushed). Features:
- Finds threads on modified code lines
- Resolves them automatically
- Posts summary comment

### auto-approve.yml

Triggered when `run-ci` workflow completes successfully. Features:
- Checks all conditions (no blocking labels, threads resolved)
- Approves via bot account
- Adds `ready-to-merge` label
- Notifies maintainer

### categorize-findings.py

Python script for severity categorization:
- Parses review comment badges
- Returns JSON with severity breakdown
- Exit code 0 = success, 1 = error

## Triggering Reviews

### Gemini Code Assist
```bash
gh pr comment <PR_NUMBER> --body "/gemini review"
```

### GitHub Copilot
Copilot reviews automatically on PR creation and updates.

## Workflow Diagram

```
┌─────────────────────────────────────────┐
│  PUSH CHANGES                           │
│  AI reviews trigger automatically       │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  ADDRESS FEEDBACK                       │
│  Critical/High → Must fix               │
│  Medium/Low → Optional                  │
│  Outdated → Auto-resolved               │
└─────────────┬───────────────────────────┘
              │ Critical/High resolved
              ▼
        Comment /run-ci
              │
┌─────────────┴───────────────────────────┐
│  CI TESTING                             │
│  Lint → Build → Tests                   │
│  Failure → Fix → Push again             │
└─────────────┬───────────────────────────┘
              │ All tests pass
              ▼
┌─────────────────────────────────────────┐
│  AUTO-APPROVAL                          │
│  → Bot approves PR                      │
│  → ready-to-merge label added           │
│  → Maintainer notified                  │
└─────────────────────────────────────────┘
```

## Troubleshooting

### Bot approval fails with "Resource not accessible"
- Ensure BOT_PAT has `repo` scope
- Ensure bot account has Write access to repository

### Severity categorization not working
- Check Python 3.11+ is available in CI
- Verify script has execute permission
- Check `GITHUB_TOKEN` and `GITHUB_REPOSITORY` env vars are set

### Auto-resolve not triggering
- Workflow triggers on `synchronize` event only
- Verify workflow file is on the default branch

### Reviews not appearing
- Check Gemini Code Assist is installed
- Check Copilot is enabled for the repository
- Verify bot accounts have repository access

## Migration Checklist

### Automated by Script
- [x] Copy workflow files to `.github/workflows/`
- [x] Copy `categorize-findings.py` to `scripts/`
- [x] Make script executable
- [x] Create `ready-to-merge` label
- [x] Create `do-not-merge` label
- [x] Add `BOT_PAT` secret (with `--with-bot-setup`)
- [x] Add bot as collaborator (with `--with-bot-setup`)

### Manual Steps
- [ ] Customize build/test steps in `run-ci.yml`
- [ ] Create bot account (if using auto-approval)
- [ ] Install Gemini Code Assist from marketplace
- [ ] Enable GitHub Copilot
- [ ] Commit and push workflow files
- [ ] Test with a sample PR
