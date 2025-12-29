# Heuristics: ci-workflow

Generated from failures, successes, and observations in the **ci-workflow** domain.

---

## H-18: All reviewer feedback MUST be addressed PRIOR TO running CI tests. Never trigger /run-ci until all review threads are resolved. To do otherwise wastes GitHub Actions minutes. Always err on the side of feedback pending vs. feedback not given - wait for reviews to complete before proceeding to CI.

**Confidence**: 1.0
**Source**: observation
**Created**: 2025-12-27

Running CI before all reviewer feedback is addressed wastes compute. Reviews often catch issues that would cause CI to fail, or raise new issues after CI passes requiring another full cycle. Wait for reviewers to finish, address all threads, then run CI once.

---

