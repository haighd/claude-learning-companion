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

# Check for opening YAML frontmatter delimiter (allow trailing whitespace)
if ! head -1 "$CHECKPOINT_PATH" | grep -qE "^--- *$"; then
    echo "ERROR: Missing opening YAML frontmatter delimiter"
    exit 1
fi

# Check for closing YAML frontmatter delimiter (must appear after line 1)
# Using awk to only find delimiter in first few lines (true YAML frontmatter),
# not a horizontal rule later in the document.
if ! awk 'NR > 1 && /^--- *$/ { found=1; exit } END { exit !found }' "$CHECKPOINT_PATH"; then
    echo "ERROR: Missing closing YAML frontmatter delimiter"
    exit 1
fi

# Check for required sections
REQUIRED_SECTIONS=(
    "## What Changed"
    "## Next Steps"
)

for section in "${REQUIRED_SECTIONS[@]}"; do
    # Check for section presence and content using awk. This verifies that:
    # 1. The section header exists (matching with optional leading whitespace)
    # 2. There is at least one non-empty, non-header line under the section
    if ! awk -v s="$section" '
        $0 ~ "^ *" s {in_section=1; next}
        in_section && $0 ~ /^ *## / {exit}
        in_section && NF > 0 {found_content=1; exit}
        END {exit !found_content}
    ' "$CHECKPOINT_PATH"; then
        echo "ERROR: Missing required section or content for: $section"
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
# Extract YAML frontmatter: awk reads line-by-line; if line 1 matches "---"
# (with optional trailing whitespace), enter in_yaml mode and skip that line;
# while in_yaml, print lines until we hit another "---" (the closing delimiter),
# then exit. This isolates the frontmatter block between the two "---" delimiters.
FRONTMATTER=$(awk 'NR==1 && $0 ~ /^--- *$/{in_yaml=1; next} in_yaml && $0 ~ /^--- *$/{exit} in_yaml{print}' "$CHECKPOINT_PATH")

# Use a single awk command to validate all fields at once for efficiency.
# This avoids spawning multiple grep processes in a loop.
MISSING_FIELDS=$(awk '
    BEGIN {
        required["created:"] = 1
        required["trigger:"] = 1
        required["project:"] = 1
    }
    /^ *created: *[^[:space:]]/ { delete required["created:"] }
    /^ *trigger: *[^[:space:]]/ { delete required["trigger:"] }
    /^ *project: *[^[:space:]]/ { delete required["project:"] }
    END {
        for (field in required) { print field }
    }
' <<< "$FRONTMATTER")

if [ -n "$MISSING_FIELDS" ]; then
    echo "ERROR: Missing required frontmatter fields or values:"
    echo "$MISSING_FIELDS" | while IFS= read -r field; do
        echo "  - $field"
    done
    exit 1
fi

# All checks passed
echo "OK: Checkpoint verified: $CHECKPOINT_PATH"
echo "  Size: $(wc -c < "$CHECKPOINT_PATH") bytes"
echo "  Sections: $(grep -c '^## ' "$CHECKPOINT_PATH") found"

exit 0
