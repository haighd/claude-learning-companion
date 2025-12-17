# Task: Write Test Suite for CLC Core Components

**Status:** Pending
**Created:** 2025-12-16
**Priority:** High

## Summary

The CLC project has 23 test files in `tests/` but many have issues (missing imports, missing fixtures, outdated dependencies). Rather than fix the broken tests, we should write a new focused test suite for core components.

**Handling Legacy Tests:** Delete the old, broken test files as they are replaced with new tests. The old tests have unresolvable dependency issues and keeping them around creates confusion about which tests are canonical. Clean deletion is preferred over archiving since the git history preserves the old tests if ever needed.

**Legacy Test Mapping:** Each priority section below includes a list of legacy test files it replaces. Delete these files as the new tests are completed and verified.

**Legacy Test Inventory (23 files):**
- **To replace** (10 files): Listed in each priority section below
- **Mapped to priorities** (6 files):
  - Priority 1 (Query): `test_sqlite_edge_cases.py`, `test_meta_observer.py` - database edge cases and observability
  - Priority 3 (Conductor): `test_crash_recovery.py`, `test_dependency_graph.py` - workflow resilience
  - Priority 5 (Non-Functional): `test_stress.py`, `test_lifecycle_adversarial.py` - performance and security
- **To evaluate** (5 files): `test_baseline_refresh.py`, `test_destructive_edge_cases.py`, `test_domain_elasticity.py`, `test_integration_multiagent.py`, `test_temporal_smoothing.py` - assess during implementation whether these can be salvaged or should be replaced
- **Pytest infrastructure** (2 files): `conftest.py` (will be replaced with new fixtures), `__init__.py` (keep as package marker)

## Background

During PR #1 (rename emergent-learning to clc), we identified that:
- `test_claim_chains*.py` - ImportError: cannot import 'BlockedError' from blackboard
- `test_conductor_workflow.py` - FileNotFoundError: missing `init_db.sql`
- Multiple other tests have similar dependency/fixture issues

## Proposed Approach

Write new, focused tests starting with the most critical components:

### Priority 1: Query System (`query/query.py`)
*Replaces: `tests/test_edge_cases.py`, `tests/test_edge_cases_v2.py`, `tests/test_sqlite_edge_cases.py`, `tests/test_meta_observer.py`*

- [ ] Test `build_context()` method (and relevance scoring)
- [ ] Test `query_by_domain()`
- [ ] Test `query_by_tags()`
- [ ] Test `query_recent()`
- [ ] Test `get_golden_rules()`
- [ ] Test `get_active_experiments()`
- [ ] Test `get_pending_ceo_reviews()`
- [ ] Test `get_violations()`
- [ ] Test `get_violation_summary()`
- [ ] Test `get_decisions()`
- [ ] Test `get_invariants()`
- [ ] Test `get_assumptions()`
- [ ] Test `get_spike_reports()`
- [ ] Test `find_similar_failures()`
- [ ] Test `get_challenged_assumptions()`
- [ ] Test `get_statistics()`
- [ ] Test `validate_database()`
- [ ] Test CLI functionality in `main()`

### Priority 2: Learning Loop Hooks (`hooks/learning-loop/`)
*Replaces: `tests/test_event_log.py`, `tests/test_event_log_dispatch.py`*

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
  - [ ] Test explicit learning extraction (`extract_and_record_learnings`)

### Priority 3: Conductor (`conductor/`)
*Replaces: `tests/test_conductor_workflow.py`, `tests/test_claim_chains.py`, `tests/test_claim_chains_comprehensive.py`, `tests/test_crash_recovery.py`, `tests/test_dependency_graph.py`*

- [ ] Test workflow management (create, get, list)
- [ ] Test node execution recording (start, completion, failure)
- [ ] Test run status updates and context management
- [ ] Test `safe_eval_condition` helper with various inputs
- [ ] Test different workflow patterns:
  - [ ] Linear (A -> B -> C)
  - [ ] Branching (A -> B, A -> C)
  - [ ] Conditional branching
  - [ ] Converging (A -> C, B -> C)
- [ ] Test trail laying (`lay_trail`)
- [ ] Test trail retrieval (`get_trails`)
- [ ] Test hot spot retrieval (`get_hot_spots`)

### Priority 4: Dashboard API (`dashboard-app/backend/`)
*Replaces: `tests/test_fraud_detection.py`, `tests/test_fraud_outcomes.py`, `tests/test_blackboard_v2.py`*

**Note:** This priority is large. Consider implementing one router at a time for incremental progress.

#### API Endpoints & Utilities
- [ ] Test WebSocket connection and real-time updates (`/ws`) - use FastAPI's `TestClient` which supports WebSocket testing
- [ ] Test analytics router endpoints (`/api/analytics/*`):
  - [ ] Test `GET /stats`
  - [ ] Test `GET /timeline`
  - [ ] Test `GET /learning-velocity`
  - [ ] Test `GET /events`
  - [ ] Test `GET /domains`
  - [ ] Test `GET /anomalies`
- [ ] Test heuristics router endpoints (`/api/heuristics/*`):
  - [ ] Test `GET /heuristics` (list all)
  - [ ] Test `GET /heuristics/{id}` (get single)
  - [ ] Test `GET /heuristic-graph` (relationship graph)
  - [ ] Test `POST /heuristics/{id}/promote`
  - [ ] Test `POST /heuristics/{id}/demote`
  - [ ] Test `PUT /heuristics/{id}` (update)
  - [ ] Test `DELETE /heuristics/{id}`
- [ ] Test runs router endpoints (`/api/runs/*`):
  - [ ] Test `GET /runs` (list runs)
  - [ ] Test `GET /runs/{id}` (get single run with executions)
  - [ ] Test `GET /runs/{id}/diff` (get run diff)
  - [ ] Test `POST /runs/{id}/retry` (retry run)
  - [ ] Test `GET /hotspots` (hot spots from runs)
  - [ ] Test `GET /hotspots/treemap` (treemap visualization)
- [ ] Test knowledge router endpoints (`/api/knowledge/*`):
  - [ ] Test `GET /learnings` (list learnings)
  - [ ] Test decisions sub-router:
    - [ ] Test `GET /decisions` (list)
    - [ ] Test `GET /decisions/{id}` (get single)
    - [ ] Test `POST /decisions` (create)
    - [ ] Test `PUT /decisions/{id}` (update)
    - [ ] Test `DELETE /decisions/{id}`
    - [ ] Test `POST /decisions/{id}/supersede`
  - [ ] Test assumptions sub-router:
    - [ ] Test `GET /assumptions` (list)
    - [ ] Test `GET /assumptions/{id}` (get single)
    - [ ] Test `POST /assumptions` (create)
    - [ ] Test `PUT /assumptions/{id}` (update)
    - [ ] Test `POST /assumptions/{id}/verify`
    - [ ] Test `POST /assumptions/{id}/challenge`
    - [ ] Test `DELETE /assumptions/{id}`
  - [ ] Test invariants sub-router:
    - [ ] Test `GET /invariants` (list)
    - [ ] Test `GET /invariants/{id}` (get single)
    - [ ] Test `POST /invariants` (create)
    - [ ] Test `PUT /invariants/{id}` (update)
    - [ ] Test `POST /invariants/{id}/validate`
    - [ ] Test `POST /invariants/{id}/violate`
    - [ ] Test `DELETE /invariants/{id}`
  - [ ] Test spike-reports sub-router:
    - [ ] Test `GET /spike-reports` (list)
    - [ ] Test `GET /spike-reports/search`
    - [ ] Test `GET /spike-reports/{id}` (get single)
    - [ ] Test `POST /spike-reports` (create)
    - [ ] Test `PUT /spike-reports/{id}` (update)
    - [ ] Test `POST /spike-reports/{id}/rate`
    - [ ] Test `DELETE /spike-reports/{id}`
- [ ] Test query router endpoints (`/api/queries/*`):
  - [ ] Test `GET /queries` (list query history)
  - [ ] Test `POST /query` (execute query)
- [ ] Test session router endpoints (`/api/sessions/*`):
  - [ ] Test `GET /sessions/stats` (session statistics)
  - [ ] Test `GET /sessions` (list sessions)
  - [ ] Test `GET /sessions/{id}` (get session details)
  - [ ] Test `GET /sessions/{id}/summary` (get session summary)
  - [ ] Test `GET /projects` (list projects)
  - [ ] Test `POST /sessions/{id}/summarize` (generate summary)
  - [ ] Test `POST /sessions/summarize-batch` (batch summarize)
- [ ] Test admin router endpoints (`/api/admin/*`):
  - [ ] Test `GET /ceo-inbox` (list CEO inbox items)
  - [ ] Test `GET /ceo-inbox/{filename}` (get single item)
  - [ ] Test `GET /export/{export_type}` (export data)
  - [ ] Test `POST /open-in-editor` (open file in editor)
- [ ] Test workflow router endpoints (`/api/workflows/*`):
  - [ ] Test `GET /workflows` (list workflows)
  - [ ] Test `POST /workflows` (create workflow)
- [ ] Test fraud router endpoints (`/api/fraud/*`):
  - [ ] Test `GET /fraud-reports` (list reports)
  - [ ] Test `GET /fraud-reports/{id}` (get single report)
  - [ ] Test `POST /fraud-reports/{id}/review` (review report)
- [ ] Test database utilities (`dashboard-app/backend/utils.py`):
  - [ ] Test `get_db()` database connection helper
  - [ ] Test `dict_from_row()` row conversion
  - [ ] Test `ConnectionManager` WebSocket management

### Priority 5: Non-Functional Testing
*Replaces: `tests/test_stress.py`, `tests/test_lifecycle_adversarial.py`*

- [ ] Implement stress tests to measure performance under heavy load
- [ ] Implement adversarial tests to check for security vulnerabilities and robustness against unexpected inputs
- [ ] Evaluate and potentially integrate chaos testing principles
- [ ] Test concurrent access patterns and race conditions
- [ ] Test memory usage under sustained load

## Technical Notes

- Use `pytest` with `pytest-asyncio` for async tests
- Use in-memory SQLite for database tests (no external dependencies)
- For database permission tests (os.chmod, icacls), use either:
  - Temporary file-based database to verify actual permission setting
  - Mock filesystem calls to verify correct arguments are passed
- Create proper fixtures in `conftest.py` and organize tests by mirroring the application's directory structure (e.g., `tests/query/test_query.py`)
- Build shared, reusable fixtures for common data setups (e.g., `standard_user_session`, `complex_workflow_run`, `golden_heuristics_set`) to reduce boilerplate
- Create a strategy for managing test data (e.g., using a library like `factory-boy` to create model factories) to cover diverse scenarios and edge cases
- Mock external services (e.g., LLM APIs) to ensure tests are fast, deterministic, and don't rely on network access
- Use `pytest.mark.parametrize` to reduce code duplication when testing similar functions or API endpoints
- Consider using snapshot testing (e.g., `pytest-snapshot`) for asserting complex API responses, especially for Dashboard API endpoints
- Use pytest markers (e.g., `@pytest.mark.unit`, `@pytest.mark.integration`) to categorize tests and enable selective test runs
- Consider `pytest-xdist` for parallel test execution to achieve the < 5 minute CI target
- Use `pytest-benchmark` to establish and track performance benchmarks for critical code paths

## Acceptance Criteria

- [ ] Achieve at least 80% test coverage for `query/query.py` (Priority 1)
- [ ] Establish baseline performance benchmarks for critical queries in `query/query.py` using `pytest-benchmark` to track performance over time
- [ ] Achieve at least 75% test coverage for `hooks/learning-loop/` (Priority 2)
- [ ] Achieve at least 70% test coverage for `conductor/` (Priority 3)
- [ ] Achieve at least 70% test coverage for `dashboard-app/backend/` (Priority 4)
- [ ] All new tests run successfully in GitHub Actions CI
- [ ] New tests are documented with clear docstrings and cover important edge cases
- [ ] Create a `tests/README.md` documenting test organization, how to run tests, and guidelines for contributors
- [ ] Test suite completes within reasonable time (target: under 5 minutes) to maintain fast CI feedback
- [ ] No flaky tests are merged into the main branch
- [ ] Legacy broken tests are deleted as new tests replace them

## To Start This Task

```bash
# Ensure you are in the root of the clc repository before running these commands.
# Create a new branch
git checkout main && git pull
git checkout -b feat/core-test-suite

# Start with query tests
# Review: tests/test_edge_cases.py, tests/test_edge_cases_v2.py (legacy tests being replaced - may have reusable test scenarios)
```
