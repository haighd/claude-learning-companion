# CLI Reference

## Query Commands

```bash
# Build full context (what agents see)
~/.claude/clc/query/query.py --context

# Query by domain
~/.claude/clc/query/query.py --domain testing

# Query by tags
~/.claude/clc/query/query.py --tags api,error

# Get recent learnings
~/.claude/clc/query/query.py --recent 10

# View statistics
~/.claude/clc/query/query.py --stats

# Validate database
~/.claude/clc/query/query.py --validate

# Health check (meta-observer)
~/.claude/clc/query/query.py --health-check

# Output formats
~/.claude/clc/query/query.py --stats --format json
~/.claude/clc/query/query.py --recent 20 --format csv
```

## Programmatic Usage (v0.2.0+)

QuerySystem uses async/await for non-blocking operations:

```python
import asyncio
from query import QuerySystem

async def main():
    qs = await QuerySystem.create()
    try:
        # Single query
        context = await qs.build_context("My task", domain="debugging")

        # Concurrent queries (2.9x faster for mixed workloads)
        context, stats, recent = await asyncio.gather(
            qs.build_context("task"),
            qs.get_statistics(),
            qs.query_recent(limit=5)
        )
    finally:
        await qs.cleanup()

asyncio.run(main())
```

### Available Methods

| Method | Description |
|--------|-------------|
| `await qs.build_context(task, domain, tags)` | Build full agent context |
| `await qs.get_golden_rules()` | Get constitutional rules |
| `await qs.query_by_domain(domain, limit)` | Query by domain |
| `await qs.query_by_tags(tags, limit)` | Query by tags |
| `await qs.query_recent(limit)` | Get recent learnings |
| `await qs.get_statistics()` | Get knowledge base stats |
| `await qs.get_decisions(domain)` | Get architecture decisions |
| `await qs.get_assumptions(domain)` | Get assumptions |
| `await qs.get_invariants(domain)` | Get invariants |
| `await qs.validate_database()` | Validate DB integrity |

## Session Search

Search your session history with natural language using the `/search` slash command:

```bash
/search what was my last prompt?
/search what was I working on yesterday?
/search find prompts about git
/search when did I last check in?
/search show me recent conversations
```

Type `/search` followed by any question in plain English. Claude will search your session logs and answer based on your conversation history.

**Token Usage:** ~500 tokens for quick lookups, scales with how much history you request.

## Recording Scripts

```bash
# Record a failure
~/.claude/clc/scripts/record-failure.sh

# Record a heuristic
~/.claude/clc/scripts/record-heuristic.sh

# Start an experiment
~/.claude/clc/scripts/start-experiment.sh
```

## Conductor Commands

```bash
# List workflow runs
python3 ~/.claude/clc/conductor/query_conductor.py --workflows

# Show specific run
python3 ~/.claude/clc/conductor/query_conductor.py --workflow 123

# Show failures
python3 ~/.claude/clc/conductor/query_conductor.py --failures

# Show hotspots
python3 ~/.claude/clc/conductor/query_conductor.py --hotspots

# Show trails by scent
python3 ~/.claude/clc/conductor/query_conductor.py --trails --scent blocker

# Statistics
python3 ~/.claude/clc/conductor/query_conductor.py --stats
```
