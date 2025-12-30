#!/usr/bin/env python3
"""
Native Subagent Interface for CLC

Maps CLC agent personas to Claude Code's native Task tool subagent_types.
Enables seamless integration between CLC party definitions and native orchestration.

Issue: #68
Implementation Date: December 29, 2025

Usage:
    from native_subagents import get_subagent_config, get_party_subagents

    # Get native subagent config for a CLC persona
    config = get_subagent_config("researcher")

    # Get subagent configs for a party
    party_configs = get_party_subagents("code-review")

Environment Variables:
    CLC_PATH: Override the default CLC installation path (~/.claude/clc)
"""

import argparse
import json
import os
import re
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any


# Mapping from CLC personas to native Claude Code subagent_types
PERSONA_TO_NATIVE = {
    "researcher": {
        "subagent_type": "research-analyst",
        "fallback_types": ["web-search-researcher", "codebase-analyzer"],
        "description": "Deep investigation, evidence gathering, documentation",
        "native_description": "Expert research analyst for comprehensive information gathering"
    },
    "architect": {
        "subagent_type": "microservices-architect",
        "fallback_types": ["architect-reviewer", "fullstack-developer"],
        "description": "System design, structure evaluation, scalability",
        "native_description": "Distributed systems architect for scalable design"
    },
    "creative": {
        "subagent_type": "general-purpose",
        "fallback_types": ["frontend-developer", "ui-designer"],
        "description": "Novel solutions, breaking conventional thinking",
        "native_description": "General-purpose agent for creative problem solving",
        "prompt_modifier": "Think creatively and propose unconventional approaches."
    },
    "skeptic": {
        "subagent_type": "code-reviewer",
        "fallback_types": ["security-auditor", "qa-expert", "penetration-tester"],
        "description": "Validation, finding flaws, edge cases",
        "native_description": "Expert code reviewer for quality and security"
    }
}

# Task-specific subagent recommendations
TASK_TO_SUBAGENT = {
    "debug": "debugger",
    "test": "test-automator",
    "security": "security-engineer",
    "performance": "performance-engineer",
    "database": "database-administrator",
    "api": "api-designer",
    "frontend": "frontend-developer",
    "backend": "backend-developer",
    "devops": "devops-engineer",
    "documentation": "technical-writer",
    "refactor": "refactoring-specialist"
}

# Pre-compiled regex patterns for task matching (performance optimization)
# Compiled once at module load rather than on each function call
_TASK_PATTERNS = {
    key: re.compile(rf'\b{re.escape(key)}\b')
    for key in TASK_TO_SUBAGENT.keys()
}


def get_clc_path() -> Path:
    """Get CLC installation path.

    Can be overridden via CLC_PATH environment variable.
    """
    if env_path := os.environ.get("CLC_PATH"):
        return Path(env_path)
    return Path.home() / ".claude" / "clc"


def load_parties() -> Dict:
    """Load party definitions from parties.yaml."""
    parties_file = get_clc_path() / "agents" / "parties.yaml"
    if parties_file.exists():
        try:
            with open(parties_file) as f:
                data = yaml.safe_load(f)
                return data.get("parties", {}) if isinstance(data, dict) else {}
        except yaml.YAMLError as e:
            # Log error but don't crash - return empty
            print(f"Warning: Failed to parse parties.yaml: {e}", file=sys.stderr)
            return {}
    return {}


def load_persona(persona_name: str) -> Optional[Dict]:
    """Load a CLC persona personality file."""
    persona_dir = get_clc_path() / "agents" / persona_name
    personality_file = persona_dir / "personality.md"

    if not personality_file.exists():
        return None

    content = personality_file.read_text()

    # Extract key sections from markdown
    persona = {
        "name": persona_name,
        "content": content,
        "triggers": [],
        "behaviors": []
    }

    # Extract triggers and behaviors sections
    # Use startswith for more robust header matching
    current_section = None
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## Triggers"):
            current_section = "triggers"
            continue
        elif stripped.startswith("## Behaviors") or stripped.startswith("## Key Behaviors"):
            current_section = "behaviors"
            continue
        elif stripped.startswith("##"):
            current_section = None
            continue

        if current_section and line.strip().startswith("-"):
            item = line.strip().lstrip("- ").strip('"')
            persona[current_section].append(item)

    return persona


def get_subagent_config(persona_name: str) -> Dict[str, Any]:
    """
    Get native subagent configuration for a CLC persona.

    Returns:
        Dict with subagent_type, description, and optional prompt_modifier
    """
    if persona_name not in PERSONA_TO_NATIVE:
        return {
            "subagent_type": "general-purpose",
            "description": f"CLC persona: {persona_name}",
            "prompt_modifier": None
        }

    mapping = PERSONA_TO_NATIVE[persona_name]
    persona = load_persona(persona_name)

    config = {
        "subagent_type": mapping["subagent_type"],
        "fallback_types": mapping["fallback_types"],
        "description": mapping["description"],
        "native_description": mapping["native_description"],
        "prompt_modifier": mapping.get("prompt_modifier"),
        "clc_persona": persona
    }

    return config


def get_party_subagents(party_name: str) -> List[Dict[str, Any]]:
    """
    Get native subagent configurations for all agents in a party.

    Returns:
        List of subagent configs with workflow information
    """
    parties = load_parties()

    if party_name not in parties:
        return []

    party = parties[party_name]
    agents = party.get("agents", [])
    workflow = party.get("workflow", "sequential")
    lead = party.get("lead")

    configs = []
    for agent_name in agents:
        config = get_subagent_config(agent_name)
        config["is_lead"] = agent_name == lead
        config["workflow"] = workflow
        config["party"] = party_name
        configs.append(config)

    return configs


def get_task_subagent(task_keyword: str) -> str:
    """
    Get recommended native subagent_type for a task keyword.

    Args:
        task_keyword: Task type like "debug", "test", "security"

    Returns:
        Native subagent_type string
    """
    keyword = task_keyword.lower()

    # Direct match
    if keyword in TASK_TO_SUBAGENT:
        return TASK_TO_SUBAGENT[keyword]

    # Partial match with word boundary using pre-compiled patterns
    # Uses regex word boundaries to prevent 'end' matching 'frontend'
    for key, pattern in _TASK_PATTERNS.items():
        if pattern.search(keyword):
            return TASK_TO_SUBAGENT[key]

    return "general-purpose"


def build_task_prompt(
    persona_name: str,
    task_description: str,
    include_clc_context: bool = True
) -> str:
    """
    Build a Task tool prompt incorporating CLC persona guidance.

    Args:
        persona_name: CLC persona name
        task_description: The task to perform
        include_clc_context: Whether to include CLC query instruction

    Returns:
        Formatted prompt for Task tool
    """
    config = get_subagent_config(persona_name)

    parts = []

    # Add persona context
    parts.append(f"## Role: {persona_name.capitalize()}")
    parts.append(config["description"])

    # Add prompt modifier if present
    if config.get("prompt_modifier"):
        parts.append(f"\n{config['prompt_modifier']}")

    # Add CLC context instruction
    if include_clc_context:
        parts.append("\n## Before Acting")
        parts.append("Query CLC for relevant context:")
        parts.append("```bash")
        parts.append("~/.claude/clc/query/query.py --context")
        parts.append("```")

    # Add task
    parts.append(f"\n## Task")
    parts.append(task_description)

    return "\n".join(parts)


def list_available_personas() -> List[Dict]:
    """List all available CLC personas with native mappings."""
    personas = []
    for name, mapping in PERSONA_TO_NATIVE.items():
        persona = load_persona(name)
        personas.append({
            "name": name,
            "native_type": mapping["subagent_type"],
            "fallbacks": mapping["fallback_types"],
            "description": mapping["description"],
            "loaded": persona is not None
        })
    return personas


def list_available_parties() -> List[Dict]:
    """List all available parties with agent compositions."""
    parties = load_parties()
    result = []
    for name, config in parties.items():
        result.append({
            "name": name,
            "description": config.get("description", ""),
            "lead": config.get("lead"),
            "agents": config.get("agents", []),
            "workflow": config.get("workflow", "sequential"),
            "triggers": config.get("triggers", [])
        })
    return result


def main():
    """CLI interface for native subagent discovery."""
    parser = argparse.ArgumentParser(description="CLC Native Subagent Interface")
    parser.add_argument("--personas", action="store_true", help="List all personas")
    parser.add_argument("--parties", action="store_true", help="List all parties")
    parser.add_argument("--persona", type=str, help="Get config for persona")
    parser.add_argument("--party", type=str, help="Get subagents for party")
    parser.add_argument("--task", type=str, help="Get subagent for task keyword")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.personas:
        personas = list_available_personas()
        if args.json:
            print(json.dumps(personas, indent=2))
        else:
            print("CLC Personas → Native Subagents:")
            print("-" * 50)
            for p in personas:
                status = "✓" if p["loaded"] else "✗"
                print(f"  {status} {p['name']:12} → {p['native_type']}")
        return

    if args.parties:
        parties = list_available_parties()
        if args.json:
            print(json.dumps(parties, indent=2))
        else:
            print("Available Parties:")
            print("-" * 50)
            for p in parties:
                agents = " → ".join(p["agents"])
                print(f"  {p['name']:15} [{p['workflow']}]")
                print(f"    Lead: {p['lead']}, Agents: {agents}")
        return

    if args.persona:
        config = get_subagent_config(args.persona)
        if args.json:
            # Remove non-serializable content
            config.pop("clc_persona", None)
            print(json.dumps(config, indent=2))
        else:
            print(f"Persona: {args.persona}")
            print(f"Native Type: {config['subagent_type']}")
            print(f"Fallbacks: {', '.join(config.get('fallback_types', []))}")
            print(f"Description: {config['description']}")
        return

    if args.party:
        configs = get_party_subagents(args.party)
        if args.json:
            for c in configs:
                c.pop("clc_persona", None)
            print(json.dumps(configs, indent=2))
        else:
            print(f"Party: {args.party}")
            print("-" * 40)
            for c in configs:
                lead = " (LEAD)" if c.get("is_lead") else ""
                print(f"  {c['subagent_type']}{lead}")
        return

    if args.task:
        subagent = get_task_subagent(args.task)
        if args.json:
            print(json.dumps({"task": args.task, "subagent_type": subagent}))
        else:
            print(f"Task '{args.task}' → {subagent}")
        return

    # Default: show summary
    personas = list_available_personas()
    parties = list_available_parties()
    print("CLC Native Subagent Interface")
    print("=" * 50)
    print(f"Personas: {len(personas)} mapped to native types")
    print(f"Parties:  {len(parties)} team compositions")
    print(f"Tasks:    {len(TASK_TO_SUBAGENT)} task→subagent mappings")
    print("")
    print("Usage:")
    print("  --personas     List persona mappings")
    print("  --parties      List party compositions")
    print("  --persona X    Get config for persona X")
    print("  --party X      Get subagents for party X")
    print("  --task X       Get subagent for task keyword X")


if __name__ == "__main__":
    main()
