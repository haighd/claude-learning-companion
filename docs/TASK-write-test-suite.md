# Task: Write Test Suite for CLC Core Components

**Status:** Pending
**Created:** 2025-12-16
**Priority:** High

## Summary

The CLC project has 23 test files in `tests/` but many have issues (missing imports, missing fixtures, outdated dependencies). Rather than fix the broken tests, we should write a new focused test suite for core components.

## Background

During PR #1 (rename emergent-learning to clc), we identified that:
- `test_claim_chains*.py` - ImportError: cannot import 'BlockedError' from blackboard
- `test_conductor_workflow.py` - FileNotFoundError: missing `init_db.sql`
- Multiple other tests have similar dependency/fixture issues

## Proposed Approach

Write new, focused tests starting with the most critical components:

### Priority 1: Query System (`query/query.py`)
- [ ] Test `build_context()` method
- [ ] Test relevance scoring
- [ ] Test domain filtering
- [ ] Test database queries (with SQLite in-memory)

### Priority 2: Learning Loop Hooks (`hooks/learning-loop/`)
- [ ] Test `pre_tool_learning.py` - heuristic lookup
- [ ] Test `post_tool_learning.py` - outcome recording
- [ ] Test `get_conductor_and_node()` helper
- [ ] Test trail laying functionality

### Priority 3: Conductor (`conductor/`)
- [ ] Test workflow start/completion
- [ ] Test node execution recording
- [ ] Test run status updates

### Priority 4: Dashboard API (`dashboard-app/backend/`)
- [ ] Test core endpoints
- [ ] Test database utilities

## Technical Notes

- Use `pytest` with `pytest-asyncio` for async tests
- Use in-memory SQLite for database tests (no external dependencies)
- Create proper fixtures in `conftest.py`
- Aim for tests that actually run in CI

## Acceptance Criteria

- [ ] At least 10 passing tests for Priority 1 (query system)
- [ ] At least 5 passing tests for Priority 2 (hooks)
- [ ] All tests run successfully in GitHub Actions CI
- [ ] Tests are documented with clear docstrings

## To Start This Task

```bash
cd ~/.claude/clc
# Create a new branch
git checkout main && git pull
git checkout -b feat/core-test-suite

# Start with query tests
# Reference: tests/test_enhancements.py (has some useful patterns)
```
