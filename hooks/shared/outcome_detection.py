#!/usr/bin/env python3
"""
Shared outcome detection logic for CLC hooks.

This module provides pre-compiled regex patterns and the determine_outcome function
used by both post_tool_learning.py and post_hook.py to avoid code duplication.
"""

import re
from typing import Tuple

# =============================================================================
# Pre-compiled regex patterns for outcome detection (module-level for performance)
# =============================================================================

# Success patterns - explicit completion phrases
SUCCESS_PATTERNS = [
    (re.compile(r'(?i)\bsuccessfully\s+\w+'), "Successfully completed action"),
    (re.compile(r'(?i)\btask\s+complete'), "Task completed"),
    (re.compile(r'(?i)\b(work|task) is (done|finished|complete)'), "Work is done"),
    (re.compile(r'(?i)\ball tests pass'), "Tests passed"),
    (re.compile(r'\[success\]'), "Success marker found"),
    (re.compile(r'(?i)## FINDINGS'), "Findings reported"),
    (re.compile(r'(?i)\bcompleted\s+successfully'), "Completed successfully"),
    (re.compile(r'(?i)## Investigation Report'), "Investigation report provided"),
    (re.compile(r'(?i)## Analysis'), "Analysis provided"),
    (re.compile(r'(?i)## Summary'), "Summary provided"),
    (re.compile(r"(?i)here's (the|my|a) (complete|full|detailed)"), "Detailed response provided"),
    # Action verbs indicating work was done (past tense)
    (re.compile(r'(?i)\b(created|generated|built|made)\b\s+\w+'), "Created something"),
    (re.compile(r'(?i)\b(fixed|resolved|corrected|repaired)\b\s+\w+'), "Fixed something"),
    (re.compile(r'(?i)\b(updated|modified|changed|revised)\b\s+\w+'), "Updated something"),
    (re.compile(r'(?i)\b(implemented|added|introduced)\b\s+\w+'), "Implemented something"),
    (re.compile(r'(?i)\b(analyzed|examined|reviewed|investigated)\b\s+\w+'), "Analyzed something"),
    (re.compile(r'(?i)\b(identified|found|discovered|located)\b\s+\w+'), "Identified something"),
    (re.compile(r'(?i)\b(removed|deleted|cleaned)\b\s+\w+'), "Removed something"),
    (re.compile(r'(?i)\b(refactored|reorganized|restructured)\b\s+\w+'), "Refactored something"),
    (re.compile(r'(?i)\b(tested|validated|verified)\b\s+\w+'), "Tested something"),
    (re.compile(r'(?i)\b(deployed|released|published)\b\s+\w+'), "Deployed something"),
    # Reporting patterns - agent is presenting findings/results
    (re.compile(r'(?i)\bhere (is|are) (the |my )?(\w+\s+)?(findings|results|analysis|summary)'), "Presented findings"),
    (re.compile(r"(?i)\bi (have |'ve )?(completed|finished|done)"), "Agent reported completion"),
    (re.compile(r'(?i)\bthe (task|work|analysis|fix|implementation) is (complete|done|finished)'), "Work is complete"),
    (re.compile(r'(?i)^\s*(finished|completed|done)\s+\w+'), "Started with completion verb"),
    (re.compile(r'(?i)\b(summary|conclusion):'), "Provided summary"),
    (re.compile(r'(?i)\brecommend(ations|s)?:'), "Provided recommendations"),
    (re.compile(r'(?i)\bnow I have a (clear|complete|comprehensive|full) picture'), "Comprehensive analysis done"),
    (re.compile(r'(?i)\blet me (provide|present|summarize|compile)'), "Presenting results"),
]

# Failure patterns
FAILURE_PATTERNS = [
    (re.compile(r'(?i)\berror\b[:\s]'), "Error detected"),
    (re.compile(r'(?i)\bexception\b[:\s]'), "Exception raised"),
    (re.compile(r'(?i)\bfailed\b[:\s]'), "Operation failed"),
    (re.compile(r'(?i)\bcould not\b'), "Could not complete"),
    (re.compile(r'(?i)\bunable to\b'), "Unable to complete"),
    (re.compile(r'\[BLOCKER\]'), "Blocker encountered"),
    (re.compile(r'(?i)\btraceback\b'), "Exception traceback"),
    (re.compile(r'(?i)\bpermission denied\b'), "Permission denied"),
    (re.compile(r'(?i)\btimed?\s+out\b'), "Timeout occurred"),
    (re.compile(r'(?i)^.*\bnot found\s*$', re.MULTILINE), "Resource not found"),
]

# False positive patterns for code analysis scenarios
FALSE_POSITIVE_PATTERNS = [
    # Discussion patterns - talking about errors, not actual errors
    re.compile(r'(?i)was not found to be'),
    re.compile(r'(?i)\berror handling\b'),
    re.compile(r'(?i)\bno errors?\b'),
    re.compile(r'(?i)\bwithout errors?\b'),
    re.compile(r'(?i)\berror.?free\b'),
    re.compile(r'(?i)\b(fixed|resolved|corrected|repaired)\b.*\b(error|failure|bug|issue|exception)'),
    re.compile(r'(?i)\b(error|failure|bug|issue|exception)\b.*(fixed|resolved|corrected|repaired)'),
    re.compile(r'(?i)\binvestigated.*\b(failed|error|failure)'),
    re.compile(r'(?i)\banalyzed.*\b(error|failure|failed)'),
    re.compile(r'(?i)\bhandl(e|es|ed|ing).*\b(error|failure|exception)'),
    re.compile(r'(?i)\b(error|failure|exception)\s+handl'),
    re.compile(r'(?i)resolved.*\b(error|failure|exception)'),
    # Python exception types being discussed
    re.compile(r'(?i)TypeError[:\s]'),
    re.compile(r'(?i)ValueError[:\s]'),
    re.compile(r'(?i)KeyError[:\s]'),
    re.compile(r'(?i)AttributeError[:\s]'),
    re.compile(r'(?i)ImportError[:\s]'),
    re.compile(r'(?i)RuntimeError[:\s]'),
    re.compile(r'(?i)SyntaxError[:\s]'),
    # Code references and literals
    re.compile(r'(?i)`[^`]*error[^`]*`'),
    re.compile(r'(?i)```[^`]{0,500}?error'),
    re.compile(r'(?i)#\s*.*error'),
    re.compile(r'(?i)"[^"]*error[^"]*"'),
    re.compile(r"(?i)'[^']*error[^']*'"),
    # Code identifiers and patterns
    re.compile(r'(?i)\.error\s*\('),
    re.compile(r'(?i)error_'),
    re.compile(r'(?i)_error\b'),
    re.compile(r'(?i)\berror[A-Z]'),
    re.compile(r'(?i)on_?error'),
    re.compile(r'(?i)if\s+.*error'),
    re.compile(r'(?i)catch.*error'),
    re.compile(r'(?i)except.*Error'),
    re.compile(r'(?i)raise.*Error'),
    re.compile(r'(?i)Error\s*='),
    re.compile(r'(?i):\s*Error\b'),
    re.compile(r'(?i)->.*Error'),
]

# Structure detection pattern
STRUCTURE_PATTERN = re.compile(r'(?m)^#{1,3}\s+\w+')


def determine_outcome(tool_output: dict) -> Tuple[str, str]:
    """
    Determine if the task succeeded or failed.

    Returns: (outcome, reason)
    - outcome: 'success', 'failure', 'unknown'
    - reason: description of why

    IMPORTANT: This function prioritizes SUCCESS signals over failure patterns.
    This prevents false positives when subagents analyze code containing error
    handling, error messages, or discussions of errors/failures.
    """
    if not tool_output:
        return "unknown", "No output to analyze"

    # Get content - handle different tool response structures
    content = ""
    if isinstance(tool_output, dict):
        # TaskOutput structure: tool_response.task.output or task.result
        if "task" in tool_output and isinstance(tool_output["task"], dict):
            task_data = tool_output["task"]
            content = task_data.get("output", "") or task_data.get("result", "") or ""
        # Task structure: tool_response.content (array of {type, text})
        elif "content" in tool_output:
            content = tool_output.get("content", "") or ""
            if isinstance(content, list):
                content = "\n".join(
                    item.get("text", "") for item in content
                    if isinstance(item, dict)
                )
        # Fallback: try common field names
        else:
            content = (tool_output.get("output", "") or
                      tool_output.get("result", "") or
                      tool_output.get("text", "") or "")
    elif isinstance(tool_output, str):
        content = tool_output

    if not content:
        return "unknown", "Empty output"

    # ==========================================================================
    # PHASE 1: CHECK SUCCESS SIGNALS FIRST (prevents false positives)
    # ==========================================================================

    for compiled_pattern, reason in SUCCESS_PATTERNS:
        if compiled_pattern.search(content):
            return "success", reason

    # Substantial output heuristic - long outputs with structure are likely successful
    if len(content) > 500:
        if STRUCTURE_PATTERN.search(content):
            return "success", "Structured report with headers"

    # ==========================================================================
    # PHASE 2: CHECK FAILURE SIGNALS (only if no success signals found)
    # ==========================================================================

    for compiled_pattern, reason in FAILURE_PATTERNS:
        match = compiled_pattern.search(content)
        if match:
            # Use 50 characters before and after the match (100 characters total context)
            match_start = max(0, match.start() - 50)
            match_end = min(len(content), match.end() + 50)
            context = content[match_start:match_end]

            is_false_positive = any(fp.search(context) for fp in FALSE_POSITIVE_PATTERNS)
            if not is_false_positive:
                return "failure", reason

    # ==========================================================================
    # PHASE 3: FALLBACK HEURISTICS
    # ==========================================================================

    # If we got substantial output without errors, probably success
    if len(content) > 50:
        return "success", "Substantial output without errors"

    return "unknown", "Could not determine outcome"
