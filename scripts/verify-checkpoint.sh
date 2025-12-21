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

# Check minimum content length.
# This is a heuristic to flag accidentally trivial checkpoints; the default
# threshold is 200 bytes but can be overridden via CHECKPOINT_MIN_BYTES.
MIN_CONTENT_BYTES="${CHECKPOINT_MIN_BYTES:-200}"
CONTENT_LENGTH=$(wc -c < "$CHECKPOINT_PATH")
if [ "$CONTENT_LENGTH" -lt "$MIN_CONTENT_BYTES" ]; then
    echo "WARNING: Checkpoint content suspiciously short ($CONTENT_LENGTH bytes; minimum $MIN_CONTENT_BYTES)"
fi

# Verify frontmatter has required fields
# Extract YAML frontmatter: awk reads line-by-line; if line 1 is exactly "---",
# enter in_yaml mode and skip that line; while in_yaml, print lines until we
# hit another "---" (the closing delimiter), then exit. This isolates the
# frontmatter block between the two "---" delimiters.
FRONTMATTER=$(awk 'NR==1 && $0=="---"{in_yaml=1; next} in_yaml && $0=="---"{exit} in_yaml{print}' "$CHECKPOINT_PATH")

REQUIRED_FIELDS=(
    "created:"
    "trigger:"
    "project:"
)

for field in "${REQUIRED_FIELDS[@]}"; do
    # Anchor to line start to avoid matching field name as substring in another value
    if ! echo "$FRONTMATTER" | grep -qE "^${field}"; then
        echo "WARNING: Missing recommended field: $field"
    fi
done

# All checks passed
echo "OK: Checkpoint verified: $CHECKPOINT_PATH"
echo "  Size: $(wc -c < "$CHECKPOINT_PATH") bytes"
echo "  Sections: $(grep -c '^## ' "$CHECKPOINT_PATH") found"

exit 0
