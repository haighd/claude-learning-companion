#!/bin/bash
# Start graph sync background service
# Synchronizes SQLite data to FalkorDB every 5 minutes

cd ~/.claude/clc || exit 1

# Optional: customize sync interval (default: 300 seconds = 5 minutes)
# python3 -m memory.graph_sync_service --interval 600

python3 -m memory.graph_sync_service
