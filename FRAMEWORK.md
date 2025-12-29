# Claude Learning Companion

> Institutional knowledge that persists across Claude sessions.
> Agents are temporary workers; CLC is permanent.

## Quick Start

```bash
# Load context before any task
python3 ~/.claude/clc/query/query.py --context

# Check domain-specific knowledge
python3 ~/.claude/clc/query/query.py --domain coordination

# Record a failure
~/.claude/clc/scripts/record-failure.sh

# Start an experiment
~/.claude/clc/scripts/start-experiment.sh
```

## Architecture

```bash
~/.claude/clc/
├── FRAMEWORK.md              # This file
├── agents/                   # Agent personalities
│   ├── researcher/           # Deep investigation
│   ├── architect/            # System design
│   ├── creative/             # Novel solutions
│   └── skeptic/              # Breaking things
├── memory/                   # Accumulated knowledge
│   ├── failures/             # Documented failures
│   ├── successes/            # Documented successes
│   ├── heuristics/           # Extracted rules
│   ├── golden-rules.md       # Proven principles (Tier 1)
│   └── index.db              # SQLite for queries
├── experiments/              # Active and archived experiments
├── cycles/                   # Learning loop records
├── ceo-inbox/                # Human decision requests
├── query/                    # Retrieval system
├── scripts/                  # Helper scripts
└── logs/                     # System logs
```

## The Learning Cycle

```text
TRY → BREAK → ANALYZE → LEARN → NEXT
 │      │        │        │       │
 │      │        │        │       └→ Iterate or move on
 │      │        │        └→ Extract heuristics
 │      │        └→ Understand WHY
 │      └→ Intentionally stress test
 └→ Implement approach
```

## Knowledge Tiers

1. **Golden Rules** - Always loaded (~500 tokens). Proven principles.
2. **Domain Knowledge** - Query-matched content (~2-5k tokens).
3. **Deep History** - On-demand full documents.

## Agent Personas

| Agent | Role | Trigger |
|-------|------|---------|
| Researcher | Investigation, evidence | "We need to understand X" |
| Architect | Design, structure | "How should we build X" |
| Creative | Novel solutions | "We're stuck on X" |
| Skeptic | Breaking, QA | "Is X ready?" |

## CEO Escalation

Escalate to human when:
- High risk (production, data loss)
- Multiple valid approaches with tradeoffs
- Ethical considerations
- Resource commitments
- Uncertainty

## Core Principle

> Don't just note what happened; extract the transferable principle.

Outcomes are specific. Heuristics apply broadly.
