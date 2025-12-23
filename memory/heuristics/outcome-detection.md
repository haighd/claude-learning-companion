# Heuristics: outcome-detection

Generated from failures, successes, and observations in the **outcome-detection** domain.

---

## H-0: When detecting task outcomes, check SUCCESS signals FIRST before failure patterns. This prevents false positives when subagents analyze code containing error handling, error types, or discussions of failures.

**Confidence**: 0.7
**Source**: observation
**Created**: 2025-12-23

The CLC outcome detection was marking successful code analysis tasks as failures because they discussed/quoted code containing error handling, exception types (TypeError:, ValueError:), or error-related patterns. Fix: (1) Check success signals first - if present, return success immediately; (2) Expand false positive patterns for code analysis scenarios; (3) Increase context window from 60 to 100 chars. This prevents 'Error detected' false positives on investigation reports that mention errors in their analysis.

---

