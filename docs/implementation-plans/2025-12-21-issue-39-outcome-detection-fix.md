# Implementation Plan: Fix Workflow Outcome Detection

**Issue:** [#39 - Workflow outcomes showing 'unknown' status](https://github.com/haighd/claude-learning-companion/issues/39)
**Research:** [docs/research/2025-12-21-issue-39-unknown-outcomes.md](../research/2025-12-21-issue-39-unknown-outcomes.md)
**Target:** Reduce "unknown" outcomes from 78% to < 10%

---

## Phase 1: Fix Bash Outcome Detection Logic

**File:** `hooks/learning-loop/post_tool_learning.py`
**Function:** `determine_bash_outcome()` (lines 230-305)

### Step 1.1: Improve Output Extraction

**Current (line 245):**
```python
output = tool_output.get("output", "") or tool_output.get("stdout", "") or str(tool_output)
```

**New:**
```python
# Extract output from Claude's Bash response structure
stdout = ""
stderr = ""
if isinstance(tool_output, dict):
    stdout = tool_output.get("stdout", "") or ""
    stderr = tool_output.get("stderr", "") or ""
elif isinstance(tool_output, str):
    stdout = tool_output

output = stdout  # Primary output for pattern matching
```

### Step 1.2: Add Success-by-Absence Logic

**Insert after error pattern checks (around line 283):**

```python
# If stderr is empty and no error patterns matched, infer success
# Rationale: Commands that complete without errors succeeded
if not stderr.strip():
    # Check if stdout has any concerning patterns we might have missed
    concerning_patterns = [
        r'(?i)\bwarning\b',
        r'(?i)\bdeprecated\b',
    ]
    has_concerns = any(re.search(p, stdout) for p in concerning_patterns)

    if not has_concerns:
        if stdout.strip():
            return "success", "Command completed with output"
        else:
            return "success", "Command completed silently"
```

### Step 1.3: Add JSON Response Detection

**Insert before the final "unknown" returns:**

```python
# Detect JSON responses - structured data usually means success
if stdout.strip():
    try:
        # Check if it's valid JSON
        if (stdout.strip().startswith('{') or stdout.strip().startswith('[')):
            import json
            json.loads(stdout)
            return "success", "Returned JSON data"
    except (json.JSONDecodeError, ValueError):
        pass  # Not JSON, continue checking
```

### Step 1.4: Add Common Success Patterns

**Extend `bash_success_patterns` list (around line 287):**

```python
bash_success_patterns = [
    # Existing patterns
    (r'(?i)successfully', "Operation successful"),
    (r'(?i)completed', "Operation completed"),
    (r'(?is)done\.?\s*\Z', "Done"),
    (r'(?i)\Aok\s', "OK status"),
    (r'(?i)\bpassed\b', "Tests passed"),
    (r'(?i)\d+ passing', "Tests passing"),

    # NEW patterns
    (r'(?i)\bfound\b', "Resource found"),
    (r'(?i)\bexists\b', "Resource exists"),
    (r'(?i)\bcreated\b', "Resource created"),
    (r'(?i)\bupdated\b', "Resource updated"),
    (r'(?i)\bdeleted\b', "Resource deleted"),
    (r'(?i)\binstalled\b', "Package installed"),
    (r'(?i)\bstarted\b', "Process started"),
    (r'(?i)\bstopped\b', "Process stopped"),
    (r'(?i)\brestarted\b', "Process restarted"),
    (r'(?i)\d+\s+(files?|items?|rows?|records?)', "Count result"),
    (r'(?i)\btrue\b', "Boolean true"),
    (r'(?i)\bfalse\b', "Boolean false"),
    (r'(?i)already\s+\w+', "Idempotent result"),
]
```

---

## Phase 2: Update Determine Outcome Order

Refactor `determine_bash_outcome()` to follow this logic order:

1. Check for explicit failure patterns (exit codes, error messages)
2. Check for explicit success patterns
3. Check for JSON responses
4. Check for warnings (return success with caveat)
5. **NEW:** If stderr empty and no errors → success
6. **NEW:** If stdout empty and stderr empty → success (silent command)
7. Only return "unknown" if stderr has content we don't understand

---

## Phase 3: Testing & Validation

### 3.1: Unit Tests

Create `tests/test_outcome_detection.py`:

```python
def test_empty_stdout_stderr_is_success():
    """Empty output with no errors = success"""
    result = determine_bash_outcome({}, {"stdout": "", "stderr": ""})
    assert result[0] == "success"

def test_json_response_is_success():
    """JSON data response = success"""
    result = determine_bash_outcome({}, {"stdout": '{"comments":[]}', "stderr": ""})
    assert result[0] == "success"

def test_fallback_message_is_success():
    """Fallback messages without errors = success"""
    result = determine_bash_outcome({}, {"stdout": "No codex review script found", "stderr": ""})
    assert result[0] == "success"

def test_error_in_stderr_is_failure():
    """Error in stderr = failure"""
    result = determine_bash_outcome({}, {"stdout": "", "stderr": "Error: command not found"})
    assert result[0] == "failure"
```

### 3.2: Historical Validation

Run against last 7 days of workflow data to measure improvement:

```python
# Query outcomes before and after applying new logic
# Target: unknown < 10% of total
```

### 3.3: Monitoring

After deployment:
1. Check outcome distribution after 24 hours
2. Compare to baseline (78% unknown)
3. Verify no false positives (failures marked as success)

---

## Acceptance Criteria Mapping

| Criteria | Implementation |
|----------|----------------|
| Add debug logging | Not needed - root cause identified |
| Update outcome detection logic | Phase 1 & 2 |
| Reduce "unknown" to < 10% | Phases 1-3 with validation |
| Document correct field structure | Research doc complete |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| False positive success | Keep explicit failure patterns first; only infer success when no errors |
| Missing new error patterns | Monitor for unexpected "success" on actual failures |
| Performance impact | JSON parsing only attempted on JSON-like strings |

---

## Estimated Changes

- Lines added: ~30
- Lines modified: ~10
- Files changed: 1 (`post_tool_learning.py`)
- Tests added: ~10

---

## Dependencies

None - self-contained fix to outcome detection logic.
