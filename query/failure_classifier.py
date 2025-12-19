#!/usr/bin/env python3
"""
Failure Classifier: Categorize failures as fixable vs unfixable.

This module analyzes error outputs and classifies them to determine
whether self-healing should be attempted.

Part of the Auto-Claude Integration (P0: Self-Healing QA Loops).
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Configuration path
CONFIG_PATH = Path.home() / ".claude" / "clc" / "config" / "self-healing.yaml"


class FailureCategory(Enum):
    """Categories of failures."""
    FIXABLE = "fixable"
    UNFIXABLE = "unfixable"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Result of failure classification."""
    category: FailureCategory
    failure_type: str  # e.g., "lint_error", "type_error", "permission_error"
    confidence: float  # 0.0-1.0
    matched_pattern: Optional[str]
    error_context: Dict = field(default_factory=dict)
    unfixable_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category.value,
            "failure_type": self.failure_type,
            "confidence": self.confidence,
            "matched_pattern": self.matched_pattern,
            "error_context": self.error_context,
            "unfixable_reason": self.unfixable_reason
        }


class FailureClassifier:
    """Classifies failures as fixable or unfixable."""

    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config = self._load_config(config_path)
        self.fixable_patterns = self._compile_patterns(
            self.config.get("self_healing", {}).get("fixable_patterns", {})
        )
        self.unfixable_patterns = self._compile_patterns(
            self.config.get("self_healing", {}).get("unfixable_patterns", {})
        )

    def _load_config(self, config_path: Path) -> Dict:
        """Load configuration from YAML file."""
        if not config_path.exists():
            return self._default_config()

        try:
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, IOError):
            return self._default_config()

    def _default_config(self) -> Dict:
        """Return default configuration if file doesn't exist."""
        return {
            "self_healing": {
                "enabled": True,
                "fixable_patterns": {
                    "syntax_error": {
                        "patterns": ["SyntaxError", "Parse error"],
                        "confidence": 0.9
                    },
                    "type_error": {
                        "patterns": ["TypeError", "type.*not assignable"],
                        "confidence": 0.85
                    },
                    "import_error": {
                        "patterns": ["ImportError", "ModuleNotFoundError"],
                        "confidence": 0.85
                    },
                    "test_failure": {
                        "patterns": ["FAILED", "AssertionError"],
                        "confidence": 0.8
                    }
                },
                "unfixable_patterns": {
                    "permission_error": {
                        "patterns": ["EACCES", "Permission denied"],
                        "reason": "Permission issues require human intervention"
                    }
                }
            }
        }

    def _compile_patterns(self, patterns_config: Dict) -> Dict[str, Dict]:
        """Compile regex patterns for efficient matching."""
        compiled = {}
        for failure_type, config in patterns_config.items():
            patterns = config.get("patterns", [])
            compiled[failure_type] = {
                "regex": [re.compile(p, re.IGNORECASE) for p in patterns],
                "confidence": config.get("confidence", 0.5),
                "reason": config.get("reason")
            }
        return compiled

    def classify(self, error_output: str, tool_name: str = None,
                 tool_input: Dict = None) -> ClassificationResult:
        """
        Classify a failure based on error output.

        Args:
            error_output: The error message/output to classify
            tool_name: Optional tool that generated the error
            tool_input: Optional tool input context

        Returns:
            ClassificationResult with category, type, and confidence
        """
        error_output = error_output or ""
        tool_input = tool_input or {}

        # Check unfixable patterns FIRST (they take precedence)
        for failure_type, config in self.unfixable_patterns.items():
            for pattern in config["regex"]:
                match = pattern.search(error_output)
                if match:
                    return ClassificationResult(
                        category=FailureCategory.UNFIXABLE,
                        failure_type=failure_type,
                        confidence=1.0,  # Unfixable patterns are definitive
                        matched_pattern=match.group(0),
                        error_context=self._extract_context(
                            error_output, match, tool_name, tool_input
                        ),
                        unfixable_reason=config.get("reason",
                            "Matched unfixable pattern")
                    )

        # Check fixable patterns
        best_match = None
        best_confidence = 0.0

        for failure_type, config in self.fixable_patterns.items():
            for pattern in config["regex"]:
                match = pattern.search(error_output)
                if match and config["confidence"] > best_confidence:
                    best_match = (failure_type, match, config["confidence"])
                    best_confidence = config["confidence"]

        if best_match:
            failure_type, match, confidence = best_match
            return ClassificationResult(
                category=FailureCategory.FIXABLE,
                failure_type=failure_type,
                confidence=confidence,
                matched_pattern=match.group(0),
                error_context=self._extract_context(
                    error_output, match, tool_name, tool_input
                )
            )

        # Unknown category - could try generic fix or escalate
        return ClassificationResult(
            category=FailureCategory.UNKNOWN,
            failure_type="unknown",
            confidence=0.0,
            matched_pattern=None,
            error_context=self._extract_context(
                error_output, None, tool_name, tool_input
            )
        )

    def _extract_context(self, error_output: str, match: Optional[re.Match],
                         tool_name: str, tool_input: Dict) -> Dict:
        """Extract relevant context from the error for fix generation."""
        context = {
            "full_error": error_output[:2000],  # Limit size
            "tool_name": tool_name,
            "tool_input_summary": str(tool_input)[:500] if tool_input else None
        }

        # Extract file path if present (various formats)
        file_patterns = [
            r'File "([^"]+)"',  # Python traceback
            r'at ([^\s]+\.(?:ts|tsx|js|jsx|py|rb|go|rs|java)):',  # JS/TS stack traces
            r'([/\\][\w./\\-]+\.\w{1,10}):\d+',  # path:line format
            r'([/\\][\w./\\-]+\.\w{1,10})\s*\(\d+',  # path (line format
        ]
        for pattern in file_patterns:
            file_match = re.search(pattern, error_output)
            if file_match:
                context["file_path"] = file_match.group(1)
                break

        # Extract line number if present
        line_patterns = [
            r':(\d+):\d+',  # file:line:col
            r':(\d+)\)',  # file:line)
            r'line\s*(\d+)',  # "line 42"
            r'Line\s*(\d+)',  # "Line 42"
        ]
        for pattern in line_patterns:
            line_match = re.search(pattern, error_output, re.IGNORECASE)
            if line_match:
                context["line_number"] = int(line_match.group(1))
                break

        # Extract column if present
        col_match = re.search(r':(\d+):(\d+)', error_output)
        if col_match:
            context["column_number"] = int(col_match.group(2))

        # Extract function/method name if present
        func_patterns = [
            r"in (\w+)\(",  # Python traceback
            r"at (\w+)\s*\(",  # JS stack traces
            r"function (\w+)",  # function keyword
            r"method (\w+)",  # method keyword
        ]
        for pattern in func_patterns:
            func_match = re.search(pattern, error_output)
            if func_match:
                context["function_name"] = func_match.group(1)
                break

        # Add match-specific context
        if match:
            context["matched_text"] = match.group(0)
            # Get surrounding context (100 chars before, 200 after)
            start = max(0, match.start() - 100)
            end = min(len(error_output), match.end() + 200)
            context["error_snippet"] = error_output[start:end]

        # Extract error message (first line of error usually)
        first_error_line = None
        for line in error_output.split('\n'):
            if any(kw in line.lower() for kw in ['error', 'exception', 'failed', 'traceback']):
                first_error_line = line.strip()[:200]
                break
        if first_error_line:
            context["error_line"] = first_error_line

        return context

    def get_fix_hint(self, result: ClassificationResult) -> str:
        """Get a hint for how to fix based on failure type."""
        hints = {
            "lint_error": "Run linter with --fix flag or apply auto-fix suggestions",
            "type_error": "Add proper type annotations or fix type mismatches",
            "test_failure": "Analyze test output, identify assertion that failed, fix code or test",
            "import_error": "Check module name, install missing package, or fix import path",
            "syntax_error": "Check syntax around the error location, fix brackets/quotes/indentation",
            "runtime_error": "Analyze stack trace, identify root cause, add error handling or fix logic"
        }
        return hints.get(result.failure_type, "Analyze error and attempt fix")


def classify_failure(error_output: str, tool_name: str = None,
                     tool_input: Dict = None) -> ClassificationResult:
    """
    Convenience function to classify a failure.

    This is the main entry point for other modules.
    """
    classifier = FailureClassifier()
    return classifier.classify(error_output, tool_name, tool_input)


# For testing
if __name__ == "__main__":
    # Test cases
    test_cases = [
        "TypeError: Cannot read property 'foo' of undefined",
        "SyntaxError: Unexpected token '}' at line 42",
        "EACCES: permission denied, open '/etc/passwd'",
        "pytest: FAILED test_user_login - AssertionError",
        "ImportError: No module named 'nonexistent'",
        "Some random output that is not an error",
    ]

    classifier = FailureClassifier()
    for test in test_cases:
        result = classifier.classify(test)
        print(f"\nInput: {test[:60]}...")
        print(f"  Category: {result.category.value}")
        print(f"  Type: {result.failure_type}")
        print(f"  Confidence: {result.confidence:.0%}")
        if result.unfixable_reason:
            print(f"  Reason: {result.unfixable_reason}")
