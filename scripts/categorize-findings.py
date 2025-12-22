#!/usr/bin/env python3
"""Categorize review findings by severity based on priority badges.

Usage: categorize-findings.py <pr_number>

Exit codes:
  0 = success
  1 = error (usage, API failure, etc.)
"""

import json
import os
import re
import subprocess
import sys
from typing import Any

SEVERITY_PATTERNS = {
    'critical': [
        r'!\[critical\]',
        r'!\[security-critical\]',
        r'\*\*critical\*\*',
    ],
    'high': [
        r'!\[high\]',
        r'!\[security-high\]',
        r'\*\*high\*\*',
    ],
    'medium': [
        r'!\[medium\]',
        r'\*\*medium\*\*',
    ],
    'low': [
        r'!\[low\]',
        r'\*\*low\*\*',
        r'nit:',
        r'nitpick:',
        r'minor:',
    ],
}


def get_repo_info() -> tuple[str, str]:
    """Get owner and repo from GITHUB_REPOSITORY env or git remote."""
    if 'GITHUB_REPOSITORY' in os.environ:
        parts = os.environ['GITHUB_REPOSITORY'].split('/')
        return parts[0], parts[1]

    # Fall back to git remote
    result = subprocess.run(
        ['git', 'remote', 'get-url', 'origin'],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        # Parse github.com:owner/repo or github.com/owner/repo
        match = re.search(r'github\.com[:/]([^/]+)/([^/.]+)', result.stdout)
        if match:
            return match.group(1), match.group(2)

    raise RuntimeError('Could not determine repository owner/name')


def get_review_threads(owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
    """Fetch all review threads for a PR using GraphQL."""
    query = '''
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          reviewThreads(first: 100) {
            nodes {
              id
              isResolved
              isOutdated
              path
              line
              comments(first: 1) {
                nodes {
                  body
                  author { login }
                }
              }
            }
          }
        }
      }
    }
    '''

    result = subprocess.run(
        [
            'gh', 'api', 'graphql',
            '-f', f'query={query}',
            '-f', f'owner={owner}',
            '-f', f'repo={repo}',
            '-F', f'pr={pr_number}'
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f'GraphQL query failed: {result.stderr}')

    data = json.loads(result.stdout)
    threads = data.get('data', {}).get('repository', {}).get('pullRequest', {}).get('reviewThreads', {}).get('nodes', [])
    return threads or []


def categorize_comment(body: str) -> str:
    """Determine severity of a comment based on content patterns."""
    body_lower = body.lower()
    for severity, patterns in SEVERITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, body_lower):
                return severity
    return 'medium'  # Default to medium if no pattern matched


def main(pr_number: int) -> int:
    """Main entry point."""
    try:
        owner, repo = get_repo_info()
    except RuntimeError as e:
        print(f'Error: {e}', file=sys.stderr)
        return 1

    try:
        threads = get_review_threads(owner, repo, pr_number)
    except RuntimeError as e:
        print(f'Error: {e}', file=sys.stderr)
        return 1

    # Only process unresolved threads
    unresolved = [t for t in threads if not t.get('isResolved', True)]

    categorized: dict[str, list[dict[str, Any]]] = {
        'critical': [],
        'high': [],
        'medium': [],
        'low': []
    }

    for thread in unresolved:
        comments = thread.get('comments', {}).get('nodes', [])
        if not comments:
            continue

        first_comment = comments[0]
        body = first_comment.get('body', '')
        severity = categorize_comment(body)

        categorized[severity].append({
            'id': thread.get('id'),
            'path': thread.get('path', 'N/A'),
            'line': thread.get('line'),
            'outdated': thread.get('isOutdated', False),
            'author': first_comment.get('author', {}).get('login', 'unknown'),
            'preview': body[:100] + '...' if len(body) > 100 else body
        })

    output = {
        'summary': {s: len(v) for s, v in categorized.items()},
        'blocking': categorized['critical'] + categorized['high'],
        'non_blocking': categorized['medium'] + categorized['low'],
        'counts': {
            'total_unresolved': len(unresolved),
            'blocking_count': len(categorized['critical']) + len(categorized['high']),
            'non_blocking_count': len(categorized['medium']) + len(categorized['low'])
        },
        'details': categorized
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: categorize-findings.py <pr_number>', file=sys.stderr)
        sys.exit(1)

    try:
        pr_num = int(sys.argv[1])
    except ValueError:
        print('Error: PR number must be an integer', file=sys.stderr)
        sys.exit(1)

    sys.exit(main(pr_num))
