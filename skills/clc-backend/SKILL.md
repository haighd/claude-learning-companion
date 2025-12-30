# CLC Backend Interface

> Native skills interface for Claude Learning Companion backend services.

## Overview

This skill provides a unified interface to CLC backend services:
- **Query System** - Load context, heuristics, and learnings
- **Progressive Loading** - Tiered context retrieval with token budgets
- **Recording** - Capture failures, heuristics, and experiments
- **Agent Personas** - Access CLC personas via native subagents

## Quick Reference

| Action | Script | Purpose |
|--------|--------|---------|
| Query Context | `query/query.py --context` | Load relevant CLC knowledge |
| Progressive Load | `query/progressive.py` | Token-budgeted context loading |
| Record Failure | `scripts/record-failure.sh` | Document what went wrong |
| Record Heuristic | `scripts/record-heuristic.sh` | Capture learned pattern |
| Start Experiment | `scripts/start-experiment.sh` | Begin tracked experiment |
| Get Party Subagents | `agents/native_subagents.py --party X` | Get subagent configs for party |

## Query System

### Standard Query (Recommended First Step)

```bash
~/.claude/clc/query/query.py --context
```

Returns:
- Golden rules
- Relevant heuristics
- Recent learnings
- Active experiments
- Pending CEO decisions

### Domain-Specific Query

```bash
~/.claude/clc/query/query.py --domain security
```

Filters context to domain-relevant items.

### Progressive Loading (New)

For token-constrained contexts, use progressive disclosure:

```python
from progressive import progressive_query

result = progressive_query(
    task_description="Implement user authentication",
    domain="security",
    tier="recommended",  # essential | recommended | full
    max_tokens=5000
)

print(result['context'])  # Formatted context string
print(result['summary'])  # Token usage stats
```

**Tiers:**
- `essential` (~500 tokens) - Golden rules only
- `recommended` (~2-5k tokens) - Domain-relevant heuristics and learnings
- `full` (~5-10k tokens) - Complete context including experiments

## Recording Services

### Record Failure

```bash
FAILURE_TITLE="API returned 500 on user creation"
FAILURE_ROOT_CAUSE="Database connection pool exhausted"
FAILURE_LESSON="Add connection pool monitoring"
FAILURE_DOMAIN="database"
~/.claude/clc/scripts/record-failure.sh
```

### Record Heuristic

```bash
HEURISTIC_DOMAIN="testing"
HEURISTIC_RULE="Always mock external APIs in unit tests"
HEURISTIC_EXPLANATION="External dependencies cause flaky tests"
~/.claude/clc/scripts/record-heuristic.sh
```

### Start Experiment

```bash
EXPERIMENT_NAME="try-new-cache-strategy"
EXPERIMENT_HYPOTHESIS="Redis caching will reduce DB load by 50%"
~/.claude/clc/scripts/start-experiment.sh
```

## Agent Personas

CLC provides four analysis personas that map to native subagents:

| Persona | Native Type | Use When |
|---------|-------------|----------|
| researcher | research-analyst | Need evidence, best practices |
| architect | microservices-architect | System design, structure |
| creative | general-purpose | Need fresh approaches |
| skeptic | code-reviewer | Validation, finding flaws |

### Get Subagent Config

```bash
# Get native subagent config for a persona
python ~/.claude/clc/agents/native_subagents.py --persona researcher

# Get all subagents for a party (team composition)
python ~/.claude/clc/agents/native_subagents.py --party code-review
```

### Programmatic Access

```python
from native_subagents import get_subagent_config, get_party_subagents

# Single persona
config = get_subagent_config("researcher")
# Returns: {"subagent_type": "research-analyst", "description": "...", ...}

# Party composition
configs = get_party_subagents("code-review")
# Returns: [{"subagent_type": "code-reviewer", "is_lead": True, ...}, ...]
```

## Integration with Claude Code

### In Task Tool Prompts

When spawning subagents, include CLC context:

```
You are a {persona} agent.

Before starting:
```bash
~/.claude/clc/query/query.py --context
```

Apply relevant golden rules and heuristics to your work.

When you learn something important:
```bash
HEURISTIC_DOMAIN="{domain}"
HEURISTIC_RULE="{what you learned}"
HEURISTIC_EXPLANATION="{why it matters}"
~/.claude/clc/scripts/record-heuristic.sh
```
```

### Hooks Integration

CLC hooks automatically:
- Load context on session start (`hooks/session_start_loader.py`)
- Save checkpoints before compaction (`hooks/pre_compact.py`)
- Capture learnings from subagents (`hooks/subagent_learning.py`)
- Warn before /clear with uncommitted state (`hooks/pre_clear_checkpoint.py`)

## Files

```
~/.claude/clc/
├── query/
│   ├── query.py          # Main context loader
│   └── progressive.py    # Token-budgeted loading
├── agents/
│   ├── native_subagents.py  # Persona→subagent mapping
│   └── parties.yaml         # Team compositions
├── hooks/
│   ├── session_start_loader.py
│   ├── pre_compact.py
│   ├── pre_clear_checkpoint.py
│   └── subagent_learning.py
├── scripts/
│   ├── record-failure.sh
│   ├── record-heuristic.sh
│   └── start-experiment.sh
└── skills/
    └── clc-backend/SKILL.md  # This file
```

## See Also

- [CLAUDE.md](/CLAUDE.md) - Main CLC integration guide
- [Golden Rules](/golden-rules/RULES.md) - Constitutional principles
- [Agent Coordination](/skills/agent-coordination/SKILL.md) - Multi-agent blackboard
