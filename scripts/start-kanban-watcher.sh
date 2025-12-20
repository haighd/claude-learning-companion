#!/bin/bash
# Start Kanban automation watcher for CEO inbox monitoring
# This script runs the kanban_watcher.py service

cd ~/.claude/clc || exit 1
python3 -m watcher.kanban_watcher
