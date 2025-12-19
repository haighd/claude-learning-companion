#!/usr/bin/env python3
"""
Self-Healer: Main healing loop logic for automatic failure recovery.

This module orchestrates the self-healing process:
1. Receives failure classification
2. Checks healing eligibility (circuit breaker, max attempts)
3. Selects model based on attempt number
4. Builds and executes fix prompt
5. Records attempt to database
6. Determines if CEO escalation is needed

Part of the Auto-Claude Integration (P0: Self-Healing QA Loops).
"""

import hashlib
import json
import sys
import sqlite3
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict

# Import siblings
try:
    from failure_classifier import FailureClassifier, ClassificationResult, FailureCategory
    from fix_strategies import get_strategy, build_fix_prompt, FixPrompt
except ImportError:
    # Handle direct execution
    from query.failure_classifier import FailureClassifier, ClassificationResult, FailureCategory
    from query.fix_strategies import get_strategy, build_fix_prompt, FixPrompt

# Paths
CLC_PATH = Path.home() / ".claude" / "clc"
DB_PATH = CLC_PATH / "memory" / "index.db"
CONFIG_PATH = CLC_PATH / "config" / "self-healing.yaml"
HEALING_STATE_FILE = Path.home() / ".claude" / "hooks" / "learning-loop" / "healing-state.json"
CEO_INBOX_PATH = CLC_PATH / "ceo-inbox"


@dataclass
class HealingAttempt:
    """Record of a healing attempt."""
    failure_id: str
    attempt_number: int
    model_used: str
    strategy_used: str
    success: bool
    error_context: str
    fix_applied: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class HealingResult:
    """Result of self-healing attempt."""
    action: str  # "heal", "escalate", "skip"
    success: bool
    should_escalate: bool
    failure_id: Optional[str] = None
    healing_attempt_id: Optional[int] = None
    escalation_reason: Optional[str] = None
    prompt: Optional[str] = None
    model: Optional[str] = None
    failure_type: Optional[str] = None
    attempt_number: Optional[int] = None
    max_attempts: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.

    States:
    - CLOSED: Normal operation, healing allowed
    - OPEN: Too many failures, healing blocked
    - HALF_OPEN: Testing if system recovered
    """

    STATES = ("closed", "open", "half_open")

    def __init__(self, failure_threshold: int = 3, reset_timeout_minutes: int = 30,
                 half_open_attempts: int = 1):
        self.failure_threshold = failure_threshold
        self.reset_timeout = timedelta(minutes=reset_timeout_minutes)
        self.half_open_attempts = half_open_attempts
        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_successes = 0

    def can_attempt(self) -> Tuple[bool, str]:
        """Check if an attempt is allowed."""
        if self.state == "closed":
            return True, "Circuit closed - healing allowed"

        if self.state == "open":
            # Check if timeout has passed
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > self.reset_timeout:
                self.state = "half_open"
                self.half_open_successes = 0
                return True, "Circuit half-open - testing with limited attempts"
            timeout_remaining = ""
            if self.last_failure_time:
                remaining = (self.last_failure_time + self.reset_timeout) - datetime.now()
                timeout_remaining = f" ({int(remaining.total_seconds() / 60)} min remaining)"
            return False, f"Circuit open - healing disabled{timeout_remaining}"

        if self.state == "half_open":
            if self.half_open_successes < self.half_open_attempts:
                return True, "Circuit half-open - limited attempts allowed"
            return False, "Circuit half-open - no more test attempts allowed"

        return False, "Unknown circuit state"

    def record_success(self):
        """Record a successful healing."""
        if self.state == "half_open":
            self.half_open_successes += 1
            if self.half_open_successes >= self.half_open_attempts:
                self.state = "closed"
                self.failure_count = 0
                sys.stderr.write("[SELF_HEALER] Circuit breaker reset to closed\n")
        elif self.state == "closed":
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record a failed healing."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == "half_open":
            # Any failure in half-open goes back to open
            self.state = "open"
            sys.stderr.write("[SELF_HEALER] Circuit breaker tripped (half-open -> open)\n")
        elif self.failure_count >= self.failure_threshold:
            self.state = "open"
            sys.stderr.write(f"[SELF_HEALER] Circuit breaker tripped after {self.failure_count} failures\n")

    def to_dict(self) -> Dict:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "half_open_successes": self.half_open_successes
        }

    @classmethod
    def from_dict(cls, data: Dict, **kwargs) -> "CircuitBreaker":
        cb = cls(**kwargs)
        cb.state = data.get("state", "closed")
        cb.failure_count = data.get("failure_count", 0)
        if data.get("last_failure_time"):
            try:
                cb.last_failure_time = datetime.fromisoformat(data["last_failure_time"])
            except (ValueError, TypeError):
                cb.last_failure_time = None
        cb.half_open_successes = data.get("half_open_successes", 0)
        return cb


class SelfHealer:
    """Main self-healing orchestrator."""

    def __init__(self, config_path: Path = CONFIG_PATH, db_path: Path = DB_PATH):
        self.config = self._load_config(config_path)
        self.db_path = db_path
        self.classifier = FailureClassifier(config_path)

        # Initialize circuit breaker from config
        cb_config = self.config.get("self_healing", {}).get("circuit_breaker", {})
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=cb_config.get("failure_threshold", 3),
            reset_timeout_minutes=cb_config.get("reset_timeout_minutes", 30),
            half_open_attempts=cb_config.get("half_open_attempts", 1)
        )

        # Load persisted state
        self._load_state()

    def _load_config(self, config_path: Path) -> Dict:
        """Load configuration."""
        if not config_path.exists():
            return {"self_healing": {"enabled": True, "max_attempts": 5}}
        try:
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, IOError):
            return {"self_healing": {"enabled": True, "max_attempts": 5}}

    def _load_state(self):
        """Load persisted healing state."""
        if HEALING_STATE_FILE.exists():
            try:
                with open(HEALING_STATE_FILE) as f:
                    state = json.load(f)
                    if "circuit_breaker" in state:
                        cb_config = self.config.get("self_healing", {}).get("circuit_breaker", {})
                        self.circuit_breaker = CircuitBreaker.from_dict(
                            state["circuit_breaker"],
                            failure_threshold=cb_config.get("failure_threshold", 3),
                            reset_timeout_minutes=cb_config.get("reset_timeout_minutes", 30)
                        )
            except (json.JSONDecodeError, KeyError, IOError):
                pass

    def _save_state(self):
        """Persist healing state."""
        HEALING_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "circuit_breaker": self.circuit_breaker.to_dict(),
            "last_updated": datetime.now().isoformat()
        }
        try:
            with open(HEALING_STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except IOError as e:
            sys.stderr.write(f"[SELF_HEALER] Failed to save state: {e}\n")

    def is_enabled(self) -> bool:
        """Check if self-healing is enabled."""
        return self.config.get("self_healing", {}).get("enabled", True)

    def get_max_attempts(self) -> int:
        """Get maximum healing attempts."""
        return self.config.get("self_healing", {}).get("max_attempts", 5)

    def get_model_for_attempt(self, attempt: int) -> str:
        """Select model based on escalation strategy."""
        strategy = self.config.get("self_healing", {}).get("model_escalation_strategy", [])

        for tier in strategy:
            if attempt in tier.get("attempts", []):
                return tier.get("model", "haiku")

        # Default escalation
        if attempt <= 2:
            return "haiku"
        elif attempt <= 4:
            return "sonnet"
        else:
            return "opus"

    def get_current_attempt_count(self, failure_id: str) -> int:
        """Get current attempt count for a failure from database."""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM healing_attempts
                WHERE failure_id = ?
            """, (failure_id,))
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except sqlite3.OperationalError:
            # Table might not exist yet
            return 0
        except Exception:
            return 0

    def should_attempt_healing(self, failure_id: str,
                               classification: ClassificationResult) -> Tuple[bool, str]:
        """
        Determine if healing should be attempted.

        Returns:
            (should_attempt, reason)
        """
        # Check if enabled
        if not self.is_enabled():
            return False, "Self-healing is disabled"

        # Check classification
        if classification.category == FailureCategory.UNFIXABLE:
            return False, f"Failure classified as unfixable: {classification.unfixable_reason}"

        if classification.category == FailureCategory.UNKNOWN and classification.confidence < 0.3:
            return False, "Failure type unknown with low confidence - escalating"

        # Check circuit breaker
        can_attempt, cb_reason = self.circuit_breaker.can_attempt()
        if not can_attempt:
            return False, f"Circuit breaker: {cb_reason}"

        # Check attempt count
        current_attempts = self.get_current_attempt_count(failure_id)
        if current_attempts >= self.get_max_attempts():
            return False, f"Max attempts ({self.get_max_attempts()}) reached"

        return True, f"Eligible for healing (attempt {current_attempts + 1}/{self.get_max_attempts()})"

    def attempt_healing(self, failure_id: str, classification: ClassificationResult,
                        exec_id: Optional[int] = None) -> HealingResult:
        """
        Execute a healing attempt.

        Args:
            failure_id: Unique identifier for this failure
            classification: Result from FailureClassifier
            exec_id: Optional node_executions.id for linking

        Returns:
            HealingResult with action, prompt, model, etc.
        """
        max_attempts = self.get_max_attempts()

        # Check eligibility
        should_attempt, reason = self.should_attempt_healing(failure_id, classification)

        if not should_attempt:
            return HealingResult(
                action="escalate",
                success=False,
                should_escalate=True,
                failure_id=failure_id,
                escalation_reason=reason,
                failure_type=classification.failure_type,
                max_attempts=max_attempts
            )

        # Get attempt number
        attempt_number = self.get_current_attempt_count(failure_id) + 1

        # Select model
        model = self.get_model_for_attempt(attempt_number)

        # Build fix prompt
        fix_prompt = build_fix_prompt(
            classification.failure_type,
            classification.error_context,
            attempt_number
        )

        # Record attempt (will be updated with result later)
        attempt_id = self._record_attempt(HealingAttempt(
            failure_id=failure_id,
            attempt_number=attempt_number,
            model_used=model,
            strategy_used=classification.failure_type,
            success=False,  # Will be updated
            error_context=json.dumps(classification.error_context)[:2000]
        ))

        # Build the full task prompt
        full_prompt = f"""{fix_prompt.system_context}

{fix_prompt.task_prompt}

**Validation:** {fix_prompt.validation_hint}

---
*Self-Healing Context:*
- Failure ID: {failure_id[:12]}...
- Attempt: {attempt_number}/{max_attempts}
- Model: {model}
- Strategy: {classification.failure_type}

When done, clearly indicate SUCCESS or FAILURE with a brief explanation."""

        return HealingResult(
            action="heal",
            success=False,  # Will be determined by Task result
            should_escalate=False,
            failure_id=failure_id,
            healing_attempt_id=attempt_id,
            prompt=full_prompt,
            model=model,
            failure_type=classification.failure_type,
            attempt_number=attempt_number,
            max_attempts=max_attempts
        )

    def record_healing_outcome(self, attempt_id: int, success: bool,
                               fix_applied: Optional[str] = None,
                               duration_ms: Optional[int] = None):
        """Record the outcome of a healing attempt."""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE healing_attempts
                SET success = ?, fix_applied = ?, duration_ms = ?
                WHERE id = ?
            """, (success, fix_applied, duration_ms, attempt_id))

            conn.commit()
            conn.close()

            # Update circuit breaker
            if success:
                self.circuit_breaker.record_success()
            else:
                self.circuit_breaker.record_failure()

            self._save_state()

        except Exception as e:
            sys.stderr.write(f"[SELF_HEALER] Failed to record outcome: {e}\n")

    def _record_attempt(self, attempt: HealingAttempt) -> Optional[int]:
        """Record a healing attempt to the database."""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO healing_attempts
                (failure_id, attempt_number, model_used, strategy_used,
                 success, error_context, fix_applied, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attempt.failure_id,
                attempt.attempt_number,
                attempt.model_used,
                attempt.strategy_used,
                attempt.success,
                attempt.error_context,
                attempt.fix_applied,
                datetime.now().isoformat()
            ))

            attempt_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return attempt_id

        except sqlite3.OperationalError as e:
            sys.stderr.write(f"[SELF_HEALER] Database error (table may not exist): {e}\n")
            return None
        except Exception as e:
            sys.stderr.write(f"[SELF_HEALER] Error recording attempt: {e}\n")
            return None

    def create_ceo_escalation(self, failure_id: str,
                              classification: ClassificationResult,
                              reason: str, attempts: int = 0) -> str:
        """
        Create a CEO inbox item for manual intervention.

        Returns:
            Path to created escalation file
        """
        CEO_INBOX_PATH.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
        safe_type = classification.failure_type[:20].replace("/", "-")
        filename = f"{timestamp}-healing-failure-{safe_type}.md"
        filepath = CEO_INBOX_PATH / filename

        error_snippet = classification.error_context.get("full_error", "No error details available")[:1500]
        file_location = ""
        if classification.error_context.get("file_path"):
            file_location = f"\n- **File:** {classification.error_context['file_path']}"
        if classification.error_context.get("line_number"):
            file_location += f":{classification.error_context['line_number']}"

        content = f"""---
status: pending
priority: medium
domain: self-healing
created: {datetime.now().strftime("%Y-%m-%d")}
---

# Self-Healing Escalation: {classification.failure_type}

## Summary
Automated self-healing was unable to resolve this failure after {attempts} attempts.

## Escalation Reason
{reason}

## Failure Details
- **Failure ID:** `{failure_id}`
- **Category:** {classification.category.value}
- **Type:** {classification.failure_type}
- **Confidence:** {classification.confidence:.0%}{file_location}
{f"- **Unfixable Reason:** {classification.unfixable_reason}" if classification.unfixable_reason else ""}

## Error Context
```
{error_snippet}
```

## Matched Pattern
`{classification.matched_pattern or "No pattern matched"}`

## Recommended Actions
1. **Manually Fix** - Investigate and apply fix yourself
2. **Add Pattern** - If this is a new fixable pattern, add it to `config/self-healing.yaml`
3. **Dismiss** - If this was a transient issue that resolved itself
4. **Investigate** - If more context is needed before deciding

## Resolution
<!-- Update status to 'resolved' and add notes below when addressed -->

"""

        filepath.write_text(content)
        sys.stderr.write(f"[SELF_HEALER] Created CEO escalation: {filepath}\n")
        return str(filepath)


def generate_failure_id(error_output: str, tool_name: str = None) -> str:
    """Generate a unique failure ID from error content."""
    # Hash the error output + tool name + date for uniqueness
    content = f"{error_output[:500]}:{tool_name or 'unknown'}:{datetime.now().date()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def process_failure(error_output: str, tool_name: str = None,
                    tool_input: Dict = None, exec_id: int = None) -> Optional[Dict]:
    """
    Process a failure and determine healing action.

    This is the main entry point for the PostToolUse hook.

    Returns:
        Dict with healing instructions, or None if no healing needed
    """
    healer = SelfHealer()

    if not healer.is_enabled():
        return None

    # Classify the failure
    classification = healer.classifier.classify(error_output, tool_name, tool_input)

    # Skip if not a recognized failure type
    if classification.category == FailureCategory.UNKNOWN and classification.confidence == 0:
        return None

    # Generate a failure ID
    failure_id = generate_failure_id(error_output, tool_name)

    # Attempt healing
    result = healer.attempt_healing(failure_id, classification, exec_id)

    if result.should_escalate:
        attempts = healer.get_current_attempt_count(failure_id)
        healer.create_ceo_escalation(
            failure_id,
            classification,
            result.escalation_reason or "Unknown reason",
            attempts
        )
        return {
            "action": "escalate",
            "reason": result.escalation_reason,
            "failure_id": failure_id,
            "failure_type": classification.failure_type
        }

    if result.prompt:
        return {
            "action": "heal",
            "failure_id": failure_id,
            "attempt_id": result.healing_attempt_id,
            "prompt": result.prompt,
            "model": result.model,
            "failure_type": result.failure_type,
            "attempt_number": result.attempt_number,
            "max_attempts": result.max_attempts
        }

    return None


# For testing
if __name__ == "__main__":
    # Test the self-healer
    test_errors = [
        ("TypeError: Cannot read property 'foo' of undefined", "Bash"),
        ("SyntaxError: Unexpected token '}' at line 42", "Edit"),
        ("EACCES: permission denied, open '/etc/passwd'", "Write"),
        ("pytest: FAILED test_user_login - AssertionError", "Bash"),
    ]

    healer = SelfHealer()
    print(f"Self-healing enabled: {healer.is_enabled()}")
    print(f"Max attempts: {healer.get_max_attempts()}")
    print(f"Circuit breaker state: {healer.circuit_breaker.state}")
    print()

    for error, tool in test_errors:
        print(f"Error: {error[:50]}...")
        result = process_failure(error, tool)
        if result:
            print(f"  Action: {result['action']}")
            if result['action'] == 'heal':
                print(f"  Model: {result['model']}")
                print(f"  Attempt: {result['attempt_number']}/{result['max_attempts']}")
            elif result['action'] == 'escalate':
                print(f"  Reason: {result['reason']}")
        else:
            print("  No healing action")
        print()
