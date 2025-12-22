#!/bin/bash
# Check for unresolved review threads on a PR
# Usage: ./check-unresolved-threads.sh <PR_NUMBER>
# Exit codes: 0 = all resolved, 1 = unresolved threads exist

PR_NUMBER="$1"
REPO="${GITHUB_REPOSITORY:-haighd/claude-learning-companion}"

if [ -z "$PR_NUMBER" ]; then
    echo "Usage: $0 <PR_NUMBER>"
    exit 2
fi

# Query for unresolved review threads
UNRESOLVED=$(gh api graphql -f query='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          isResolved
          comments(first: 1) {
            nodes { body path }
          }
        }
      }
    }
  }
}' -f owner="${REPO%/*}" -f repo="${REPO#*/}" -F pr="$PR_NUMBER" \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length')

if [ "$UNRESOLVED" -gt 0 ]; then
    echo "::error::Found $UNRESOLVED unresolved review thread(s)"
    echo ""
    echo "Please resolve all review threads before running CI."
    echo "Use: gh api graphql to resolve threads, or address the feedback first."
    exit 1
fi

echo "All review threads are resolved. CI can proceed."
exit 0
