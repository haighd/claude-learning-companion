# Heuristics: framework

Generated from failures, successes, and observations in the **framework** domain.

---

## H-0: When native Claude Code features overlap with custom framework features, prefer HYBRID approaches: use native for bootstrapping/critical paths, keep custom for progressive disclosure and unique value-adds (confidence scoring, learning cycles, CEO escalation). Full migration loses progressive loading; full custom loses native integration benefits.

**Confidence**: 0.7
**Source**: observation
**Created**: 2025-12-29

Analysis of CLC vs Claude Code 2.0.76 revealed 5 major conflicts between 'migrate to native' and 'improve custom' recommendations. Resolution: (1) Golden rules: 3-5 critical to .claude/rules/, rest in progressive CLC query; (2) Query.py: improve, don't deprecate - native lacks confidence scoring; (3) Skills = interface, query.py = backend - complementary, not competing; (4) Subagents write to CLC BEFORE returning summaries; (5) Package as 4 plugins not 1 bundle. Hybrid approach preserves both native discoverability AND custom depth.

---

