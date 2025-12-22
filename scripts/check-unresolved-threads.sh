#!/bin/bash
set -euo pipefail

# Check for unresolved review threads on a PR
# Usage: ./check-unresolved-threads.sh <PR_NUMBER>
# Exit codes: 0 = all resolved, 1 = unresolved threads exist, 2 = usage error

PR_NUMBER="${1:-}"

if [ -z "$PR_NUMBER" ]; then
    echo "Usage: $0 <PR_NUMBER>" >&2
    exit 2
fi

# Get repo info from environment or git remote
if [ -n "${GITHUB_REPOSITORY:-}" ]; then
    OWNER="${GITHUB_REPOSITORY%/*}"
    REPO="${GITHUB_REPOSITORY#*/}"
else
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
    if [[ "$REMOTE_URL" =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
        OWNER="${BASH_REMATCH[1]}"
        REPO="${BASH_REMATCH[2]}"
    else
        echo "Error: Could not determine repository owner/name" >&2
        exit 2
    fi
fi

# Query for unresolved review threads using GraphQL (gh pr view --json doesn't support reviewThreads)
QUERY='query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes { isResolved }
      }
    }
  }
}'

# Capture stdout and stderr separately to avoid corrupting JSON with warning messages
STDERR_FILE=$(mktemp)
RESULT=$(gh api graphql -f query="$QUERY" -f owner="$OWNER" -f repo="$REPO" -F pr="$PR_NUMBER" 2>"$STDERR_FILE") || {
    echo "Error: Failed to query review threads" >&2
    cat "$STDERR_FILE" >&2
    rm -f "$STDERR_FILE"
    exit 2
}
rm -f "$STDERR_FILE"

if ! echo "$RESULT" | grep -q '"reviewThreads"'; then
    echo "Error: GraphQL response missing reviewThreads data" >&2
    echo "$RESULT" >&2
    exit 2
fi

UNRESOLVED=$(echo "$RESULT" | jq '[.data.repository.pullRequest.reviewThreads.nodes // [] | .[] | select(.isResolved == false)] | length')

if [ "$UNRESOLVED" -gt 0 ]; then
    echo "::error::Found $UNRESOLVED unresolved review thread(s) on PR #$PR_NUMBER"
    echo ""
    echo "Please resolve all review threads before running CI."
    exit 1
fi

echo "All review threads are resolved. CI can proceed."
exit 0
