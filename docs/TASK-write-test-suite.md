# Task: Write Test Suite for CLC Core Components

**Status:** Pending
**Created:** 2025-12-16
**Priority:** High

## Summary

The CLC project has 23 test files in `tests/` but many have issues (missing imports, missing fixtures, outdated dependencies). Rather than fix the broken tests, we should write a new focused test suite for core components.

**Handling Legacy Tests:** Delete the old, broken test files as they are replaced with new tests. The old tests have unresolvable dependency issues and keeping them around creates confusion about which tests are canonical. Clean deletion is preferred over archiving since the git history preserves the old tests if ever needed.

## Background

During PR #1 (rename emergent-learning to clc), we identified that:
- `test_claim_chains*.py` - ImportError: cannot import 'BlockedError' from blackboard
- `test_conductor_workflow.py` - FileNotFoundError: missing `init_db.sql`
- Multiple other tests have similar dependency/fixture issues

## Proposed Approach

Write new, focused tests starting with the most critical components:

### Priority 1: Query System (`query/query.py`)
- [ ] Test `build_context()` method (and relevance scoring)
- [ ] Test `query_by_domain()`
- [ ] Test `query_by_tags()`
- [ ] Test `query_recent()`
- [ ] Test `get_golden_rules()`
- [ ] Test `get_active_experiments()` and `get_pending_ceo_reviews()`
- [ ] Test `get_violations()` and `get_violation_summary()`
- [ ] Test `get_decisions()`, `get_invariants()`, `get_assumptions()`, `get_spike_reports()`
- [ ] Test `find_similar_failures()`
- [ ] Test `validate_database()`
- [ ] Test CLI functionality in `main()`

### Priority 2: Learning Loop Hooks (`hooks/learning-loop/`)
- `pre_tool_learning.py`
  - [ ] Test domain extraction logic
  - [ ] Test complexity and risk scoring (`ComplexityScorer`)
  - [ ] Test heuristic retrieval
- `post_tool_learning.py`
  - [ ] Test task outcome determination (`determine_outcome`) for success, failure, and unknown cases
  - [ ] Test heuristic validation logic (success/failure paths)
  - [ ] Test auto-recording of failures
  - [ ] Test advisory verification for risky patterns (`AdvisoryVerifier`)
  - [ ] Test trail laying functionality
  - [ ] Test `get_conductor_and_node()` helper

### Priority 3: Conductor (`conductor/`)
- [ ] Test workflow management (create, get, list)
- [ ] Test node execution recording (start, completion, failure)
- [ ] Test run status updates and context management
- [ ] Test `safe_eval_condition` helper with various inputs
- [ ] Test different workflow patterns:
  - [ ] Linear (A -> B -> C)
  - [ ] Branching (A -> B, A -> C)
  - [ ] Conditional branching
  - [ ] Converging (A -> C, B -> C)
- [ ] Test trail laying and retrieval (`lay_trail`, `get_trails`, `get_hot_spots`)

### Priority 4: Dashboard API (`dashboard-app/backend/`)
- [ ] Test WebSocket connection and real-time updates (`/ws`)
- [ ] Test analytics router endpoints (`/api/analytics/*`)
- [ ] Test heuristics router endpoints (`/api/heuristics/*`)
- [ ] Test runs and knowledge routers (`/api/runs/*`, `/api/knowledge/*`)
- [ ] Test query and session routers (`/api/queries/*`, `/api/sessions/*`)
- [ ] Test admin and workflow routers (`/api/admin/*`, `/api/workflows/*`)
- [ ] Test database utilities

## Technical Notes

- Use `pytest` with `pytest-asyncio` for async tests
- Use in-memory SQLite for database tests (no external dependencies)
- Create proper fixtures in `conftest.py`
- Aim for tests that actually run in CI

## Acceptance Criteria

- [ ] Achieve at least 80% test coverage for `query/query.py` (Priority 1)
- [ ] Achieve at least 75% test coverage for `hooks/learning-loop/` (Priority 2)
- [ ] Achieve at least 70% test coverage for `conductor/` (Priority 3)
- [ ] Achieve at least 70% test coverage for `dashboard-app/backend/` (Priority 4)
- [ ] All new tests run successfully in GitHub Actions CI
- [ ] New tests are documented with clear docstrings and cover important edge cases
- [ ] Legacy broken tests are deleted as new tests replace them

## To Start This Task

```bash
# Ensure you are in the root of the clc repository before running these commands.
# Create a new branch
git checkout main && git pull
git checkout -b feat/core-test-suite

# Start with query tests
# Reference: tests/test_enhancements.py (has some useful patterns)
```
