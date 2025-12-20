# Heuristics: hooks

Generated from failures, successes, and observations in the **hooks** domain.

---

## H-0: Claude Code PostToolUse hooks receive tool output in 'tool_response' field, not 'tool_output' - always check official docs for field names

**Confidence**: 0.7
**Source**: observation
**Created**: 2025-12-17

The CLC hooks were looking for hook_input.get('tool_output') but Claude Code sends 'tool_response'. This caused 100% of workflow outcomes to be 'unknown' because the output was never captured. Fix: lookup chain should be tool_response -> tool_output -> output for backwards compatibility.

---

## H-14: TaskOutput tool_response uses nested structure: tool_response.task.output, not tool_response.content like Task tool. Always verify actual hook input structure with debug logging before assuming field names.

**Confidence**: 0.7
**Source**: observation
**Created**: 2025-12-17



---

