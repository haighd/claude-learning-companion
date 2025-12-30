#!/usr/bin/env python3
"""
CLC Backend Skills Interface

Provides a unified Python API for all CLC backend services.
Can be used directly or as the backend for skill invocations.

Issue: #69
Implementation Date: December 29, 2025

Usage:
    from interface import CLCBackend

    clc = CLCBackend()

    # Query context
    context = clc.query(domain="security")

    # Progressive load
    result = clc.progressive_query(
        task="implement auth",
        domain="security",
        tier="recommended"
    )

    # Record heuristic
    clc.record_heuristic(
        domain="testing",
        rule="Mock external APIs",
        explanation="Prevents flaky tests"
    )
"""

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add CLC paths for imports
# Note: sys.path manipulation is intentional here. CLC is designed as a
# user-installed CLI tool in ~/.claude/clc, not a pip-installable package.
# This allows the interface to import from the CLC installation regardless
# of where this script is invoked from. The alternative (making CLC a proper
# package) would require pip install which conflicts with the git-based
# update mechanism and user customization workflow.
CLC_PATH = Path.home() / ".claude" / "clc"
sys.path.insert(0, str(CLC_PATH / "query"))
sys.path.insert(0, str(CLC_PATH / "agents"))


@dataclass
class QueryResult:
    """Result from a CLC query."""
    context: str
    golden_rules: List[str]
    heuristics: List[Dict]
    learnings: List[Dict]
    experiments: List[Dict]
    ceo_inbox: List[Dict]
    metadata: Dict[str, Any]


@dataclass
class RecordResult:
    """Result from a recording operation."""
    success: bool
    file_path: Optional[str]
    message: str


class CLCBackend:
    """Unified interface to CLC backend services."""

    def __init__(self, clc_path: Optional[Path] = None):
        self.clc_path = clc_path or CLC_PATH
        self._validate_installation()

    def _validate_installation(self) -> None:
        """Check if CLC is properly installed. Raises FileNotFoundError on failure."""
        required_files = {
            "query script": self.clc_path / "query" / "query.py",
            "golden rules": self.clc_path / "golden-rules" / "RULES.md",
        }
        for name, path in required_files.items():
            if not path.exists():
                raise FileNotFoundError(
                    f"CLC installation is incomplete. Missing {name}: {path}"
                )

    def query(
        self,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        full: bool = False
    ) -> QueryResult:
        """
        Query CLC for context.

        Args:
            domain: Optional domain filter
            tags: Optional tag filters
            full: Whether to include full context

        Returns:
            QueryResult with all context components
        """
        cmd = [sys.executable, str(self.clc_path / "query" / "query.py")]

        if domain:
            cmd.extend(["--domain", domain])
        if tags:
            cmd.extend(["--tags"] + tags)
        if full:
            cmd.append("--full")

        cmd.append("--json")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return QueryResult(
                    context=data.get("context", ""),
                    golden_rules=data.get("golden_rules", []),
                    heuristics=data.get("heuristics", []),
                    learnings=data.get("learnings", []),
                    experiments=data.get("experiments", []),
                    ceo_inbox=data.get("ceo_inbox", []),
                    metadata=data.get("metadata", {})
                )
            else:
                # Fallback to basic context
                return self._fallback_query()

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return self._fallback_query()

    def _fallback_query(self) -> QueryResult:
        """Fallback query using direct file reads."""
        golden_rules = []
        rules_file = self.clc_path / "golden-rules" / "RULES.md"
        if rules_file.exists():
            golden_rules = [rules_file.read_text(encoding="utf-8")]

        return QueryResult(
            context="CLC query fallback - check query.py",
            golden_rules=golden_rules,
            heuristics=[],
            learnings=[],
            experiments=[],
            ceo_inbox=[],
            metadata={"fallback": True}
        )

    def progressive_query(
        self,
        task: str,
        domain: Optional[str] = None,
        tier: str = "recommended",
        max_tokens: int = 5000
    ) -> Dict[str, Any]:
        """
        Progressive disclosure query with token budgeting.

        Args:
            task: Task description for relevance scoring
            domain: Optional domain filter
            tier: Loading tier (essential, recommended, full)
            max_tokens: Maximum token budget

        Returns:
            Dict with context, summary, and metadata
        """
        try:
            from progressive import progressive_query as pq

            # Load golden rules
            golden_rules = ""
            rules_file = self.clc_path / "golden-rules" / "RULES.md"
            if rules_file.exists():
                golden_rules = rules_file.read_text(encoding="utf-8")

            # Load heuristics
            heuristics = self._load_heuristics()

            # Load learnings
            learnings = self._load_learnings()

            return pq(
                task_description=task,
                domain=domain,
                tier=tier,
                max_tokens=max_tokens,
                golden_rules=golden_rules,
                heuristics=heuristics,
                learnings=learnings
            )

        except ImportError:
            # Fallback if progressive.py not available
            return {
                "context": f"# Task: {task}\n\nProgressive loading unavailable.",
                "summary": {"error": "progressive.py not found"},
                "metadata": {"fallback": True}
            }

    def _load_heuristics(self) -> List[Dict]:
        """Load heuristics from memory directory.

        Note: This uses file-based loading rather than the SQLite database.
        This is intentional for the native skills interface - it provides a
        lightweight read-only view without requiring database initialization.
        For full query capabilities with confidence scores, use query.py.
        """
        heuristics = []
        heuristics_dir = self.clc_path / "memory" / "heuristics"

        if heuristics_dir.exists():
            for f in heuristics_dir.glob("*.md"):
                content = f.read_text(encoding="utf-8")
                # Parse heuristic rule from markdown content
                # Use regex to find the line starting with '## H-X: '
                rule_match = re.search(r"##\s+H-\d+:\s*(.*)", content)
                rule = rule_match.group(1).strip() if rule_match else content.split('\n')[0]

                heuristics.append({
                    "file": f.name,
                    "domain": f.stem,  # Filename without extension as domain (e.g., "ci-workflow", "hooks")
                    "rule": rule,
                    # Use 'created_at' key for compatibility with progressive.py RelevanceScorer
                    # which uses this field for recency scoring. The mtime is the best available
                    # approximation for heuristic freshness when loading from markdown files.
                    "created_at": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()
                })

        return heuristics

    def _load_learnings(self) -> List[Dict]:
        """Load learnings from memory directory.

        Note: Uses file-based loading for lightweight read-only access.
        See _load_heuristics for design rationale.
        """
        learnings = []
        learnings_dir = self.clc_path / "memory" / "learnings"

        if learnings_dir.exists():
            for f in learnings_dir.rglob("*.json"):
                try:
                    with open(f, encoding="utf-8") as fp:
                        data = json.load(fp)
                        learnings.append(data)
                except (json.JSONDecodeError, IOError):
                    pass

        return learnings

    def record_heuristic(
        self,
        domain: str,
        rule: str,
        explanation: str
    ) -> RecordResult:
        """
        Record a learned heuristic.

        Args:
            domain: Domain this heuristic applies to
            rule: The heuristic rule
            explanation: Why this matters

        Returns:
            RecordResult with success status and file path
        """
        script = self.clc_path / "scripts" / "record-heuristic.sh"

        if not script.exists():
            return RecordResult(
                success=False,
                file_path=None,
                message="record-heuristic.sh not found"
            )

        # Inherit current environment and add required vars
        # This ensures HOME, USER, and other critical vars are available
        env = os.environ.copy()
        env.update({
            "HEURISTIC_DOMAIN": domain,
            "HEURISTIC_RULE": rule,
            "HEURISTIC_EXPLANATION": explanation,
        })

        try:
            result = subprocess.run(
                ["bash", str(script)],
                capture_output=True,
                text=True,
                env=env,
                timeout=10
            )

            if result.returncode == 0:
                return RecordResult(
                    success=True,
                    file_path=result.stdout.strip(),
                    message="Heuristic recorded"
                )
            else:
                return RecordResult(
                    success=False,
                    file_path=None,
                    message=result.stderr or "Recording failed"
                )

        except subprocess.TimeoutExpired:
            return RecordResult(
                success=False,
                file_path=None,
                message="Recording timed out"
            )

    def record_failure(
        self,
        title: str,
        root_cause: str,
        lesson: str,
        domain: str = "general"
    ) -> RecordResult:
        """
        Record a failure analysis.

        Args:
            title: Brief failure description
            root_cause: Why it failed
            lesson: What was learned
            domain: Domain category

        Returns:
            RecordResult with success status
        """
        script = self.clc_path / "scripts" / "record-failure.sh"

        if not script.exists():
            return RecordResult(
                success=False,
                file_path=None,
                message="record-failure.sh not found"
            )

        # Inherit current environment and add required vars
        env = os.environ.copy()
        env.update({
            "FAILURE_TITLE": title,
            "FAILURE_ROOT_CAUSE": root_cause,
            "FAILURE_LESSON": lesson,
            "FAILURE_DOMAIN": domain,
        })

        try:
            result = subprocess.run(
                ["bash", str(script)],
                capture_output=True,
                text=True,
                env=env,
                timeout=10
            )

            return RecordResult(
                success=result.returncode == 0,
                file_path=result.stdout.strip() if result.returncode == 0 else None,
                message="Failure recorded" if result.returncode == 0 else result.stderr
            )

        except subprocess.TimeoutExpired:
            return RecordResult(
                success=False,
                file_path=None,
                message="Recording timed out"
            )

    def get_subagent_config(self, persona: str) -> Dict[str, Any]:
        """
        Get native subagent configuration for a CLC persona.

        Args:
            persona: CLC persona name (researcher, architect, creative, skeptic)

        Returns:
            Dict with subagent_type and configuration
        """
        try:
            from native_subagents import get_subagent_config
            return get_subagent_config(persona)
        except ImportError:
            return {
                "subagent_type": "general-purpose",
                "description": f"CLC persona: {persona}",
                "error": "native_subagents.py not available"
            }

    def get_party_subagents(self, party: str) -> List[Dict[str, Any]]:
        """
        Get subagent configurations for a party.

        Args:
            party: Party name from parties.yaml

        Returns:
            List of subagent configurations
        """
        try:
            from native_subagents import get_party_subagents
            return get_party_subagents(party)
        except ImportError:
            return []

    def health_check(self) -> Dict[str, Any]:
        """
        Check CLC backend health.

        Returns:
            Dict with component status
        """
        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "clc_path": str(self.clc_path),
            "components": {}
        }

        # Check key files
        checks = {
            "query.py": self.clc_path / "query" / "query.py",
            "progressive.py": self.clc_path / "query" / "progressive.py",
            "native_subagents.py": self.clc_path / "agents" / "native_subagents.py",
            "golden_rules": self.clc_path / "golden-rules" / "RULES.md",
            "record_heuristic": self.clc_path / "scripts" / "record-heuristic.sh",
            "record_failure": self.clc_path / "scripts" / "record-failure.sh"
        }

        for name, path in checks.items():
            status["components"][name] = {
                "exists": path.exists(),
                "path": str(path)
            }

        status["healthy"] = all(c["exists"] for c in status["components"].values())
        return status


def main():
    """CLI interface for CLC backend."""
    import argparse

    parser = argparse.ArgumentParser(description="CLC Backend Interface")
    parser.add_argument("--query", action="store_true", help="Query CLC context")
    parser.add_argument("--progressive", type=str, help="Progressive query for task")
    parser.add_argument("--domain", type=str, help="Domain filter")
    parser.add_argument("--tier", type=str, default="recommended", help="Loading tier")
    parser.add_argument("--health", action="store_true", help="Health check")
    parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    clc = CLCBackend()

    if args.health:
        result = clc.health_check()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"CLC Backend Health Check")
            print("=" * 40)
            print(f"Path: {result['clc_path']}")
            print(f"Healthy: {'✓' if result['healthy'] else '✗'}")
            print("\nComponents:")
            for name, status in result["components"].items():
                icon = "✓" if status["exists"] else "✗"
                print(f"  {icon} {name}")
        return

    if args.progressive:
        result = clc.progressive_query(
            task=args.progressive,
            domain=args.domain,
            tier=args.tier
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(result["context"])
        return

    if args.query:
        result = clc.query(domain=args.domain)
        if args.json:
            print(json.dumps({
                "context": result.context,
                "golden_rules": result.golden_rules,
                "heuristics": result.heuristics,
                "metadata": result.metadata
            }, indent=2))
        else:
            print(result.context)
        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
