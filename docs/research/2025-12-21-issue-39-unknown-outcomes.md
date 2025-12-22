# Research: Workflow Outcome Detection - Issue #39

**Date:** 2025-12-21
**Issue:** [#39 - Workflow outcomes showing 'unknown' status](https://github.com/haighd/claude-learning-companion/issues/39)
**Status:** Research Complete

## Executive Summary

Investigation reveals **78% of workflow outcomes** are classified as "unknown" in the last 7 days (1492 unknown vs 414 success). The root causes are:

1. **Bash output structure mismatch** - Looking for "output" key when Claude returns "stdout"
2. **Insufficient success patterns** - Common successful outputs don't match any pattern
3. **No exit code field** - Claude Bash responses include no direct exit code field

## Evidence Analysis

### Current Outcome Distribution (Last 7 Days)

| Outcome | Count | Percentage |
|---------|-------|------------|
| unknown | 1,492 | 73% |
| success | 414 | 20% |
| no_outcome | 138 | 7% |
| failure | 0 | 0% |

**Target:** < 10% unknown outcomes (per issue acceptance criteria)

### Sample "Unknown" Outputs

```json
// Type 1: Empty stdout (successful silent commands)
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false}

// Type 2: Simple acknowledgment strings
{"stdout": "Labels may not exist", "stderr": "", "interrupted": false}

// Type 3: JSON data responses
{"stdout": "{\"comments\":[]}", "stderr": "", "interrupted": false}

// Type 4: Fallback messages
{"stdout": "No codex review script found", "stderr": "", "interrupted": false}
```

### Code Analysis

**File:** `hooks/learning-loop/post_tool_learning.py`

#### Issue 1: Field Access Order (Line 245)

```python
# Current code:
output = tool_output.get("output", "") or tool_output.get("stdout", "") or str(tool_output)
```

Claude's Bash tool response structure is:
```json
{
  "stdout": "...",
  "stderr": "...",
  "interrupted": false,
  "isImage": false
}
```

The code checks "output" first (doesn't exist), gets empty string, then checks "stdout". This works BUT falls back to `str(tool_output)` on empty stdout, which creates unparseable JSON strings.

#### Issue 2: Missing Success Patterns (Lines 287-298)

Current success patterns:
- `successfully`
- `completed`
- `done.` (at end)
- `ok ` (at start)
- `passed`
- `\d+ passing`

**Missing patterns for common successful outputs:**
- Empty stdout with no stderr (successful silent command)
- JSON responses (data returned = success)
- Fallback/default messages that aren't errors
- Commands that produce output without success keywords

#### Issue 3: No Exit Code Detection

Claude's Bash responses don't include an exit code field directly. The code searches for exit code patterns in the OUTPUT TEXT:

```python
exit_code_match = re.search(r'(?i)exit(?:ed)?(?:\s+with|\s+status|[:\s]+code)?[:\s]+(\d+)', output)
```

This only works if the command's output itself contains "exit code X" text, which is rare.

### Heuristic from Previous Learning

From CLC heuristics (hooks domain):
> "TaskOutput tool_response uses nested structure: tool_response.task.output, not tool_response.content like Task tool."

This confirms the response structure varies by tool type and must be handled differently.

## Root Cause Summary

| Issue | Impact | Severity |
|-------|--------|----------|
| Empty stdout = unknown | Silent successful commands marked unknown | High |
| No JSON response recognition | API-like outputs marked unknown | Medium |
| Fallback messages not recognized | Graceful fallbacks marked unknown | Medium |
| Exit code not in response | Can't detect success/failure from exit code | High |

## Recommended Solutions

### Solution 1: Infer Success from Absence of Failure

If a Bash command produces:
- No stderr content
- No error patterns in stdout
- Empty or any stdout

**Then classify as "success"** (not "unknown"), with reason "Command completed without errors".

Rationale: If there's no error, the command succeeded. Being conservative ("unknown") when there's no error is overly cautious.

### Solution 2: Add JSON Response Detection

If stdout contains valid JSON and no error indicators:
- Classify as "success" with reason "Returned JSON data"

### Solution 3: Add Common Output Patterns

Add success patterns for:
- `"found"` (resource located)
- `"exists"` / `"already exists"` (idempotent success)
- `"created"` / `"updated"` / `"deleted"`
- `"[0-9]+ (files?|items?|rows?)` (count results)
- `true` / `false` (boolean responses)

### Solution 4: Treat Empty as Success

Empty stdout + empty stderr = success (silent command completed)

Currently this returns "unknown" with "No output and no clear outcome indicators".

## Implementation Priority

1. **High Priority:** Empty stdout+stderr → success
2. **High Priority:** No stderr + no error patterns → success
3. **Medium Priority:** JSON stdout → success
4. **Medium Priority:** Add common output patterns

## Files to Modify

| File | Changes |
|------|---------|
| `hooks/learning-loop/post_tool_learning.py` | Update `determine_bash_outcome()` function (lines 230-305) |

## Testing Strategy

1. Create test cases for each scenario
2. Run on historical data to validate improvement
3. Monitor outcome distribution for 24 hours post-deployment
4. Target: < 10% unknown outcomes

## References

- Issue #39: https://github.com/haighd/claude-learning-companion/issues/39
- Relevant heuristic: "TaskOutput tool_response uses nested structure"
- Code location: `hooks/learning-loop/post_tool_learning.py:230-305`
