# Claude Learning Companion (CLC)

> Persistent memory and pattern tracking for Claude Code sessions.

Claude Code learns from your failures and successes, building institutional knowledge that persists across sessions. Patterns strengthen automatically. Install once, watch knowledge compound over weeks.

## Install

```bash
./install.sh              # Mac/Linux
./install.ps1             # Windows
```

**New to CLC?** See the [Getting Started Guide](GETTING_STARTED.md) for detailed step-by-step instructions including prerequisites and troubleshooting.

## First Use: Say "check in"

**Every session, start with `check in`.** This is the most important habit:

```bash
You: check in

Claude: [Queries CLC, starts dashboard, returns golden rules + heuristics]
```

**Auto-Setup on First Check-In:**
- **New user:** Everything installs automatically - config, commands, hooks
- **Existing CLAUDE.md:** Selection boxes to choose merge/replace/skip
- **Already configured:** Proceeds normally

**What "check in" does:**
- **First time ever:** Auto-installs config, hooks, /search, /checkin, /swarm commands
- **Start of session:** Loads knowledge, starts dashboard at http://localhost:3001 (Ctrl+click to open)
- **When stuck:** Searches for relevant patterns that might help
- **Before closing:** Ensures learnings are captured (CYA - cover your ass)

**When to check in:**
| Moment | Why |
|--------|-----|
| Start of every session | Load context, start dashboard, prevent repeating mistakes |
| When you hit a problem | See if CLC knows about this issue |
| Before closing session | Ensure learnings are captured |

## Core Features

| Feature | What It Does |
|---------|--------------|
| **Persistent Learning** | Failures and successes recorded to SQLite, survive across sessions |
| **Heuristics** | Patterns gain confidence through validation (0.0 -> 1.0) |
| **Golden Rules** | High-confidence heuristics promoted to constitutional principles |
| **Pheromone Trails** | Files touched by tasks tracked for hotspot analysis |
| **Coordinated Swarms** | Multi-agent workflows with specialized personas |
| **Local Dashboard** | Visual monitoring at http://localhost:3001 (no API tokens used) |
| **Session History** | Browse all Claude Code sessions in dashboard - search, filter by project/date, expand to see full conversations |
| **Cross-Session Continuity** | Pick up where you left off - search what you asked in previous sessions. Lightweight retrieval (~500 tokens), or ~20k for heavy users reviewing full day |
| **Async Watcher** | Background Haiku monitors your work, escalates to Opus only when needed. 95% cheaper than constant Opus monitoring |
| **Self-Healing QA** | Automatic failure classification and fix spawning with model escalation (haiku → sonnet → opus) |
| **Experiment Isolation** | Git worktree-based experiments with separate databases - safely test changes without affecting main |
| **Kanban Board** | Visual task management in dashboard with drag-drop, priorities, and links to learnings |
| **Graph Memory** | FalkorDB graph database for semantic relationships between heuristics (SQLite fallback when unavailable) |
| **CI/CD Workflow** | Dual AI reviewers (Gemini + Copilot), severity-based gating, auto-approval |

### CI/CD Workflow

A sophisticated PR workflow with dual AI reviewers and intelligent gating:

```
┌─────────────────────────────────────────┐
│  PHASE 1: REVIEW                        │
│  Push → /gemini review → Address feedback
│  (critical/high must be fixed)          │
└─────────────────────────────────────────┘
              │
              ▼ All critical/high resolved
        Comment /run-ci
              │
┌─────────────────────────────────────────┐
│  PHASE 2: CI TESTING                    │
│  Lint → Build → Tests                   │
│  Auto-approval on success               │
└─────────────────────────────────────────┘
```

**Key Features:**
- **Dual AI reviewers**: Gemini Code Assist + GitHub Copilot
- **Severity-based gating**: Only critical/high findings block CI (medium/low don't)
- **Auto-resolve outdated**: Threads on modified code resolved automatically
- **Bot auto-approval**: Automatic approval + `ready-to-merge` label when CI passes

**Migrate to your repos:**
```bash
./scripts/migrate-cicd-workflow.sh ~/Projects/my-app
```

See [CI/CD Wiki](https://github.com/haighd/claude-learning-companion/wiki/CI-CD) for full documentation.

### Hotspots
![Hotspots](assets/Hotspots.png)
Treemap of file activity - see which files get touched most and spot anomalies at a glance.

### Graph
![Graph](assets/graph.png)
Interactive knowledge graph showing how heuristics connect across domains.

### Analytics
![Analytics](assets/analytics.png)
Track learning velocity, success rates, and confidence trends over time.

### Kanban Board

Manage tasks visually in the dashboard's **Workflows** tab:

- **4 Columns**: Pending → In Progress → Review → Done
- **Drag & Drop**: Move tasks between columns
- **Priority Levels**: Set task importance
- **Link to Learnings**: Connect tasks to related heuristics

### Self-Healing QA

When Claude encounters errors, CLC automatically:

1. **Classifies** the failure (fixable vs unfixable)
2. **Spawns** a fix agent with appropriate model tier
3. **Escalates** through haiku → sonnet → opus if needed
4. **Circuit breaks** after repeated failures to prevent loops

Configure in `config/self-healing.yaml`.

### Experiment Isolation

Test risky changes safely with isolated git worktrees:

```bash
/experiment start my-feature    # Create isolated worktree + database
/experiment status              # See active experiments
/experiment merge my-feature    # Merge successful experiment back
/experiment discard my-feature  # Abandon failed experiment
/experiment clean               # Remove stale worktrees
```

Each experiment gets its own database, so learnings don't pollute main until you're ready.

### Cross-Session Continuity

Ever close a session and forget what you were working on? Use `/search` with natural language:

```bash
/search what was my last prompt?
/search what was I working on yesterday?
/search find prompts about git
/search when did I last check in?
```

Just type `/search` followed by your question in plain English. Pick up where you left off instantly.

**Token Usage:** ~500 tokens for quick lookups, scales with how much history you request.

### Session History (Dashboard)

Browse your Claude Code session history visually in the dashboard's **Sessions** tab:

- **Search** - Filter sessions by prompt text
- **Project Filter** - Focus on specific projects
- **Date Range** - Today, 7 days, 30 days, or all time
- **Expandable Cards** - Click to see full conversation with user/assistant messages
- **Tool Usage** - See what tools Claude used in each response

No tokens consumed - reads directly from `~/.claude/projects/` JSONL files.

### Async Watcher

A background Haiku agent monitors coordination state every 30 seconds. When it detects something that needs attention, it escalates to Opus automatically.

```text
┌─────────────────┐     exit 1      ┌─────────────────┐
│  Haiku (Tier 1) │ ──────────────► │  Opus (Tier 2)  │
│  Fast checks    │   "need help"   │  Deep analysis  │
│  ~$0.001/check  │                 │  ~$0.10/call    │
└─────────────────┘                 └─────────────────┘
```

Runs automatically - no user interaction required. See [watcher/README.md](watcher/README.md) for configuration and details.

## How It Works

```bash
+---------------------------------------------------+
|              The Learning Loop                    |
+---------------------------------------------------+
|  QUERY   ->  Check CLC for knowledge              |
|  APPLY   ->  Use heuristics during task           |
|  RECORD  ->  Capture outcome (success/failure)    |
|  PERSIST ->  Update confidence scores             |
|                    |                              |
|         (cycle repeats, patterns strengthen)      |
+---------------------------------------------------+
```

## Key Phrases

| Say This | What Happens |
|----------|--------------|
| `check in` | Start dashboard, query CLC, show golden rules + heuristics |
| `query CLC` | Same as check in |
| `what does CLC know about X` | Search for topic X |
| `record this failure: [lesson]` | Create failure log |
| `record this success: [pattern]` | Document what worked |
| `/search [question]` | Search session history with natural language |

## Quick Commands

```bash
# Check what has been learned
python ~/.claude/clc/query/query.py --stats

# Start dashboard manually (if needed)
cd ~/.claude/clc/dashboard-app && ./run-dashboard.sh

# Multi-agent swarm (Pro/Max plans)
/swarm investigate the authentication system

# Experiment isolation
/experiment start my-feature    # Start isolated experiment
/experiment status              # List active experiments
/experiment merge my-feature    # Merge back to main

# Start FalkorDB graph database (optional, for graph features)
cd ~/.claude/clc && docker compose up -d
```

## Programmatic Usage (v0.2.0+)

The QuerySystem uses async/await for non-blocking database operations:

```python
import asyncio
from query import QuerySystem

async def main():
    # Initialize with factory method
    qs = await QuerySystem.create()

    try:
        # Build context for a task
        context = await qs.build_context("My task", domain="debugging")

        # Query by domain
        results = await qs.query_by_domain("testing", limit=10)

        # Get statistics
        stats = await qs.get_statistics()

        # Run multiple queries concurrently (2.9x faster for mixed workloads)
        context, stats, recent = await asyncio.gather(
            qs.build_context("task"),
            qs.get_statistics(),
            qs.query_recent(limit=5)
        )
    finally:
        await qs.cleanup()

asyncio.run(main())
```

**CLI unchanged** - handles async internally:
```bash
python -m query --context --domain debugging
python -m query --stats
python -m query --validate
```

See [query/MIGRATION.md](query/MIGRATION.md) for migration guide from sync API.

## Swarm Agents

| Agent | Role |
|-------|------|
| **Researcher** | Deep investigation, gather evidence |
| **Architect** | System design, big picture |
| **Skeptic** | Break things, find edge cases |
| **Creative** | Novel solutions, lateral thinking |

## Documentation

**Quick Start:** [Getting Started Guide](GETTING_STARTED.md) - Step-by-step setup from zero to running

Full documentation in the [Wiki](https://github.com/haighd/claude-learning-companion/wiki):

- [Installation](https://github.com/haighd/claude-learning-companion/wiki/Installation) - Prerequisites, options, troubleshooting
- [Configuration](https://github.com/haighd/claude-learning-companion/wiki/Configuration) - CLAUDE.md, settings.json, hooks
- [Dashboard](https://github.com/haighd/claude-learning-companion/wiki/Dashboard) - Tabs, stats, themes
- [CI/CD](https://github.com/haighd/claude-learning-companion/wiki/CI-CD) - Dual AI reviewers, severity gating, auto-approval
- [Swarm](https://github.com/haighd/claude-learning-companion/wiki/Swarm) - Multi-agent coordination, blackboard pattern
- [CLI Reference](https://github.com/haighd/claude-learning-companion/wiki/CLI-Reference) - All query commands
- [Golden Rules](https://github.com/haighd/claude-learning-companion/wiki/Golden-Rules) - How to customize principles
- [Migration](https://github.com/haighd/claude-learning-companion/wiki/Migration) - Upgrading, team setup
- [Architecture](https://github.com/haighd/claude-learning-companion/wiki/Architecture) - Database schema, hooks system
- [Token Costs](https://github.com/haighd/claude-learning-companion/wiki/Token-Costs) - Usage breakdown, optimization

## Plan Compatibility

| Plan | Core + Dashboard | Swarm |
|------|------------------|-------|
| Free | Yes | No |
| Pro ($20) | Yes | Yes |
| Max ($100+) | Yes | Yes |

## Troubleshooting

### Dashboard fails on Windows with Git Bash (Issue #11)

If you see `Cannot find module @rollup/rollup-win32-x64-msvc` when starting the dashboard:

**Cause:** Git Bash makes npm think it's running on Linux, so it installs Linux-specific binaries instead of Windows binaries.

**Fix Option 1:** Use PowerShell or CMD for npm install:
```powershell
cd ~/.claude/clc/dashboard-app/frontend
rm -rf node_modules package-lock.json
npm install
```

**Fix Option 2:** Use Bun (handles platform detection correctly):
```bash
bun install
```

The run-dashboard.sh script will now detect this issue and warn you before failing.

## Links

- [Claude Code Docs](https://docs.anthropic.com/en/docs/claude-code)
- [Hooks System](https://docs.anthropic.com/en/docs/claude-code/hooks)
- [Issues & Support](https://github.com/haighd/claude-learning-companion/issues)

## License

MIT License

## Development Status

CLC (Claude Learning Companion) is under active development. Rapid commits reflect live experimentation, architectural refinement, and real-world usage. The main branch represents active research and may change frequently. Stable checkpoints will be published as versioned GitHub releases; users who prefer stability should rely on tagged releases rather than the latest commit.
