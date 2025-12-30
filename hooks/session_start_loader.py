#!/usr/bin/env python3
"""
SessionStart Hook: Automatically load CLC context on session start.

This hook replaces the manual "check in" requirement by automatically:
1. Loading critical rules from .claude/rules/ (native integration)
2. Invoking query.py --context for heuristics/learnings
3. Writing context to CLAUDE_ENV_FILE for session persistence

The goal is FULLY AUTOMATIC context loading - agents no longer need
to explicitly query CLC at the start of each session.

Implementation Date: December 29, 2025
GitHub Issue: #63
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def get_clc_path() -> Path:
    """Get the CLC installation path."""
    return Path.home() / ".claude" / "clc"


def query_clc_context(domain: str = None) -> dict:
    """
    Query CLC for relevant context.

    Returns:
        dict with keys: golden_rules, heuristics, recent_learnings, experiments
    """
    clc_path = get_clc_path()
    query_script = clc_path / "query" / "query.py"

    if not query_script.exists():
        return {"error": "CLC query.py not found"}

    try:
        cmd = [sys.executable, str(query_script), "--context", "--format", "json"]
        if domain:
            cmd.extend(["--domain", domain])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(clc_path)
        )

        if result.returncode == 0:
            # Try to parse JSON output
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # Return raw output if not JSON
                return {"raw_context": result.stdout}
        else:
            return {"error": result.stderr or "Query failed"}

    except subprocess.TimeoutExpired:
        return {"error": "CLC query timed out"}
    except Exception as e:
        return {"error": str(e)}


def detect_project_domain(project_dir: str) -> Optional[str]:
    """
    Detect the domain based on project files.

    Returns domain string or None if no specific domain detected.
    For monorepos with multiple project types, uses priority ordering
    to return the most relevant domain.
    """
    if not project_dir:
        return None

    project_path = Path(project_dir)

    # Domain detection heuristics with priority (lower index = higher priority)
    # Priority: database > backend > frontend > infrastructure > testing
    # Rationale: More specific domains take precedence
    domain_indicators = [
        ("database", ["schema.prisma", "migrations", "alembic"]),
        ("backend", ["requirements.txt", "pyproject.toml", "go.mod", "Cargo.toml"]),
        ("frontend", ["package.json", "tsconfig.json", "vite.config.ts", "next.config.js"]),
        ("infrastructure", ["terraform", "docker-compose.yml", "Dockerfile", "k8s"]),
        ("testing", ["tests", "test", "__tests__", "cypress", "playwright"]),
    ]

    detected_domains = []
    for domain, indicators in domain_indicators:
        for indicator in indicators:
            if (project_path / indicator).exists():
                detected_domains.append(domain)
                break  # Found this domain, check next

    # Return highest priority detected domain, or None
    return detected_domains[0] if detected_domains else None


def format_context_for_injection(context: dict) -> str:
    """
    Format CLC context for injection into the session.

    This creates a concise summary suitable for context injection.
    """
    lines = []
    lines.append("# CLC Context (Auto-Loaded)")
    lines.append(f"# Session: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    # Golden Rules (always include)
    if "golden_rules" in context:
        lines.append("## Active Golden Rules")
        for rule in context.get("golden_rules", [])[:5]:  # Limit to top 5
            lines.append(f"- {rule}")
        lines.append("")

    # Relevant Heuristics
    if "heuristics" in context:
        lines.append("## Relevant Heuristics")
        for h in context.get("heuristics", [])[:3]:  # Limit to top 3
            lines.append(f"- {h.get('rule', h) if isinstance(h, dict) else h}")
        lines.append("")

    # Recent Learnings
    if "recent_learnings" in context:
        lines.append("## Recent Learnings")
        for l in context.get("recent_learnings", [])[:3]:  # Limit to top 3
            lines.append(f"- {l}")
        lines.append("")

    # Active Experiments
    if "experiments" in context and context["experiments"]:
        lines.append("## Active Experiments")
        for exp in context["experiments"]:
            lines.append(f"- {exp}")
        lines.append("")

    return "\n".join(lines)


def write_to_env_file(content: str, env_file: str) -> bool:
    """
    Write context to CLAUDE_ENV_FILE for session persistence.

    Returns True on success.
    """
    if not env_file:
        return False

    try:
        with open(env_file, "a", encoding="utf-8") as f:
            f.write(f"\n# CLC_CONTEXT_START\n")
            f.write(f"CLC_CONTEXT_LOADED=true\n")
            f.write(f"CLC_LOAD_TIME={datetime.now(timezone.utc).isoformat()}\n")
            f.write(f"# CLC_CONTEXT_END\n")
        return True
    except Exception:
        return False


def main():
    """
    Main hook entry point.

    Reads hook input from stdin, processes it, and outputs result.
    """
    # Read hook input
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # No input or invalid JSON - still proceed
        hook_input = {}

    # Get environment variables
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    env_file = os.environ.get("CLAUDE_ENV_FILE", "")
    is_remote = os.environ.get("CLAUDE_CODE_REMOTE", "false") == "true"

    # Detect domain from project
    domain = detect_project_domain(project_dir)

    # Query CLC for context
    context = query_clc_context(domain=domain)

    # Format context for injection
    formatted_context = format_context_for_injection(context)

    # Write to env file for persistence
    env_written = write_to_env_file(formatted_context, env_file)

    # Output hook result
    result = {
        "continue": True,  # Always continue - this is informational
        "outputToStdout": formatted_context,  # Show context in session
        "metadata": {
            "domain_detected": domain,
            "env_file_written": env_written,
            "context_loaded": "error" not in context,
            "is_remote": is_remote,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
