#!/bin/bash
# Bulk resolve review threads on a PR
# Usage: ./resolve-threads.sh <PR_NUMBER> [--outdated-only] [--dry-run]

PR_NUMBER="$1"
REPO="${GITHUB_REPOSITORY:-haighd/claude-learning-companion}"
OUTDATED_ONLY=false
DRY_RUN=false

# Parse flags
shift
while [ $# -gt 0 ]; do
    case "$1" in
        --outdated-only) OUTDATED_ONLY=true ;;
        --dry-run) DRY_RUN=true ;;
    esac
    shift
done

if [ -z "$PR_NUMBER" ]; then
    echo "Usage: $0 <PR_NUMBER> [--outdated-only] [--dry-run]"
    exit 2
fi

# Fetch unresolved thread IDs
echo "Fetching unresolved threads for PR #$PR_NUMBER..."

THREADS=$(gh api graphql -f query='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          isOutdated
          comments(first: 1) {
            nodes { body path line }
          }
        }
      }
    }
  }
}' -f owner="${REPO%/*}" -f repo="${REPO#*/}" -F pr="$PR_NUMBER")

# Filter threads
if [ "$OUTDATED_ONLY" = true ]; then
    THREAD_IDS=$(echo "$THREADS" | jq -r '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false and .isOutdated == true) | .id')
else
    THREAD_IDS=$(echo "$THREADS" | jq -r '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false) | .id')
fi

COUNT=$(echo "$THREAD_IDS" | grep -c . || echo 0)

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
RESOLVED=0
FAILED=0

for THREAD_ID in $THREAD_IDS; do
    echo "Resolving thread: $THREAD_ID"
    RESULT=$(gh api graphql -f query='
      mutation($threadId: ID!) {
        resolveReviewThread(input: {threadId: $threadId}) {
          thread { isResolved }
        }
      }' -f threadId="$THREAD_ID" 2>&1)

    if echo "$RESULT" | grep -q '"isResolved":true'; then
        ((RESOLVED++))
    else
        echo "  Failed to resolve: $RESULT"
        ((FAILED++))
    fi
done

echo ""
echo "Summary: $RESOLVED resolved, $FAILED failed"
exit $FAILED
