#!/bin/bash
set -euo pipefail

# Bulk resolve review threads on a PR
# Usage: ./resolve-threads.sh <PR_NUMBER> [--outdated-only] [--dry-run]

PR_NUMBER="${1:-}"

if [ -z "$PR_NUMBER" ]; then
    echo "Usage: $0 <PR_NUMBER> [--outdated-only] [--dry-run]" >&2
    exit 2
fi
shift

OUTDATED_ONLY=false
DRY_RUN=false

# Parse flags
for arg in "$@"; do
    case "$arg" in
        --outdated-only) OUTDATED_ONLY=true ;;
        --dry-run) DRY_RUN=true ;;
        *)
            echo "Unknown option: $arg" >&2
            echo "Usage: $0 <PR_NUMBER> [--outdated-only] [--dry-run]" >&2
            exit 2
            ;;
    esac
done

# Fetch unresolved thread IDs using gh pr view
echo "Fetching unresolved threads for PR #$PR_NUMBER..."

JQ_FILTER='[.reviewThreads[] | select(.isResolved == false'
if [ "$OUTDATED_ONLY" = true ]; then
    JQ_FILTER+=' and .isOutdated == true'
fi
JQ_FILTER+=')]'

THREADS_JSON=$(gh pr view "$PR_NUMBER" --json reviewThreads --jq "$JQ_FILTER")
THREAD_IDS=$(echo "$THREADS_JSON" | jq -r '.[].id')

# Fix: Use proper empty check instead of grep -c which returns 1 on no match
if [ -z "$THREAD_IDS" ]; then
    COUNT=0
else
    COUNT=$(echo "$THREAD_IDS" | wc -l | tr -d ' ')
fi

if [ "$COUNT" -eq 0 ]; then
    echo "No unresolved threads found."
    exit 0
fi

echo "Found $COUNT unresolved thread(s)."

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would resolve the following threads:"
    echo "$THREAD_IDS"
    exit 0
fi

# Resolve each thread
# Note: Using process substitution to avoid subshell issue where counters wouldn't persist
RESOLVED=0
FAILED=0

while IFS= read -r THREAD_ID; do
    [ -z "$THREAD_ID" ] && continue
    echo "Resolving thread: $THREAD_ID"
    RESULT=$(gh api graphql -f query='
      mutation($threadId: ID!) {
        resolveReviewThread(input: {threadId: $threadId}) {
          thread { isResolved }
        }
      }' -f threadId="$THREAD_ID" 2>&1)

    if echo "$RESULT" | grep -q '"isResolved":true'; then
        RESOLVED=$((RESOLVED + 1))
    else
        echo "  Failed to resolve: $RESULT"
        FAILED=$((FAILED + 1))
    fi
done < <(echo "$THREAD_IDS")

echo ""
echo "Summary: $RESOLVED resolved, $FAILED failed"

# Exit with 1 if any failures, 0 otherwise (exit codes are 0-255)
if [ "$FAILED" -gt 0 ]; then
    exit 1
else
    exit 0
fi
