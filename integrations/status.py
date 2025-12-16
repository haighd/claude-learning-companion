#!/usr/bin/env python3
"""
CLC Integration Status

Shows status of MCP servers and installed plugins.

Usage:
    python status.py              # Show all integrations
    python status.py --mcp        # Show MCP servers only
    python status.py --plugins    # Show plugins only
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# Integration paths (symlinked)
INTEGRATIONS_PATH = Path(__file__).parent
MCP_CONFIGS_PATH = INTEGRATIONS_PATH / "mcp-configs"
PLUGINS_PATH = INTEGRATIONS_PATH / "plugins"

def get_mcp_servers():
    """Get configured MCP servers."""
    servers_file = MCP_CONFIGS_PATH / "servers.json"
    if not servers_file.exists():
        return []

    try:
        with open(servers_file) as f:
            data = json.load(f)

        servers = []
        for name, config in data.get("servers", {}).items():
            servers.append({
                "name": name,
                "type": config.get("type", "unknown"),
                "command": config.get("command", ""),
                "args": config.get("args", [])
            })
        return servers
    except Exception as e:
        return []

def get_installed_plugins():
    """Get installed plugins."""
    plugins_file = PLUGINS_PATH / "installed_plugins.json"
    if not plugins_file.exists():
        return []

    try:
        with open(plugins_file) as f:
            data = json.load(f)

        plugins = []
        for plugin_id, installs in data.get("plugins", {}).items():
            if installs:
                install = installs[0]  # Get first install
                plugins.append({
                    "id": plugin_id,
                    "version": install.get("version", "unknown"),
                    "scope": install.get("scope", "unknown"),
                    "installed_at": install.get("installedAt", "unknown")
                })
        return plugins
    except Exception as e:
        return []

def format_date(iso_date):
    """Format ISO date to readable format."""
    try:
        dt = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d")
    except:
        return iso_date

def print_mcp_status():
    """Print MCP server status."""
    servers = get_mcp_servers()
    print(f"MCP Servers ({len(servers)} configured):")
    print("-" * 50)
    if servers:
        for s in servers:
            print(f"  {s['name']}")
            print(f"    Type: {s['type']}")
            print(f"    Command: {s['command']} {' '.join(s['args'][:2])}...")
            print()
    else:
        print("  No servers configured")
    print()

def print_plugin_status():
    """Print plugin status."""
    plugins = get_installed_plugins()
    print(f"Installed Plugins ({len(plugins)}):")
    print("-" * 50)
    if plugins:
        for p in plugins:
            print(f"  {p['id']}")
            print(f"    Version: {p['version']}")
            print(f"    Scope: {p['scope']}")
            print(f"    Installed: {format_date(p['installed_at'])}")
            print()
    else:
        print("  No plugins installed")
    print()

def main():
    parser = argparse.ArgumentParser(description="CLC Integration Status")
    parser.add_argument("--mcp", action="store_true", help="Show MCP servers only")
    parser.add_argument("--plugins", action="store_true", help="Show plugins only")

    args = parser.parse_args()

    print()
    print("=" * 50)
    print("CLC Integration Status")
    print("=" * 50)
    print()

    if args.mcp:
        print_mcp_status()
    elif args.plugins:
        print_plugin_status()
    else:
        print_mcp_status()
        print_plugin_status()

    # Show paths
    print("Paths:")
    print("-" * 50)
    print(f"  MCP Configs: {MCP_CONFIGS_PATH.resolve()}")
    print(f"  Plugins: {PLUGINS_PATH.resolve()}")
    print()

if __name__ == "__main__":
    main()
