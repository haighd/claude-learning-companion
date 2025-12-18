#!/usr/bin/env python3
"""
Post-Tool Learning Hook: Validate heuristics and close the learning loop.

This hook completes the learning loop by:
1. Checking task outcomes (success/failure)
2. Validating heuristics that were consulted
3. Auto-recording failures when they happen
4. Incrementing validation counts on successful tasks
5. Flagging heuristics that may have led to failures
6. Laying trails for hotspot tracking
7. Advisory verification of risky patterns (warns but never blocks)

The key insight: If we showed heuristics before a task and the task succeeded,
those heuristics were useful. If the task failed, maybe they weren't.
"""

import json
import os
import re
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Import trail helper
try:
    from trail_helper import extract_file_paths, lay_trails
except ImportError:
    def extract_file_paths(content): return []
    def lay_trails(*args, **kwargs): pass

# Paths - using Path.home() for portability
CLC_PATH = Path.home() / ".claude" / "clc"
DB_PATH = CLC_PATH / "memory" / "index.db"
STATE_FILE = Path.home() / ".claude" / "hooks" / "learning-loop" / "session-state.json"
PENDING_TASKS_FILE = Path.home() / ".claude" / "hooks" / "learning-loop" / "pending-tasks.json"

# Import security patterns
try:
    from security_patterns import RISKY_PATTERNS
except ImportError:
    # Fallback to basic patterns if import fails
    RISKY_PATTERNS = {
        'code': [
            (r'eval\s*\(', 'eval() detected - potential code injection risk'),
            (r'exec\s*\(', 'exec() detected - potential code injection risk'),
        ],
        'file_operations': []
    }


class AdvisoryVerifier:
    """
    Post-action verification that warns but NEVER blocks.
    Philosophy: Advisory only, human decides.
    """

    def __init__(self):
        self.warnings = []

    def analyze_edit(self, file_path: str, old_content: str,
                     new_content: str) -> Dict:
        """Analyze a file edit for risky patterns."""
        warnings = []

        # Only check what was ADDED (not existing code)
        added_lines = self._get_added_lines(old_content, new_content)

        for line in added_lines:
            for category, patterns in RISKY_PATTERNS.items():
                for pattern, message in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        warnings.append({
                            'category': category,
                            'message': message,
                            'line_preview': line[:80] + '...' if len(line) > 80 else line
                        })

        return {
            'has_warnings': len(warnings) > 0,
            'warnings': warnings,
            'recommendation': self._get_recommendation(warnings)
        }

    def _is_comment_line(self, line: str) -> bool:
        """Check if a line is entirely a comment (not code with comment).

        Returns True for:
        - Python comments: starts with #
        - JS/C/Go single-line comments: starts with //
        - C-style multi-line comment start: starts with /*
        - Multi-line comment bodies: starts with *
        - Docstrings: starts with triple quotes

        Returns False for:
        - Mixed lines like: x = eval(y)  # comment
        - Code before comment: foo()  // comment
        """
        stripped = line.strip()
        if not stripped:
            return False

        # Check for pure comment lines (line starts with comment marker)
        triple_quote = chr(34) * 3
        single_triple = chr(39) * 3
        comment_markers = ['#', '//', '/*', '*', triple_quote, single_triple]
        return any(stripped.startswith(marker) for marker in comment_markers)

    def _get_added_lines(self, old: str, new: str) -> List[str]:
        """Get lines that were added (simple diff), excluding pure comment lines."""
        old_lines = set(old.split('\n')) if old else set()
        new_lines = new.split('\n') if new else []
        added_lines = [line for line in new_lines if line not in old_lines]

        # Filter out pure comment lines to avoid false positives
        return [line for line in added_lines if not self._is_comment_line(line)]

    def _get_recommendation(self, warnings: List[Dict]) -> str:
        if not warnings:
            return "No concerns detected."
        if len(warnings) >= 3:
            return "[!] Multiple concerns - consider CEO escalation"
        return "[!] Review flagged items before proceeding"


def get_hook_input() -> dict:
    """Read hook input from stdin."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, IOError, ValueError):
        return {}


def output_result(result: dict):
    """Output hook result to stdout."""
    print(json.dumps(result))


def load_session_state() -> dict:
    """Load current session state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError, ValueError):
            pass
    return {
        "session_start": datetime.now().isoformat(),
        "heuristics_consulted": [],
        "domains_queried": [],
        "task_context": None
    }


def save_session_state(state: dict):
    """Save session state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def load_pending_tasks() -> dict:
    """Load pending background tasks awaiting completion."""
    if PENDING_TASKS_FILE.exists():
        try:
            return json.loads(PENDING_TASKS_FILE.read_text())
        except (json.JSONDecodeError, IOError, ValueError):
            pass
    return {}


def save_pending_tasks(tasks: dict):
    """Save pending background tasks."""
    PENDING_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PENDING_TASKS_FILE.write_text(json.dumps(tasks, indent=2))


def record_pending_task(task_id: str, metadata: dict):
    """Record a background task spawn as pending completion."""
    tasks = load_pending_tasks()
    tasks[task_id] = {
        "spawned_at": datetime.now().isoformat(),
        "description": metadata.get("description", "Unknown task"),
        "prompt": metadata.get("prompt", "")[:500],
        "run_id": metadata.get("run_id"),
        "exec_id": metadata.get("exec_id"),
        "heuristics_consulted": metadata.get("heuristics_consulted", []),
        "domains_queried": metadata.get("domains_queried", [])
    }
    save_pending_tasks(tasks)
    sys.stderr.write(f"[LEARNING_LOOP] Recorded pending task: {task_id}\n")


def complete_pending_task(task_id: str, outcome: str, reason: str, tool_output: dict) -> Optional[dict]:
    """Complete a pending background task with actual outcome.

    Returns the pending task metadata if found, None otherwise.
    """
    tasks = load_pending_tasks()
    if task_id not in tasks:
        sys.stderr.write(f"[LEARNING_LOOP] No pending task found for: {task_id}\n")
        return None

    pending = tasks.pop(task_id)
    save_pending_tasks(tasks)
    sys.stderr.write(f"[LEARNING_LOOP] Completing pending task: {task_id} with outcome: {outcome}\n")
    return pending


def get_db_connection():
    """Get SQLite connection."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


def determine_bash_outcome(tool_input: dict, tool_output: dict) -> Tuple[str, str]:
    """Determine if a Bash command succeeded or failed.

    Returns: (outcome, reason)
    - outcome: 'success', 'failure', 'unknown'
    - reason: description of why
    """
    if not tool_output:
        return "unknown", "No output to analyze"

    # Get output content
    output = ""
    if isinstance(tool_output, str):
        output = tool_output
    elif isinstance(tool_output, dict):
        output = tool_output.get("output", "") or tool_output.get("stdout", "") or str(tool_output)

    # Check for explicit error indicators in output
    output_lower = output.lower()

    # Exit code patterns (if captured in output)
    exit_code_match = re.search(r'exit[:\s]+code[:\s]+(\d+)', output_lower)
    if exit_code_match:
        code = int(exit_code_match.group(1))
        if code != 0:
            return "failure", f"Exit code {code}"

    # Error message patterns specific to shell commands
    bash_error_patterns = [
        (r'(?i)^.*:\s*command not found', "Command not found"),
        (r'(?i)^.*:\s*No such file or directory', "File/directory not found"),
        (r'(?i)^.*:\s*Permission denied', "Permission denied"),
        (r'(?i)^.*:\s*cannot\s+', "Operation cannot be performed"),
        (r'(?i)fatal:', "Fatal error"),
        (r'(?i)^error:', "Error occurred"),
        (r'(?i)ENOENT', "File not found (ENOENT)"),
        (r'(?i)EACCES', "Access denied (EACCES)"),
        (r'(?i)ECONNREFUSED', "Connection refused"),
        (r'(?i)npm ERR!', "npm error"),
        (r'(?i)yarn error', "yarn error"),
        (r'(?i)bun error', "bun error"),
        (r'(?i)ModuleNotFoundError', "Python module not found"),
        (r'(?i)ImportError', "Python import error"),
        (r'(?i)SyntaxError', "Syntax error"),
        (r'(?i)TypeError', "Type error"),
        (r'(?i)RuntimeError', "Runtime error"),
        (r'(?i)Traceback \(most recent', "Python exception"),
        (r'(?i)segmentation fault', "Segmentation fault"),
        (r'(?i)killed', "Process killed"),
        (r'(?i)out of memory', "Out of memory"),
    ]

    for pattern, reason in bash_error_patterns:
        if re.search(pattern, output, re.MULTILINE):
            return "failure", reason

    # Check for common success patterns
    bash_success_patterns = [
        (r'(?i)successfully', "Operation successful"),
        (r'(?i)completed', "Operation completed"),
        (r'(?i)done\.?$', "Done"),
        (r'(?i)^ok\s', "OK status"),
        (r'(?i)passed', "Tests passed"),
        (r'(?i)\d+ passing', "Tests passing"),
    ]

    for pattern, reason in bash_success_patterns:
        if re.search(pattern, output, re.MULTILINE):
            return "success", reason

    # If we got output without errors, consider it success
    if output.strip():
        return "success", "Command produced output"

    return "unknown", "No clear outcome indicators"


def determine_mcp_outcome(tool_input: dict, tool_output: dict) -> Tuple[str, str]:
    """Determine if an MCP tool call succeeded or failed.

    Returns: (outcome, reason)
    - outcome: 'success', 'failure', 'unknown'
    - reason: description of why
    """
    if not tool_output:
        return "unknown", "No output to analyze"

    # MCP responses are typically dicts
    if isinstance(tool_output, dict):
        # Check for explicit error field
        if "error" in tool_output:
            error = tool_output["error"]
            if isinstance(error, dict):
                return "failure", error.get("message", "MCP error")
            elif error:
                return "failure", str(error)[:100]

        # Check for error in content
        if "content" in tool_output:
            content = tool_output["content"]
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "error":
                            return "failure", item.get("text", "MCP content error")[:100]

        # Check for status fields
        status = tool_output.get("status", "").lower()
        if status in ("error", "failed", "failure"):
            return "failure", f"MCP status: {status}"
        if status in ("success", "ok", "completed"):
            return "success", f"MCP status: {status}"

        # Check for isError flag
        if tool_output.get("isError"):
            return "failure", "MCP isError flag set"

        # If we have results/data, it's likely success
        if tool_output.get("result") or tool_output.get("data") or tool_output.get("content"):
            return "success", "MCP returned data"

    elif isinstance(tool_output, str):
        if "error" in tool_output.lower():
            return "failure", "Error in MCP response"
        if tool_output.strip():
            return "success", "MCP returned text"

    return "unknown", "Could not determine MCP outcome"


def determine_webfetch_outcome(tool_input: dict, tool_output: dict) -> Tuple[str, str]:
    """Determine if a WebFetch/WebSearch operation succeeded or failed.

    Returns: (outcome, reason)
    - outcome: 'success', 'failure', 'unknown'
    - reason: description of why
    """
    if not tool_output:
        return "unknown", "No output to analyze"

    output_str = ""
    if isinstance(tool_output, dict):
        output_str = str(tool_output)
    elif isinstance(tool_output, str):
        output_str = tool_output

    output_lower = output_str.lower()

    # HTTP error patterns
    http_error_patterns = [
        (r'(?i)404\s*(not found)?', "HTTP 404 Not Found"),
        (r'(?i)403\s*(forbidden)?', "HTTP 403 Forbidden"),
        (r'(?i)401\s*(unauthorized)?', "HTTP 401 Unauthorized"),
        (r'(?i)500\s*(internal server)?', "HTTP 500 Server Error"),
        (r'(?i)502\s*(bad gateway)?', "HTTP 502 Bad Gateway"),
        (r'(?i)503\s*(service unavailable)?', "HTTP 503 Service Unavailable"),
        (r'(?i)timeout', "Request timeout"),
        (r'(?i)connection refused', "Connection refused"),
        (r'(?i)network error', "Network error"),
        (r'(?i)DNS.*fail', "DNS resolution failed"),
        (r'(?i)certificate.*error', "SSL certificate error"),
        (r'(?i)could not fetch', "Could not fetch URL"),
        (r'(?i)failed to fetch', "Failed to fetch URL"),
    ]

    for pattern, reason in http_error_patterns:
        if re.search(pattern, output_str):
            return "failure", reason

    # Check for redirect notification (not failure, but notable)
    if "redirect" in output_lower and "different host" in output_lower:
        return "success", "Redirect detected (follow-up needed)"

    # Success indicators
    if isinstance(tool_output, dict):
        # If we got content back, it's success
        if tool_output.get("content") or tool_output.get("text") or tool_output.get("result"):
            return "success", "Content fetched successfully"

    # If we have substantial output, consider it success
    if len(output_str) > 100:
        return "success", "Substantial content received"

    return "unknown", "Could not determine fetch outcome"


def determine_outcome(tool_output: dict) -> Tuple[str, str]:
    """Determine if the task succeeded or failed.

    Returns: (outcome, reason)
    - outcome: 'success', 'failure', 'unknown'
    - reason: description of why
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

    content_lower = content.lower()

    # Strong failure indicators (case-insensitive with word boundaries)
    failure_patterns = [
        (r'(?i)\berror\b[:\s]', "Error detected"),
        (r'(?i)\bexception\b[:\s]', "Exception raised"),
        (r'(?i)\bfailed\b[:\s]', "Operation failed"),
        (r'(?i)\bcould not\b', "Could not complete"),
        (r'(?i)\bunable to\b', "Unable to complete"),
        (r'\[BLOCKER\]', "Blocker encountered"),
        (r'(?i)\btraceback\b', "Exception traceback"),
        (r'(?i)\bpermission denied\b', "Permission denied"),
        (r'(?i)\btimed?\s+out\b', "Timeout occurred"),  # Match "timeout" or "timed out"
        (r'(?i)^.*\bnot found\s*$', "Resource not found"),  # Only at end of line
    ]

    # Patterns to exclude false positives
    # These indicate discussion of errors/failures, not actual errors
    false_positive_patterns = [
        r'(?i)was not found to be',
        r'(?i)\berror handling\b',
        r'(?i)\bno errors?\b',
        r'(?i)\bwithout errors?\b',
        r'(?i)\berror.?free\b',
        r'(?i)\b(fixed|resolved|corrected|repaired)\b.*\b(error|failure|bug|issue|exception)',  # "fixed the error"
        r'(?i)\b(error|failure|bug|issue|exception)\b.*(fixed|resolved|corrected|repaired)',   # "error was fixed"
        r'(?i)\binvestigated.*\b(failed|error|failure)',  # "investigated the failure"
        r'(?i)\banalyzed.*\b(error|failure|failed)',      # "analyzed the error"
        r'(?i)\bhandl(e|es|ed|ing).*\b(error|failure|exception)',  # "handles errors"
        r'(?i)\b(error|failure|exception)\s+handl',  # "exception handling"
        r'(?i)resolved.*\b(error|failure|exception)',  # "resolved the exception"
    ]

    for pattern, reason in failure_patterns:
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            # Verify this isn't a false positive by checking surrounding context
            match_start = max(0, match.start() - 30)
            match_end = min(len(content), match.end() + 30)
            context = content[match_start:match_end]

            # Skip if this match is part of a false positive pattern
            is_false_positive = any(
                re.search(fp, context) for fp in false_positive_patterns
            )
            if not is_false_positive:
                return "failure", reason

    # Strong success indicators - explicit completion phrases
    explicit_success_patterns = [
        (r'\bsuccessfully\s+\w+', "Successfully completed action"),
        (r'\btask\s+complete', "Task completed"),
        (r'\b(work|task) is (done|finished|complete)', "Work is done"),
        (r'\ball tests pass', "Tests passed"),
        (r'\[success\]', "Success marker found"),
        (r'## FINDINGS', "Findings reported"),
        (r'\bcompleted\s+successfully', "Completed successfully"),
    ]

    for pattern, reason in explicit_success_patterns:
        if re.search(pattern, content_lower):
            return "success", reason

    # Action verbs that indicate work was done (past tense)
    # These are strong indicators that a task was completed
    action_verb_patterns = [
        (r'\b(created|generated|built|made)\b\s+\w+', "Created something"),
        (r'\b(fixed|resolved|corrected|repaired)\b\s+\w+', "Fixed something"),
        (r'\b(updated|modified|changed|revised)\b\s+\w+', "Updated something"),
        (r'\b(implemented|added|introduced)\b\s+\w+', "Implemented something"),
        (r'\b(analyzed|examined|reviewed|investigated)\b\s+\w+', "Analyzed something"),
        (r'\b(identified|found|discovered|located)\b\s+\w+', "Identified something"),
        (r'\b(removed|deleted|cleaned)\b\s+\w+', "Removed something"),
        (r'\b(refactored|reorganized|restructured)\b\s+\w+', "Refactored something"),
        (r'\b(tested|validated|verified)\b\s+\w+', "Tested something"),
        (r'\b(deployed|released|published)\b\s+\w+', "Deployed something"),
    ]

    for pattern, reason in action_verb_patterns:
        if re.search(pattern, content_lower):
            return "success", reason

    # Reporting patterns - agent is presenting findings/results
    reporting_patterns = [
        (r'\bhere (is|are) (the |my )?(\w+\s+)?(findings|results|analysis|summary)', "Presented findings"),
        (r'\bi (have |\'ve )?(completed|finished|done)', "Agent reported completion"),
        (r'\bthe (task|work|analysis|fix|implementation) is (complete|done|finished)', "Work is complete"),
        (r'^\s*(finished|completed|done)\s+\w+', "Started with completion verb"),  # "Finished the X", "Completed the Y"
        (r'\b(summary|conclusion):', "Provided summary"),
        (r'\brecommend(ations|s)?:', "Provided recommendations"),
    ]

    for pattern, reason in reporting_patterns:
        if re.search(pattern, content_lower):
            return "success", reason

    # If we got substantial output without errors, probably success
    # Lowered threshold from 100 to 50 chars since short completions are valid
    if len(content) > 50:
        return "success", "Substantial output without errors"

    return "unknown", "Could not determine outcome"


def validate_heuristics(heuristic_ids: List[int], outcome: str):
    """Update heuristic validation counts based on outcome."""
    conn = get_db_connection()
    if not conn or not heuristic_ids:
        return

    try:
        cursor = conn.cursor()

        if outcome == "success":
            # Increment times_validated for consulted heuristics
            placeholders = ",".join("?" * len(heuristic_ids))
            cursor.execute(f"""
                UPDATE heuristics
                SET times_validated = times_validated + 1,
                    confidence = MIN(1.0, confidence + 0.01),
                    updated_at = ?
                WHERE id IN ({placeholders})
            """, (datetime.now().isoformat(), *heuristic_ids))

            # Log the validation
            for hid in heuristic_ids:
                cursor.execute("""
                    INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
                    VALUES ('heuristic_validated', 'validation', 1, ?, ?)
                """, (f"heuristic_id:{hid}", "success"))

        elif outcome == "failure":
            # Increment times_violated - heuristic might not be reliable
            placeholders = ",".join("?" * len(heuristic_ids))
            cursor.execute(f"""
                UPDATE heuristics
                SET times_violated = times_violated + 1,
                    confidence = MAX(0.0, confidence - 0.02),
                    updated_at = ?
                WHERE id IN ({placeholders})
            """, (datetime.now().isoformat(), *heuristic_ids))

            # Log the violation
            for hid in heuristic_ids:
                cursor.execute("""
                    INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
                    VALUES ('heuristic_violated', 'violation', 1, ?, ?)
                """, (f"heuristic_id:{hid}", "failure"))

        conn.commit()

    except Exception as e:
        sys.stderr.write(f"Warning: Failed to validate heuristics: {e}\n")
    finally:
        conn.close()


def check_golden_rule_promotion(conn):
    """Check if any heuristics should be promoted to golden rules."""
    try:
        cursor = conn.cursor()

        # Find heuristics with high confidence and many validations
        cursor.execute("""
            SELECT id, domain, rule, confidence, times_validated, times_violated
            FROM heuristics
            WHERE is_golden = 0
              AND confidence >= 0.9
              AND times_validated >= 10
              AND (times_violated = 0 OR times_validated / times_violated > 10)
        """)

        candidates = cursor.fetchall()

        for c in candidates:
            # Promote to golden
            cursor.execute("""
                UPDATE heuristics
                SET is_golden = 1, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), c['id']))

            # Log the promotion
            cursor.execute("""
                INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
                VALUES ('golden_rule_promotion', 'promotion', ?, ?, ?)
            """, (c['id'], f"domain:{c['domain']}", c['rule'][:100]))

            sys.stderr.write(f"PROMOTED TO GOLDEN RULE: {c['rule'][:50]}...\n")

        conn.commit()

    except Exception as e:
        sys.stderr.write(f"Warning: Failed to check golden rule promotion: {e}\n")


def auto_record_failure(tool_input: dict, tool_output: dict, outcome_reason: str, domains: List[str]):
    """Auto-record a failure to the learnings table."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()

        # Extract details
        prompt = tool_input.get("prompt", "")[:500]
        description = tool_input.get("description", "unknown task")

        # Get output content
        output_content = ""
        if isinstance(tool_output, dict):
            output_content = str(tool_output.get("content", ""))[:1000]
        elif isinstance(tool_output, str):
            output_content = tool_output[:1000]

        # Create failure record
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"auto-failures/failure_{timestamp}.md"
        title = f"Auto-captured: {description[:50]}"
        summary = f"Reason: {outcome_reason}\n\nTask: {description}\n\nOutput snippet: {output_content[:200]}"
        domain = domains[0] if domains else "general"

        cursor.execute("""
            INSERT INTO learnings (type, filepath, title, summary, domain, severity, created_at)
            VALUES ('failure', ?, ?, ?, ?, 3, ?)
        """, (filepath, title, summary, domain, datetime.now().isoformat()))

        # Log the auto-capture
        cursor.execute("""
            INSERT INTO metrics (metric_type, metric_name, metric_value, context)
            VALUES ('auto_failure_capture', 'capture', 1, ?)
        """, (title,))

        conn.commit()
        sys.stderr.write(f"AUTO-RECORDED FAILURE: {title}\n")

    except Exception as e:
        sys.stderr.write(f"Warning: Failed to auto-record failure: {e}\n")
    finally:
        conn.close()


def log_advisory_warning(file_path: str, advisory_result: Dict):
    """Log advisory warnings to the building (non-blocking)."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()

        # Log each warning
        for warning in advisory_result.get('warnings', []):
            cursor.execute("""
                INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
                VALUES ('advisory_warning', ?, 1, ?, ?)
            """, (
                warning['category'],
                f"file:{file_path}",
                warning['message']
            ))

            # Write to stderr for visibility
            sys.stderr.write(
                f"[ADVISORY] {warning['category']}: {warning['message']}\n"
                f"           Line: {warning['line_preview']}\n"
            )

        # If multiple warnings, log the escalation recommendation
        if len(advisory_result.get('warnings', [])) >= 3:
            sys.stderr.write(
                f"\n[ADVISORY] {advisory_result['recommendation']}\n"
                f"           File: {file_path}\n\n"
            )

        conn.commit()

    except Exception as e:
        sys.stderr.write(f"Warning: Failed to log advisory warning: {e}\n")
    finally:
        conn.close()


def extract_and_record_learnings(tool_output: dict, domains: List[str]):
    """Extract learnings from successful task output and record them."""
    conn = get_db_connection()
    if not conn:
        return

    # Get content
    content = ""
    if isinstance(tool_output, dict):
        content = tool_output.get("content", "")
        if isinstance(content, list):
            content = "\n".join(
                item.get("text", "") for item in content
                if isinstance(item, dict)
            )

    # Look for explicit learning markers
    # Format: [LEARNED:domain] description
    learning_pattern = r'\[LEARN(?:ED|ING)?:?([^\]]*)\]\s*([^\n]+)'
    matches = re.findall(learning_pattern, content, re.IGNORECASE)

    if not matches:
        return

    try:
        cursor = conn.cursor()

        for domain_hint, learning in matches:
            domain = domain_hint.strip() if domain_hint.strip() else (domains[0] if domains else "general")

            # Check if this might be a heuristic (contains "always", "never", "should", etc.)
            is_heuristic = any(word in learning.lower() for word in
                              ["always", "never", "should", "must", "don't", "avoid", "prefer"])

            if is_heuristic:
                # Record as heuristic
                cursor.execute("""
                    INSERT INTO heuristics (domain, rule, explanation, confidence, source_type, created_at)
                    VALUES (?, ?, 'Auto-extracted from task output', 0.5, 'auto', ?)
                """, (domain, learning.strip(), datetime.now().isoformat()))

                sys.stderr.write(f"AUTO-EXTRACTED HEURISTIC: {learning[:50]}...\n")
            else:
                # Record as observation
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                cursor.execute("""
                    INSERT INTO learnings (type, filepath, title, summary, domain, severity, created_at)
                    VALUES ('observation', ?, ?, ?, ?, 3, ?)
                """, (
                    f"auto-observations/obs_{timestamp}.md",
                    learning[:100],
                    learning,
                    domain,
                    datetime.now().isoformat()
                ))

        conn.commit()

    except Exception as e:
        sys.stderr.write(f"Warning: Failed to record learnings: {e}\n")
    finally:
        conn.close()


def main():
    """Main hook logic."""
    hook_input = get_hook_input()

    tool_name = hook_input.get("tool_name", hook_input.get("tool"))
    tool_input = hook_input.get("tool_input", hook_input.get("input", {}))
    tool_output = hook_input.get("tool_response",
                   hook_input.get("tool_output",
                   hook_input.get("output", {})))

    if not tool_name:
        output_result({})
        return

    # Advisory verification for Edit/Write tools
    if tool_name in ('Edit', 'Write'):
        verifier = AdvisoryVerifier()
        file_path = tool_input.get('file_path', '')

        # Get old and new content for comparison
        old_content = ""
        new_content = ""

        if tool_name == 'Edit':
            # For Edit: old_string is the old content, new_string is the new content
            # But we need full file context - check if tool_output contains it
            old_content = tool_output.get('old_content', tool_input.get('old_string', ''))
            new_content = tool_input.get('new_string', '')
        elif tool_name == 'Write':
            # For Write: content is the new content, old content might be in output
            old_content = tool_output.get('old_content', '')
            new_content = tool_input.get('content', '')

        # Run analysis
        result = verifier.analyze_edit(
            file_path=file_path,
            old_content=old_content,
            new_content=new_content
        )

        # Log warnings if any (non-blocking)
        if result['has_warnings']:
            log_advisory_warning(file_path, result)

        # Always approve, just attach advisory info
        output_result({
            "decision": "approve",
            "advisory": result if result['has_warnings'] else None
        })
        return

    # Track file operations (Read/Edit/Write/Glob/Grep) for hotspot trails
    file_operation_tools = {'Read', 'Edit', 'Write', 'Glob', 'Grep'}
    if tool_name in file_operation_tools:
        try:
            file_path = tool_input.get('file_path') or tool_input.get('path', '')
            if file_path:
                # Normalize path
                file_path = file_path.replace('\\', '/')
                # Extract relative path from common markers
                for marker in ['.claude/clc/', 'clc/', 'dashboard-app/']:
                    if marker in file_path:
                        file_path = file_path[file_path.index(marker):]
                        break

                # Determine scent based on operation type
                scent = 'read' if tool_name in ('Read', 'Glob', 'Grep') else 'write'
                strength = 0.5 if tool_name == 'Read' else 0.9  # Writes are more significant

                # Record trail
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO trails (run_id, location, scent, strength, agent_id, message, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (None, file_path, scent, strength, 'claude-main', f'{tool_name} operation', datetime.now().isoformat())
                    )
                    conn.commit()
                    conn.close()
                    sys.stderr.write(f"[TRAIL] Recorded {tool_name} on {file_path}\n")
        except Exception as e:
            sys.stderr.write(f"[TRAIL_ERROR] Failed to record file operation trail: {e}\n")

        output_result({})
        return

    # =========================================================================
    # HANDLE Bash - Shell command outcomes
    # =========================================================================
    if tool_name == "Bash":
        outcome, reason = determine_bash_outcome(tool_input, tool_output)
        command = tool_input.get("command", "unknown")[:100]

        # Only record significant commands (skip trivial ones)
        trivial_commands = ['echo', 'pwd', 'ls', 'cd', 'cat', 'head', 'tail', 'sleep']
        is_trivial = any(command.strip().startswith(cmd) for cmd in trivial_commands)

        if not is_trivial or outcome == "failure":
            try:
                sys.path.insert(0, str(Path.home() / '.claude' / 'clc' / 'conductor'))
                from conductor import Conductor, Node

                conductor = Conductor(
                    base_path=str(Path.home() / '.claude' / 'clc'),
                    project_root=str(Path.home() / '.claude' / 'clc')
                )

                description = tool_input.get('description', command)[:100]
                run_id = conductor.start_run(
                    workflow_name=f"bash-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    input_data={
                        'command': command,
                        'description': description
                    }
                )

                if run_id:
                    node = Node(
                        id=f"bash-{datetime.now().timestamp()}",
                        name=description,
                        node_type='single',
                        prompt_template=command,
                        config={'tool': 'Bash'}
                    )
                    exec_id = conductor.record_node_start(run_id, node, command)

                    if outcome == 'failure':
                        conductor.record_node_failure(
                            exec_id=exec_id,
                            error_message=reason,
                            error_type='bash_error'
                        )
                        conductor.update_run_status(run_id, 'failed', error_message=reason)
                        sys.stderr.write(f"[LEARNING_LOOP] Bash FAILURE recorded: {reason}\n")
                    else:
                        output_text = str(tool_output)[:500] if tool_output else ""
                        conductor.record_node_completion(
                            exec_id=exec_id,
                            result_text=output_text,
                            result_dict={'outcome': outcome, 'reason': reason}
                        )
                        conductor.update_run_status(run_id, 'completed', output={'outcome': outcome, 'reason': reason})
            except Exception as e:
                sys.stderr.write(f"[LEARNING_LOOP] Bash tracking error (non-fatal): {e}\n")

        output_result({})
        return

    # =========================================================================
    # HANDLE MCP tools - External server calls
    # =========================================================================
    if tool_name.startswith("mcp__"):
        outcome, reason = determine_mcp_outcome(tool_input, tool_output)

        try:
            sys.path.insert(0, str(Path.home() / '.claude' / 'clc' / 'conductor'))
            from conductor import Conductor, Node

            conductor = Conductor(
                base_path=str(Path.home() / '.claude' / 'clc'),
                project_root=str(Path.home() / '.claude' / 'clc')
            )

            # Parse MCP tool name (e.g., mcp__server__tool)
            parts = tool_name.split("__")
            server_name = parts[1] if len(parts) > 1 else "unknown"
            tool_method = parts[2] if len(parts) > 2 else "unknown"

            run_id = conductor.start_run(
                workflow_name=f"mcp-{server_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                input_data={
                    'server': server_name,
                    'method': tool_method,
                    'input': str(tool_input)[:500]
                }
            )

            if run_id:
                node = Node(
                    id=f"mcp-{datetime.now().timestamp()}",
                    name=f"{server_name}.{tool_method}",
                    node_type='single',
                    prompt_template=str(tool_input)[:200],
                    config={'tool': tool_name, 'server': server_name}
                )
                exec_id = conductor.record_node_start(run_id, node, str(tool_input)[:500])

                if outcome == 'failure':
                    conductor.record_node_failure(
                        exec_id=exec_id,
                        error_message=reason,
                        error_type='mcp_error'
                    )
                    conductor.update_run_status(run_id, 'failed', error_message=reason)
                    sys.stderr.write(f"[LEARNING_LOOP] MCP FAILURE ({server_name}.{tool_method}): {reason}\n")
                else:
                    output_text = str(tool_output)[:500] if tool_output else ""
                    conductor.record_node_completion(
                        exec_id=exec_id,
                        result_text=output_text,
                        result_dict={'outcome': outcome, 'reason': reason}
                    )
                    conductor.update_run_status(run_id, 'completed', output={'outcome': outcome, 'reason': reason})
        except Exception as e:
            sys.stderr.write(f"[LEARNING_LOOP] MCP tracking error (non-fatal): {e}\n")

        output_result({})
        return

    # =========================================================================
    # HANDLE WebFetch/WebSearch - Network operations
    # =========================================================================
    if tool_name in ("WebFetch", "WebSearch"):
        outcome, reason = determine_webfetch_outcome(tool_input, tool_output)

        try:
            sys.path.insert(0, str(Path.home() / '.claude' / 'clc' / 'conductor'))
            from conductor import Conductor, Node

            conductor = Conductor(
                base_path=str(Path.home() / '.claude' / 'clc'),
                project_root=str(Path.home() / '.claude' / 'clc')
            )

            url = tool_input.get('url', tool_input.get('query', 'unknown'))[:200]

            run_id = conductor.start_run(
                workflow_name=f"{tool_name.lower()}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                input_data={
                    'url': url,
                    'prompt': tool_input.get('prompt', '')[:200]
                }
            )

            if run_id:
                node = Node(
                    id=f"{tool_name.lower()}-{datetime.now().timestamp()}",
                    name=f"{tool_name}: {url[:50]}",
                    node_type='single',
                    prompt_template=url,
                    config={'tool': tool_name}
                )
                exec_id = conductor.record_node_start(run_id, node, url)

                if outcome == 'failure':
                    conductor.record_node_failure(
                        exec_id=exec_id,
                        error_message=reason,
                        error_type='webfetch_error'
                    )
                    conductor.update_run_status(run_id, 'failed', error_message=reason)
                    sys.stderr.write(f"[LEARNING_LOOP] {tool_name} FAILURE: {reason}\n")
                else:
                    output_text = str(tool_output)[:500] if tool_output else ""
                    conductor.record_node_completion(
                        exec_id=exec_id,
                        result_text=output_text,
                        result_dict={'outcome': outcome, 'reason': reason}
                    )
                    conductor.update_run_status(run_id, 'completed', output={'outcome': outcome, 'reason': reason})
        except Exception as e:
            sys.stderr.write(f"[LEARNING_LOOP] {tool_name} tracking error (non-fatal): {e}\n")

        output_result({})
        return

    # Process Task and TaskOutput tools for learning loop
    # Task: handles synchronous tasks and background task spawns
    # TaskOutput: handles background task completions (the actual results)
    if tool_name not in ("Task", "TaskOutput"):
        output_result({})
        return

    # Load session state
    state = load_session_state()
    heuristics_consulted = state.get("heuristics_consulted", [])
    domains_queried = state.get("domains_queried", [])

    # =========================================================================
    # HANDLE TaskOutput - Complete pending background task
    # =========================================================================
    if tool_name == "TaskOutput":
        task_id = tool_input.get('task_id', 'unknown')
        sys.stderr.write(f"[LEARNING_LOOP] Processing TaskOutput for task_id: {task_id}\n")

        # Determine outcome from actual result
        outcome, reason = determine_outcome(tool_output)

        # Try to complete pending task
        pending = complete_pending_task(task_id, outcome, reason, tool_output)

        if pending and pending.get('run_id') and pending.get('exec_id'):
            # Complete the existing workflow run
            try:
                sys.path.insert(0, str(Path.home() / '.claude' / 'clc' / 'conductor'))
                from conductor import Conductor

                conductor = Conductor(
                    base_path=str(Path.home() / '.claude' / 'clc'),
                    project_root=str(Path.home() / '.claude' / 'clc')
                )

                run_id = pending['run_id']
                exec_id = pending['exec_id']

                if outcome == 'failure':
                    conductor.record_node_failure(
                        exec_id=exec_id,
                        error_message=reason,
                        error_type='task_failure'
                    )
                    conductor.update_run_status(run_id, 'failed', error_message=reason)
                else:
                    result_text = str(tool_output.get('content', '') if isinstance(tool_output, dict) else tool_output)[:1000]
                    conductor.record_node_completion(
                        exec_id=exec_id,
                        result_text=result_text,
                        result_dict={'outcome': outcome, 'reason': reason}
                    )
                    conductor.update_run_status(run_id, 'completed', output={'outcome': outcome, 'reason': reason})

                sys.stderr.write(f"[LEARNING_LOOP] Completed pending workflow run_id={run_id} with outcome={outcome}\n")
            except Exception as e:
                sys.stderr.write(f"Conductor integration error (non-fatal): {e}\n")
        else:
            # No pending task found - create new workflow record
            sys.stderr.write(f"[LEARNING_LOOP] No pending task for {task_id}, creating new workflow record\n")
            try:
                sys.path.insert(0, str(Path.home() / '.claude' / 'clc' / 'conductor'))
                from conductor import Conductor, Node

                conductor = Conductor(
                    base_path=str(Path.home() / '.claude' / 'clc'),
                    project_root=str(Path.home() / '.claude' / 'clc')
                )

                run_id = conductor.start_run(
                    workflow_name=f"taskoutput-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    input_data={'task_id': task_id}
                )

                if run_id:
                    node = Node(
                        id=f"taskoutput-{task_id}",
                        name=f"TaskOutput: {task_id}",
                        node_type='single',
                        prompt_template='',
                        config={'model': 'claude'}
                    )
                    exec_id = conductor.record_node_start(run_id, node, '')

                    if outcome == 'failure':
                        conductor.record_node_failure(exec_id=exec_id, error_message=reason, error_type='task_failure')
                        conductor.update_run_status(run_id, 'failed', error_message=reason)
                    else:
                        result_text = str(tool_output.get('content', '') if isinstance(tool_output, dict) else tool_output)[:1000]
                        conductor.record_node_completion(exec_id=exec_id, result_text=result_text, result_dict={'outcome': outcome, 'reason': reason})
                        conductor.update_run_status(run_id, 'completed', output={'outcome': outcome, 'reason': reason})
            except Exception as e:
                sys.stderr.write(f"Conductor integration error (non-fatal): {e}\n")

        # Continue to trail laying (below)
        outcome_for_trails = outcome
        tool_output_for_trails = tool_output

    # =========================================================================
    # HANDLE Task - Background spawn or synchronous completion
    # =========================================================================
    elif tool_name == "Task":
        is_background = tool_input.get('run_in_background', False)

        if is_background:
            # Background task spawn - record as pending, don't complete yet
            # Extract agent_id from tool_output (Claude returns it when spawning)
            agent_id = None
            if isinstance(tool_output, dict):
                agent_id = tool_output.get('agentId') or tool_output.get('agent_id')
                # Also check content for agent ID pattern
                content = tool_output.get('content', '')
                if isinstance(content, str) and 'agentId:' in content:
                    import re
                    match = re.search(r'agentId:\s*([a-f0-9]+)', content)
                    if match:
                        agent_id = match.group(1)

            if not agent_id:
                # Generate a fallback ID based on timestamp
                agent_id = f"bg-{datetime.now().strftime('%H%M%S')}-{hash(str(tool_input.get('prompt', '')))%10000:04d}"

            sys.stderr.write(f"[LEARNING_LOOP] Background task spawn detected, agent_id: {agent_id}\n")

            # Create workflow run and record as pending
            try:
                sys.path.insert(0, str(Path.home() / '.claude' / 'clc' / 'conductor'))
                from conductor import Conductor, Node

                conductor = Conductor(
                    base_path=str(Path.home() / '.claude' / 'clc'),
                    project_root=str(Path.home() / '.claude' / 'clc')
                )

                description = tool_input.get('description', 'Background task')
                run_id = conductor.start_run(
                    workflow_name=f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    input_data={
                        'description': description,
                        'prompt': tool_input.get('prompt', '')[:500],
                        'background': True,
                        'agent_id': agent_id
                    }
                )

                exec_id = None
                if run_id:
                    node = Node(
                        id=f"task-{agent_id}",
                        name=description[:100],
                        node_type='single',
                        prompt_template=tool_input.get('prompt', '')[:500],
                        config={'model': 'claude', 'background': True}
                    )
                    exec_id = conductor.record_node_start(run_id, node, tool_input.get('prompt', ''))

                # Record as pending for later completion
                record_pending_task(agent_id, {
                    'description': description,
                    'prompt': tool_input.get('prompt', ''),
                    'run_id': run_id,
                    'exec_id': exec_id,
                    'heuristics_consulted': heuristics_consulted,
                    'domains_queried': domains_queried
                })

            except Exception as e:
                sys.stderr.write(f"Conductor integration error (non-fatal): {e}\n")

            # Don't do trail laying for spawn - wait for completion
            output_result({})
            return

        else:
            # Synchronous task - process immediately
            outcome, reason = determine_outcome(tool_output)

            try:
                sys.path.insert(0, str(Path.home() / '.claude' / 'clc' / 'conductor'))
                from conductor import Conductor, Node

                conductor = Conductor(
                    base_path=str(Path.home() / '.claude' / 'clc'),
                    project_root=str(Path.home() / '.claude' / 'clc')
                )

                description = tool_input.get('description', 'Unknown task')
                run_id = conductor.start_run(
                    workflow_name=f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    input_data={
                        'description': description,
                        'prompt': tool_input.get('prompt', '')[:500]
                    }
                )

                if run_id:
                    node = Node(
                        id=f"task-{datetime.now().timestamp()}",
                        name=description[:100],
                        node_type='single',
                        prompt_template=tool_input.get('prompt', '')[:500],
                        config={'model': 'claude'}
                    )
                    exec_id = conductor.record_node_start(run_id, node, tool_input.get('prompt', ''))

                    if outcome == 'failure':
                        conductor.record_node_failure(
                            exec_id=exec_id,
                            error_message=reason,
                            error_type='task_failure'
                        )
                        conductor.update_run_status(run_id, 'failed', error_message=reason)
                    else:
                        conductor.record_node_completion(
                            exec_id=exec_id,
                            result_text=str(tool_output.get('content', '') if isinstance(tool_output, dict) else tool_output)[:1000],
                            result_dict={'outcome': outcome, 'reason': reason}
                        )
                        conductor.update_run_status(run_id, 'completed', output={'outcome': outcome, 'reason': reason})
            except Exception as e:
                sys.stderr.write(f"Conductor integration error (non-fatal): {e}\n")

            # Continue to trail laying
            outcome_for_trails = outcome
            tool_output_for_trails = tool_output

    # Lay trails for files mentioned in output
    try:
        sys.stderr.write("[TRAIL_DEBUG] Starting trail extraction from tool output\n")
        output_content = ""
        if isinstance(tool_output, dict):
            output_content = str(tool_output.get("content", ""))
        elif isinstance(tool_output, str):
            output_content = tool_output

        sys.stderr.write(f"[TRAIL_DEBUG] Output content length: {len(output_content)}\n")

        file_paths = extract_file_paths(output_content)
        sys.stderr.write(f"[TRAIL_DEBUG] Extracted {len(file_paths)} file paths: {file_paths}\n")

        if file_paths:
            description = tool_input.get("description", "")
            agent_type = tool_input.get("subagent_type", "unknown")
            sys.stderr.write(f"[TRAIL_DEBUG] Calling lay_trails with agent_type={agent_type}, description={description[:50]}\n")
            trails_count = lay_trails(file_paths, outcome, agent_id=agent_type, description=description)
            sys.stderr.write(f"[TRAIL_DEBUG] lay_trails returned: {trails_count}\n")
        else:
            sys.stderr.write("[TRAIL_DEBUG] No file paths extracted, skipping trail laying\n")
    except Exception as e:
        sys.stderr.write(f"[TRAIL_ERROR] Exception in trail laying section: {type(e).__name__}: {e}\n")
        import traceback
        sys.stderr.write(f"[TRAIL_ERROR] Traceback: {traceback.format_exc()}\n")

    # Validate heuristics based on outcome
    if heuristics_consulted:
        validate_heuristics(heuristics_consulted, outcome)

    # Check for golden rule promotions
    conn = get_db_connection()
    if conn:
        check_golden_rule_promotion(conn)
        conn.close()

    # Auto-record failure if task failed
    if outcome == "failure":
        auto_record_failure(tool_input, tool_output, reason, domains_queried)

    # Extract any explicit learnings from output
    if outcome == "success":
        extract_and_record_learnings(tool_output, domains_queried)

    # Clear consulted heuristics for next task
    state["heuristics_consulted"] = []
    save_session_state(state)

    # Log outcome
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
                VALUES ('task_outcome', ?, 1, ?, ?)
            """, (outcome, f"reason:{reason[:50]}", datetime.now().isoformat()))
            conn.commit()
        except:
            pass
        finally:
            conn.close()

    # Output (no modification to tool output)
    output_result({})


if __name__ == "__main__":
    main()
