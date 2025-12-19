#!/usr/bin/env python3
"""
Fix Strategies: Generate fix prompts based on failure type.

Each strategy knows how to build a prompt for the fix agent
and how to validate the fix was successful.

Part of the Auto-Claude Integration (P0: Self-Healing QA Loops).
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class FixPrompt:
    """Generated prompt for fix agent."""
    system_context: str
    task_prompt: str
    validation_hint: str
    model_preference: str  # haiku, sonnet, opus


class BaseStrategy(ABC):
    """Base class for fix strategies."""

    @abstractmethod
    def build_prompt(self, error_context: Dict, attempt: int) -> FixPrompt:
        """Build a prompt for the fix agent."""
        pass

    @abstractmethod
    def validate_fix(self, output: str) -> bool:
        """Validate that the fix was successful."""
        pass

    def _escalation_context(self, attempt: int) -> str:
        """Add context about previous attempts."""
        if attempt == 1:
            return ""
        if attempt == 2:
            return "\n\n**Note:** This is attempt #2. The previous fix attempt failed. Try a different approach."
        if attempt >= 3:
            return f"\n\n**IMPORTANT:** This is attempt #{attempt}. Previous {attempt-1} attempts failed. Think carefully about why and try a fundamentally different approach. Consider if there's a deeper issue."
        return ""

    def _format_file_location(self, context: Dict) -> str:
        """Format file location from context."""
        parts = []
        if context.get("file_path"):
            parts.append(f"**File:** `{context['file_path']}`")
        if context.get("line_number"):
            parts.append(f"**Line:** {context['line_number']}")
        if context.get("column_number"):
            parts.append(f"**Column:** {context['column_number']}")
        if context.get("function_name"):
            parts.append(f"**Function:** `{context['function_name']}`")
        return "\n".join(parts) if parts else ""


class LintErrorStrategy(BaseStrategy):
    """Strategy for fixing lint errors."""

    def build_prompt(self, error_context: Dict, attempt: int) -> FixPrompt:
        file_path = error_context.get("file_path", "the affected file")
        error_snippet = error_context.get("error_snippet", error_context.get("full_error", ""))

        task_prompt = f"""Fix the following lint error:

{self._format_file_location(error_context)}

**Error:**
```
{error_snippet[:1500]}
```

**Instructions:**
1. Read the file to understand the context
2. Identify the specific lint violations
3. Fix each violation following the linter's rules
4. Common fixes:
   - Unused variables: Remove or use them
   - Missing semicolons: Add them
   - Inconsistent quotes: Standardize
   - Import order: Reorder imports
5. Run the linter again to verify the fix
{self._escalation_context(attempt)}"""

        return FixPrompt(
            system_context="You are a code quality expert. Fix lint errors precisely with minimal changes.",
            task_prompt=task_prompt,
            validation_hint="Run linter to verify fix (e.g., npm run lint, eslint, ruff)",
            model_preference="haiku"
        )

    def validate_fix(self, output: str) -> bool:
        """Check if lint output indicates success."""
        success_indicators = [
            "no errors",
            "0 errors",
            "0 warnings",
            "all clear",
            "lint passed",
            "successfully fixed",
            "no issues found",
            "no problems"
        ]
        output_lower = output.lower()
        return any(ind in output_lower for ind in success_indicators)


class TypeErrorStrategy(BaseStrategy):
    """Strategy for fixing type errors."""

    def build_prompt(self, error_context: Dict, attempt: int) -> FixPrompt:
        error_snippet = error_context.get("error_snippet", error_context.get("full_error", ""))

        task_prompt = f"""Fix the following type error:

{self._format_file_location(error_context)}

**Error:**
```
{error_snippet[:1500]}
```

**Instructions:**
1. Read the file and understand the type issue
2. Analyze the error message carefully - it tells you exactly what's wrong
3. Determine the appropriate fix:
   - **Missing property:** Add the property to the type/interface
   - **Type mismatch:** Cast, convert, or fix the value type
   - **Missing type annotation:** Add explicit types
   - **Incorrect generic:** Fix generic type parameters
   - **Union type issue:** Add type guards or narrow the type
4. Apply the minimal fix that resolves the type error
5. Ensure the fix doesn't break other type checks
6. Run type checker to verify (tsc, mypy, pyright)
{self._escalation_context(attempt)}"""

        return FixPrompt(
            system_context="You are a type system expert. Fix type errors with minimal, precise changes.",
            task_prompt=task_prompt,
            validation_hint="Run type checker (tsc --noEmit, mypy, pyright) to verify",
            model_preference="sonnet" if attempt > 2 else "haiku"
        )

    def validate_fix(self, output: str) -> bool:
        output_lower = output.lower()
        success_indicators = ["no errors", "0 errors", "type check passed", "found 0 errors"]
        failure_indicators = ["error", "type error", "cannot find", "not assignable"]

        # Check for explicit success
        if any(ind in output_lower for ind in success_indicators):
            return True

        # Check for absence of failure indicators
        return not any(ind in output_lower for ind in failure_indicators)


class TestFailureStrategy(BaseStrategy):
    """Strategy for fixing test failures."""

    def build_prompt(self, error_context: Dict, attempt: int) -> FixPrompt:
        error_snippet = error_context.get("error_snippet", error_context.get("full_error", ""))

        task_prompt = f"""Fix the following test failure:

{self._format_file_location(error_context)}

**Error:**
```
{error_snippet[:2000]}
```

**Instructions:**
1. Analyze the test failure carefully:
   - What assertion failed?
   - What was the expected value?
   - What was the actual value?
2. Determine the root cause:
   - Is there a bug in the code being tested?
   - Is the test expectation incorrect?
   - Is there a setup/teardown issue?
3. Fix the appropriate code:
   - If the code has a bug → fix the implementation
   - If the test is wrong → fix the test (with justification)
   - If it's a flaky test → add proper async handling/mocking
4. Re-run the specific failing test to verify
{self._escalation_context(attempt)}

**Important:**
- Don't just make the test pass by weakening assertions
- Fix the actual root cause
- If unsure whether code or test is wrong, investigate before fixing"""

        return FixPrompt(
            system_context="You are a testing expert. Analyze test failures and fix root causes, not symptoms.",
            task_prompt=task_prompt,
            validation_hint="Re-run the failing test(s) to verify the fix",
            model_preference="sonnet"  # Tests often need more reasoning
        )

    def validate_fix(self, output: str) -> bool:
        output_lower = output.lower()
        # Look for passed tests
        if ("passed" in output_lower or "pass" in output_lower) and "failed" not in output_lower:
            return True
        if "all tests passed" in output_lower:
            return True
        if "0 failed" in output_lower:
            return True
        return False


class ImportErrorStrategy(BaseStrategy):
    """Strategy for fixing import errors."""

    def build_prompt(self, error_context: Dict, attempt: int) -> FixPrompt:
        error_snippet = error_context.get("error_snippet", error_context.get("full_error", ""))

        task_prompt = f"""Fix the following import error:

{self._format_file_location(error_context)}

**Error:**
```
{error_snippet[:1500]}
```

**Instructions:**
1. Identify the module that cannot be imported
2. Determine the cause and fix:

   **Wrong module name:**
   - Check for typos in the import statement
   - Verify the correct package name (e.g., `PIL` vs `pillow`)

   **Wrong import path:**
   - Check relative vs absolute imports
   - Verify the file exists at the expected location
   - Check __init__.py files for package imports

   **Missing package:**
   - If it's a third-party package, note what needs to be installed
   - DO NOT run install commands (pip/npm) - just document the need

   **Circular import:**
   - Move import inside function
   - Restructure to break the cycle
   - Use TYPE_CHECKING for type-only imports

3. Verify the import works after the fix
{self._escalation_context(attempt)}"""

        return FixPrompt(
            system_context="You are a Python/Node.js expert. Fix import errors with proper module resolution.",
            task_prompt=task_prompt,
            validation_hint="Try importing the module to verify (python -c 'import X' or node -e 'require(X)')",
            model_preference="haiku"
        )

    def validate_fix(self, output: str) -> bool:
        output_lower = output.lower()
        failure_indicators = ["importerror", "modulenotfounderror", "cannot find module", "module not found"]
        return not any(ind in output_lower for ind in failure_indicators)


class SyntaxErrorStrategy(BaseStrategy):
    """Strategy for fixing syntax errors."""

    def build_prompt(self, error_context: Dict, attempt: int) -> FixPrompt:
        error_snippet = error_context.get("error_snippet", error_context.get("full_error", ""))

        task_prompt = f"""Fix the following syntax error:

{self._format_file_location(error_context)}

**Error:**
```
{error_snippet[:1500]}
```

**Instructions:**
1. Read the file around the error location
2. Identify the syntax error. Common causes:
   - **Mismatched brackets:** (), [], {{}} - count opens and closes
   - **Missing colons:** Python requires : after if/for/def/class
   - **Missing commas:** Between items in lists, dicts, function args
   - **Unclosed strings:** Check for matching quotes
   - **Incorrect indentation:** Python is whitespace-sensitive
   - **Reserved word misuse:** Using keywords as variable names
   - **Invalid characters:** Unicode issues, wrong quote types

3. Fix the syntax error with minimal changes
4. Verify the file parses correctly
{self._escalation_context(attempt)}

**Tip:** The line number in the error often points to where the parser noticed the problem, but the actual error may be on a previous line (e.g., unclosed bracket on line 41 causes error on line 42)."""

        return FixPrompt(
            system_context="You are a syntax expert. Fix parsing errors precisely with minimal changes.",
            task_prompt=task_prompt,
            validation_hint="Try parsing the file (python -m py_compile X.py, node --check X.js)",
            model_preference="haiku"
        )

    def validate_fix(self, output: str) -> bool:
        output_lower = output.lower()
        failure_indicators = ["syntaxerror", "parse error", "unexpected token", "invalid syntax"]
        return not any(ind in output_lower for ind in failure_indicators)


class RuntimeErrorStrategy(BaseStrategy):
    """Strategy for fixing runtime errors."""

    def build_prompt(self, error_context: Dict, attempt: int) -> FixPrompt:
        error_snippet = error_context.get("error_snippet", error_context.get("full_error", ""))

        task_prompt = f"""Fix the following runtime error:

{self._format_file_location(error_context)}

**Error:**
```
{error_snippet[:2000]}
```

**Instructions:**
1. Analyze the stack trace to find the root cause
2. Identify the error type and fix accordingly:

   **KeyError / AttributeError:**
   - Add existence check before access
   - Use .get() with default for dicts
   - Check if attribute exists

   **ValueError:**
   - Validate input before using
   - Add proper type conversion
   - Handle edge cases

   **IndexError:**
   - Check bounds before accessing
   - Handle empty collections

   **NoneType errors:**
   - Add null checks
   - Initialize variables properly
   - Handle optional values

3. Don't just catch the exception - fix the underlying issue
4. Add appropriate error handling if needed
{self._escalation_context(attempt)}"""

        return FixPrompt(
            system_context="You are a debugging expert. Analyze stack traces and fix root causes.",
            task_prompt=task_prompt,
            validation_hint="Re-run the operation that caused the error",
            model_preference="sonnet" if attempt > 1 else "haiku"
        )

    def validate_fix(self, output: str) -> bool:
        output_lower = output.lower()
        # For runtime errors, absence of error indicators is success
        failure_indicators = [
            "error", "exception", "traceback", "failed",
            "keyerror", "valueerror", "typeerror", "indexerror",
            "attributeerror", "nameerror"
        ]
        # But allow "error handling" and similar phrases
        if "error handling" in output_lower or "no error" in output_lower:
            return True
        return not any(ind in output_lower for ind in failure_indicators)


class GenericErrorStrategy(BaseStrategy):
    """Fallback strategy for unknown error types."""

    def build_prompt(self, error_context: Dict, attempt: int) -> FixPrompt:
        error_snippet = error_context.get("full_error", "Unknown error")
        tool_name = error_context.get("tool_name", "unknown")

        task_prompt = f"""Analyze and fix the following error:

**Tool:** {tool_name}
{self._format_file_location(error_context)}

**Error:**
```
{error_snippet[:2000]}
```

**Instructions:**
1. Carefully analyze the error message
2. Identify:
   - What operation was attempted?
   - What went wrong?
   - What's the root cause?
3. Determine if this is fixable:
   - If yes: Apply the fix
   - If no: Clearly explain why with "CANNOT_FIX:" prefix
4. Verify the fix works
{self._escalation_context(attempt)}

**Note:** If you determine this error cannot be automatically fixed (e.g., requires credentials, external service fix, architectural decision), respond with:
```
CANNOT_FIX: [reason]
```
This will escalate to human review."""

        return FixPrompt(
            system_context="You are a debugging expert. Analyze errors and attempt fixes when possible.",
            task_prompt=task_prompt,
            validation_hint="Verify the original operation succeeds",
            model_preference="sonnet" if attempt > 1 else "haiku"
        )

    def validate_fix(self, output: str) -> bool:
        output_lower = output.lower()
        # If agent says they can't fix it, that's not success
        if "cannot_fix:" in output_lower:
            return False
        # Otherwise, check for general success indicators
        if "fixed" in output_lower or "resolved" in output_lower:
            return True
        # And absence of error indicators
        if "error" not in output_lower or "no error" in output_lower:
            return True
        return False


# Strategy registry
STRATEGIES: Dict[str, BaseStrategy] = {
    "lint_error": LintErrorStrategy(),
    "type_error": TypeErrorStrategy(),
    "test_failure": TestFailureStrategy(),
    "import_error": ImportErrorStrategy(),
    "syntax_error": SyntaxErrorStrategy(),
    "runtime_error": RuntimeErrorStrategy(),
    "unknown": GenericErrorStrategy(),
}


def get_strategy(failure_type: str) -> BaseStrategy:
    """Get the appropriate strategy for a failure type."""
    return STRATEGIES.get(failure_type, STRATEGIES["unknown"])


def build_fix_prompt(failure_type: str, error_context: Dict, attempt: int) -> FixPrompt:
    """
    Convenience function to build a fix prompt.

    This is the main entry point for other modules.
    """
    strategy = get_strategy(failure_type)
    return strategy.build_prompt(error_context, attempt)


# For testing
if __name__ == "__main__":
    # Test each strategy
    test_context = {
        "file_path": "/app/src/component.tsx",
        "line_number": 42,
        "error_snippet": "TypeError: Property 'foo' does not exist on type 'Bar'",
        "full_error": "Error at component.tsx:42\nTypeError: Property 'foo' does not exist on type 'Bar'"
    }

    for name, strategy in STRATEGIES.items():
        print(f"\n=== {name} Strategy ===")
        prompt = strategy.build_prompt(test_context, attempt=1)
        print(f"Model: {prompt.model_preference}")
        print(f"System: {prompt.system_context[:80]}...")
        print(f"Validation: {prompt.validation_hint}")
