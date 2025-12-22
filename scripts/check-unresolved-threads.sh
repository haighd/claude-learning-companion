#!/bin/bash
set -euo pipefail

# Check for unresolved review threads on a PR
# Usage: ./check-unresolved-threads.sh <PR_NUMBER>
# Exit codes: 0 = all resolved, 1 = unresolved threads exist

PR_NUMBER="${1:-}"

if [ -z "$PR_NUMBER" ]; then
    echo "Usage: $0 <PR_NUMBER>" >&2
    exit 2
fi

# Query for unresolved review threads using gh pr view
UNRESOLVED=$(gh pr view "$PR_NUMBER" --json reviewThreads -q '[.reviewThreads[] | select(.isResolved | not)] | length')

if [ "$UNRESOLVED" -gt 0 ]; then
    echo "::error::Found $UNRESOLVED unresolved review thread(s) on PR #$PR_NUMBER"
    echo ""
    echo "Please resolve all review threads before running CI."
    exit 1
fi

echo "All review threads are resolved. CI can proceed."
exit 0
