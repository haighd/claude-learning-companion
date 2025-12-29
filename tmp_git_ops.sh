#!/bin/bash
cd /Users/danhaight/.claude/clc
OUTPUT_FILE="/Users/danhaight/.claude/clc/tmp_git_output.txt"

echo "=== Git Status ===" > "$OUTPUT_FILE"
git status >> "$OUTPUT_FILE" 2>&1

echo "" >> "$OUTPUT_FILE"
echo "=== Current Branch ===" >> "$OUTPUT_FILE"
git branch --show-current >> "$OUTPUT_FILE" 2>&1

echo "" >> "$OUTPUT_FILE"
echo "=== Recent Commits ===" >> "$OUTPUT_FILE"
git log --oneline -5 >> "$OUTPUT_FILE" 2>&1

echo "" >> "$OUTPUT_FILE"
echo "=== Push Attempt ===" >> "$OUTPUT_FILE"
git push -u origin sprint/2025-12-29 >> "$OUTPUT_FILE" 2>&1

echo "" >> "$OUTPUT_FILE"
echo "=== Done ===" >> "$OUTPUT_FILE"
