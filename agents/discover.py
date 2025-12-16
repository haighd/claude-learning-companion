#!/usr/bin/env python3
"""
Agent Discovery for CLC

Lists and searches available agents from the catalog.

Usage:
    python discover.py                    # List all categories
    python discover.py --list             # List all agents
    python discover.py --category NAME    # List agents in category
    python discover.py --search KEYWORD   # Search agents by keyword
    python discover.py --agent NAME       # Show agent details
"""

import os
import sys
import argparse
from pathlib import Path

# Agent catalog location (symlinked from ~/.claude/agents)
CATALOG_PATH = Path(__file__).parent / "catalog"
PERSONA_PATH = Path(__file__).parent

def get_categories():
    """Get all agent categories."""
    if not CATALOG_PATH.exists():
        return []

    categories = []
    for item in sorted(CATALOG_PATH.iterdir()):
        if item.is_dir() and not item.name.startswith('.'):
            agent_count = len(list(item.glob("*.md")))
            categories.append({
                "name": item.name,
                "path": str(item),
                "count": agent_count
            })
    return categories

def get_agents_in_category(category_name):
    """Get all agents in a category."""
    category_path = CATALOG_PATH / category_name
    if not category_path.exists():
        return []

    agents = []
    for agent_file in sorted(category_path.glob("*.md")):
        if agent_file.name != "README.md":
            agents.append({
                "name": agent_file.stem,
                "path": str(agent_file),
                "category": category_name
            })
    return agents

def get_all_agents():
    """Get all agents from all categories."""
    all_agents = []
    for category in get_categories():
        agents = get_agents_in_category(category["name"])
        all_agents.extend(agents)
    return all_agents

def search_agents(keyword):
    """Search agents by keyword in name."""
    keyword = keyword.lower()
    matching = []
    for agent in get_all_agents():
        if keyword in agent["name"].lower():
            matching.append(agent)
    return matching

def get_agent_content(agent_name):
    """Get the content of an agent file."""
    for category in get_categories():
        agent_path = CATALOG_PATH / category["name"] / f"{agent_name}.md"
        if agent_path.exists():
            return agent_path.read_text()
    return None

def get_persona_agents():
    """Get CLC persona agents (architect, creative, researcher, skeptic)."""
    personas = []
    for item in PERSONA_PATH.iterdir():
        if item.is_dir() and item.name not in ['catalog', '__pycache__']:
            prompt_file = item / "PROMPT.md"
            if prompt_file.exists():
                personas.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "persona"
                })
    return personas

def main():
    parser = argparse.ArgumentParser(description="CLC Agent Discovery")
    parser.add_argument("--list", action="store_true", help="List all agents")
    parser.add_argument("--category", type=str, help="List agents in category")
    parser.add_argument("--search", type=str, help="Search agents by keyword")
    parser.add_argument("--agent", type=str, help="Show agent details")
    parser.add_argument("--personas", action="store_true", help="List CLC persona agents")

    args = parser.parse_args()

    if args.personas:
        personas = get_persona_agents()
        print(f"CLC Persona Agents ({len(personas)}):")
        print("-" * 40)
        for p in personas:
            print(f"  {p['name']}")
        return

    if args.agent:
        content = get_agent_content(args.agent)
        if content:
            print(content)
        else:
            print(f"Agent '{args.agent}' not found")
            sys.exit(1)
        return

    if args.search:
        results = search_agents(args.search)
        print(f"Search results for '{args.search}' ({len(results)} found):")
        print("-" * 40)
        for agent in results:
            print(f"  {agent['category']}/{agent['name']}")
        return

    if args.category:
        agents = get_agents_in_category(args.category)
        if agents:
            print(f"Agents in {args.category} ({len(agents)}):")
            print("-" * 40)
            for agent in agents:
                print(f"  {agent['name']}")
        else:
            print(f"Category '{args.category}' not found or empty")
        return

    if args.list:
        all_agents = get_all_agents()
        print(f"All Agents ({len(all_agents)}):")
        print("-" * 40)
        current_category = None
        for agent in all_agents:
            if agent["category"] != current_category:
                current_category = agent["category"]
                print(f"\n[{current_category}]")
            print(f"  {agent['name']}")
        return

    # Default: show categories
    categories = get_categories()
    total = sum(c["count"] for c in categories)
    print(f"Agent Catalog ({total} agents in {len(categories)} categories):")
    print("-" * 40)
    for cat in categories:
        print(f"  {cat['name']}: {cat['count']} agents")
    print("")
    print("Usage:")
    print("  --list              List all agents")
    print("  --category NAME     List agents in category")
    print("  --search KEYWORD    Search agents")
    print("  --agent NAME        Show agent details")
    print("  --personas          List CLC persona agents")

if __name__ == "__main__":
    main()
