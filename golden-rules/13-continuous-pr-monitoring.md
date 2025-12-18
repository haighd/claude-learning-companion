# Golden Rule 13: Continuous PR Monitoring and CEO-Only Merging

> Continuously poll PRs for reviewer feedback (every 2 minutes) and address ALL feedback before proceeding. Never run `/run-ci` until feedback exists AND is fully addressed. Never merge - only the CEO merges.

## Why

- Agents waste GitHub Actions credits by triggering CI prematurely (before reviewers respond)
- They frustrate the user by stopping to announce "awaiting feedback" instead of actively monitoring
- Feedback must be genuinely addressed (implemented or explained) before marking resolved - not just dismissed
- Merge authority belongs exclusively to the CEO; any exception requires explicit one-time permission that does not persist beyond that single action

## The Pattern

```bash
# 1. PUSH AND REQUEST REVIEW
git push origin feature-branch
gh pr comment <PR_NUMBER> --body "/gemini review"

# 2. POLL FOR FEEDBACK (every 2 minutes)
while true; do
    # Check for new review comments
    gh pr view <PR_NUMBER> --json reviews,comments

    # If feedback exists, address it
    # If no feedback yet, wait and check again
    sleep 120  # 2 minutes
done

# 3. ADDRESS ALL FEEDBACK (for each comment)
# Option A: Implement the suggested change
# Option B: Explain why you're not implementing it
# THEN mark as resolved (never before)

# 4. ONLY AFTER ALL FEEDBACK ADDRESSED
gh pr comment <PR_NUMBER> --body "/run-ci"

# 5. NEVER MERGE - wait for CEO
```

## Anti-Patterns (NEVER DO)

- Stopping to tell user "awaiting feedback" instead of actively monitoring
- Running `/run-ci` before reviewer feedback has been received
- Running `/run-ci` while feedback remains unaddressed
- Marking feedback as "resolved" without addressing it (implementation OR explanation)
- Merging a PR directly (unless CEO gives explicit one-time permission)
- Assuming one-time merge permission persists to future PRs

## Consequences of Unauthorized Merge

If an agent merges without explicit CEO permission:

1. **Immediately revert** the merge or unmerge the PR
2. **Record as failure** in CLC failure-analysis
3. **Escalate to CEO** via ceo-inbox
4. The agent has violated constitutional authority - this is a serious breach

## Enforcement

- Every PR workflow MUST include continuous polling (2-minute intervals)
- `/run-ci` MUST NOT be triggered until feedback is received AND addressed
- Merge authority is CEO-exclusive with no standing exceptions
- One-time merge permission expires immediately after use

---

**Promoted:** 2025-12-18
**Reason:** CEO identified agents wasting GitHub Actions credits by premature CI triggers, being passive instead of actively monitoring, and needing explicit merge authority boundaries.
**Status:** CONSTITUTIONAL - PR workflow constraint
