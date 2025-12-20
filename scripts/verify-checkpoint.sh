#!/bin/bash
# ABOUTME: Checkpoint verification script
# Validates that a checkpoint file exists and contains required sections

set -euo pipefail

CHECKPOINT_PATH="${1:-}"

if [ -z "$CHECKPOINT_PATH" ]; then
    echo "Usage: verify-checkpoint.sh <checkpoint-path>"
    exit 1
fi

# Check file exists
if [ ! -f "$CHECKPOINT_PATH" ]; then
    echo "ERROR: Checkpoint file does not exist: $CHECKPOINT_PATH"
    exit 1
fi

# Check file is not empty
if [ ! -s "$CHECKPOINT_PATH" ]; then
    echo "ERROR: Checkpoint file is empty: $CHECKPOINT_PATH"
    exit 1
fi

# Check for opening YAML frontmatter delimiter
if ! head -1 "$CHECKPOINT_PATH" | grep -q "^---$"; then
    echo "ERROR: Missing opening YAML frontmatter delimiter"
    exit 1
fi

# Check for closing YAML frontmatter delimiter (should appear after line 1)
if ! tail -n +2 "$CHECKPOINT_PATH" | grep -q "^---$"; then
    echo "ERROR: Missing closing YAML frontmatter delimiter"
    exit 1
fi

# Check for required sections
REQUIRED_SECTIONS=(
    "## What Changed"
    "## Next Steps"
)

for section in "${REQUIRED_SECTIONS[@]}"; do
    if ! grep -q "$section" "$CHECKPOINT_PATH"; then
        echo "ERROR: Missing required section: $section"
        exit 1
    fi
done

# Check minimum content length (at least 200 chars of actual content)
CONTENT_LENGTH=$(wc -c < "$CHECKPOINT_PATH")
if [ "$CONTENT_LENGTH" -lt 200 ]; then
    echo "WARNING: Checkpoint content suspiciously short ($CONTENT_LENGTH bytes)"
fi

# Verify frontmatter has required fields
REQUIRED_FIELDS=(
    "created:"
    "trigger:"
    "project:"
)

for field in "${REQUIRED_FIELDS[@]}"; do
    # Use word boundary or start-of-line to avoid false positives
    if ! grep -qE "(^|[[:space:]])$field" "$CHECKPOINT_PATH"; then
        echo "WARNING: Missing recommended field: $field"
    fi
done

# All checks passed
echo "OK: Checkpoint verified: $CHECKPOINT_PATH"
echo "  Size: $(wc -c < "$CHECKPOINT_PATH") bytes"
echo "  Sections: $(grep -c '^## ' "$CHECKPOINT_PATH") found"

exit 0
