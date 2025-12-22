"""
Unit tests for workflow outcome detection in post_tool_learning.py.

Tests the determine_bash_outcome() function to ensure proper classification
of bash command results as success, failure, or unknown.

Issue: #39 - Workflow outcomes showing 'unknown' status
Target: < 10% unknown outcomes
"""

import sys
from pathlib import Path

# Add hooks directory to path for imports, relative to this test file
HOOKS_DIR = Path(__file__).resolve().parents[1] / 'hooks' / 'learning-loop'
sys.path.insert(0, str(HOOKS_DIR))

import pytest
from post_tool_learning import determine_bash_outcome


class TestEmptyOutputSuccess:
    """Test that empty output with no errors is classified as success."""

    def test_empty_stdout_stderr_is_success(self):
        """Empty output with no errors = success (silent command)."""
        result = determine_bash_outcome(
            {},
            {"stdout": "", "stderr": "", "interrupted": False, "isImage": False}
        )
        assert result[0] == "success"
        assert "silently" in result[1].lower()

    def test_empty_string_output_is_unknown(self):
        """Empty string output = unknown (ambiguous, could be no output).

        When tool_output is a plain empty string (not a dict with empty fields),
        Python treats it as falsy and the function returns early with "No output
        to analyze". This is correct - an empty string at this level is ambiguous.
        Use dict format with explicit stdout/stderr fields for clarity.
        """
        result = determine_bash_outcome({}, "")
        assert result[0] == "unknown"
        assert "no output" in result[1].lower()


class TestJsonResponseSuccess:
    """Test that JSON responses are classified as success."""

    def test_json_object_response_is_success(self):
        """JSON object response = success."""
        result = determine_bash_outcome(
            {},
            {"stdout": '{"comments":[]}', "stderr": "", "interrupted": False}
        )
        assert result[0] == "success"
        assert "json" in result[1].lower()

    def test_json_array_response_is_success(self):
        """JSON array response = success."""
        result = determine_bash_outcome(
            {},
            {"stdout": '[{"id": 1}, {"id": 2}]', "stderr": "", "interrupted": False}
        )
        assert result[0] == "success"
        assert "json" in result[1].lower()

    def test_invalid_json_not_matched(self):
        """Invalid JSON should not match JSON pattern."""
        result = determine_bash_outcome(
            {},
            {"stdout": '{invalid json', "stderr": "", "interrupted": False}
        )
        # Should still be success via success-by-absence logic (no stderr)
        assert result[0] == "success"


class TestFallbackMessageSuccess:
    """Test that fallback messages without errors are classified as success."""

    def test_no_script_found_is_success(self):
        """Fallback messages without errors = success."""
        result = determine_bash_outcome(
            {},
            {"stdout": "No codex review script found", "stderr": "", "interrupted": False}
        )
        assert result[0] == "success"

    def test_labels_may_not_exist_is_success(self):
        """Informational messages = success."""
        result = determine_bash_outcome(
            {},
            {"stdout": "Labels may not exist", "stderr": "", "interrupted": False}
        )
        assert result[0] == "success"


class TestErrorInStderrIsFailure:
    """Test that errors in stderr are classified as failure."""

    def test_error_in_stderr_is_failure(self):
        """Error in stderr = failure."""
        result = determine_bash_outcome(
            {},
            {"stdout": "", "stderr": "Error: command not found", "interrupted": False}
        )
        assert result[0] == "failure"

    def test_permission_denied_is_failure(self):
        """Permission denied = failure."""
        result = determine_bash_outcome(
            {},
            {"stdout": "", "stderr": "Permission denied", "interrupted": False}
        )
        assert result[0] == "failure"

    def test_fatal_error_is_failure(self):
        """Fatal error = failure."""
        result = determine_bash_outcome(
            {},
            {"stdout": "", "stderr": "fatal: not a git repository", "interrupted": False}
        )
        assert result[0] == "failure"


class TestExitCodeDetection:
    """Test exit code detection from output text."""

    def test_exit_code_1_is_failure(self):
        """Exit code 1 in output = failure."""
        result = determine_bash_outcome(
            {},
            {"stdout": "Command failed with exit code 1", "stderr": "", "interrupted": False}
        )
        assert result[0] == "failure"

    def test_exit_code_0_not_failure(self):
        """Exit code 0 should not be classified as failure."""
        result = determine_bash_outcome(
            {},
            {"stdout": "Completed with exit code 0", "stderr": "", "interrupted": False}
        )
        # Exit code 0 is not matched by failure pattern, so success via other patterns
        assert result[0] == "success"


class TestSuccessPatterns:
    """Test explicit success pattern matching."""

    def test_successfully_keyword(self):
        """'successfully' keyword = success."""
        result = determine_bash_outcome(
            {},
            {"stdout": "File copied successfully", "stderr": "", "interrupted": False}
        )
        assert result[0] == "success"
        assert "successful" in result[1].lower()

    def test_tests_passed(self):
        """Tests passed = success."""
        result = determine_bash_outcome(
            {},
            {"stdout": "All tests passed", "stderr": "", "interrupted": False}
        )
        assert result[0] == "success"
        assert "pass" in result[1].lower()

    def test_count_result(self):
        """Count results = success."""
        result = determine_bash_outcome(
            {},
            {"stdout": "Found 15 files", "stderr": "", "interrupted": False}
        )
        assert result[0] == "success"

    def test_created_keyword(self):
        """'created' keyword = success."""
        result = determine_bash_outcome(
            {},
            {"stdout": "Branch created", "stderr": "", "interrupted": False}
        )
        assert result[0] == "success"

    def test_boolean_true(self):
        """Boolean true = success."""
        result = determine_bash_outcome(
            {},
            {"stdout": "true", "stderr": "", "interrupted": False}
        )
        assert result[0] == "success"
        assert "boolean" in result[1].lower()

    def test_boolean_false(self):
        """Boolean false = success (command completed with result).

        Outputting 'false' is distinct from failure - the command successfully
        returned a boolean result (e.g., git config, test commands).
        """
        result = determine_bash_outcome(
            {},
            {"stdout": "false", "stderr": "", "interrupted": False}
        )
        assert result[0] == "success"
        assert "boolean" in result[1].lower()

    def test_already_exists(self):
        """'already exists' (idempotent) = success."""
        result = determine_bash_outcome(
            {},
            {"stdout": "Directory already exists", "stderr": "", "interrupted": False}
        )
        assert result[0] == "success"


class TestWarningHandling:
    """Test that warnings are handled appropriately."""

    def test_warning_in_output_is_unknown(self):
        """Warnings result in unknown outcome (conservative approach).

        Warnings are concerning but not failures. The success-by-absence logic
        explicitly checks for warning patterns and excludes them from automatic
        success classification, resulting in 'unknown' for human review.
        """
        result = determine_bash_outcome(
            {},
            {"stdout": "Warning: deprecated function used", "stderr": "", "interrupted": False}
        )
        assert result[0] == "unknown"
        assert "could not determine" in result[1].lower()


class TestStderrPresent:
    """Test behavior when stderr has content."""

    def test_stderr_with_unknown_content(self):
        """Unknown stderr content = unknown outcome."""
        result = determine_bash_outcome(
            {},
            {"stdout": "Some output", "stderr": "Some stderr message", "interrupted": False}
        )
        # Stderr present without matching error patterns
        assert result[0] == "unknown"
        assert "stderr" in result[1].lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_none_output(self):
        """None output = unknown."""
        result = determine_bash_outcome({}, None)
        assert result[0] == "unknown"

    def test_string_output_success(self):
        """String output with success keyword = success."""
        result = determine_bash_outcome({}, "Operation completed successfully")
        assert result[0] == "success"

    def test_string_output_failure(self):
        """String output with error = failure."""
        result = determine_bash_outcome({}, "Error: something went wrong")
        assert result[0] == "failure"

    def test_whitespace_only_stdout(self):
        """Whitespace-only stdout with no stderr = success (silent)."""
        result = determine_bash_outcome(
            {},
            {"stdout": "   \n  \t  ", "stderr": "", "interrupted": False}
        )
        assert result[0] == "success"
        assert "silently" in result[1].lower()


class TestPythonErrors:
    """Test Python-specific error patterns."""

    def test_traceback_is_failure(self):
        """Python traceback = failure."""
        result = determine_bash_outcome(
            {},
            {"stdout": "Traceback (most recent call last):\n  File...", "stderr": "", "interrupted": False}
        )
        assert result[0] == "failure"

    def test_import_error_is_failure(self):
        """ImportError = failure."""
        result = determine_bash_outcome(
            {},
            {"stdout": "", "stderr": "ImportError: No module named 'foo'", "interrupted": False}
        )
        assert result[0] == "failure"

    def test_module_not_found_is_failure(self):
        """ModuleNotFoundError = failure."""
        result = determine_bash_outcome(
            {},
            {"stdout": "", "stderr": "ModuleNotFoundError: No module named 'bar'", "interrupted": False}
        )
        assert result[0] == "failure"


class TestNpmErrors:
    """Test npm/yarn/bun error patterns."""

    def test_npm_err_is_failure(self):
        """npm ERR! = failure."""
        result = determine_bash_outcome(
            {},
            {"stdout": "npm ERR! code ENOENT", "stderr": "", "interrupted": False}
        )
        assert result[0] == "failure"

    def test_connection_refused_is_failure(self):
        """ECONNREFUSED = failure."""
        result = determine_bash_outcome(
            {},
            {"stdout": "", "stderr": "ECONNREFUSED", "interrupted": False}
        )
        assert result[0] == "failure"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
