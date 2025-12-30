# CLC Framework Analysis: Opportunities for Improvement & Deprecation

**Date:** December 29, 2025
**Context:** Claude Code v2.0.76 released, industry best practices evolving
**Scope:** Comprehensive analysis of CLC vs. native Claude Code features

---

## Executive Summary

This research identifies **8 features to potentially deprecate/supersede**, **12 improvements to existing CLC features**, and **6 new additions** to enhance Claude Code agent performance and context management. The analysis is based on:
- Complete CLC framework inventory (17+ core systems)
- Claude Code 2.0.76 changelog and recent features
- Anthropic engineering best practices
- Community SME recommendations (December 2025)

---

## 1. Features to SUPERSEDE (CLC → Native Claude Code)

### 1.1 Session Memory via CLAUDE.md → `.claude/rules/` Directory

| CLC Current | Native Alternative | Recommendation |
|-------------|-------------------|----------------|
| Query system loads all golden rules at startup | `.claude/rules/` auto-loads all `.md` files | **HYBRID** - critical rules to native, keep progressive for rest |

**Why HYBRID (not full migration):**
- Native `.claude/rules/` auto-loads ALL files (no progressive disclosure)
- Full migration would lose CLC's on-demand loading capability
- Confidence scoring and learning cycle remain in CLC

**⚠️ CONFLICT RESOLVED:** See Section 7.1 for detailed resolution.

**Migration Path (REVISED):**
1. Export ONLY 3-5 critical bootstrapping rules to `.claude/rules/` (~100 tokens)
2. Keep detailed heuristics and domain rules in CLC query system (progressive)
3. DO NOT deprecate query.py - improve it instead (see Section 2.1)
4. Native rules serve as "always-on" safety net; CLC provides depth

### 1.2 Session Logging → Native Session Recording

| CLC Current | Native Alternative | Recommendation |
|-------------|-------------------|----------------|
| `hooks/session_logger_hook.py` | Built-in `~/.claude/projects/*.jsonl` | **PARTIALLY DEPRECATE** |

**Why Supersede:**
- Claude Code now natively records all sessions to JSONL
- Named sessions with `/rename` command
- Resume with `/resume <n>` or `--resume` flag
- `/search` command for natural language session search

**What to Keep:**
- CLC's rich metadata extraction (outcome classification, learning capture)
- Dashboard integration for visual browsing
- The hook should transform data, not duplicate logging

### 1.3 Agent Personas → Native Subagents

| CLC Current | Native Alternative | Recommendation |
|-------------|-------------------|----------------|
| `agents/researcher.md`, `architect.md`, etc. | `.claude/agents/` with YAML frontmatter | **MIGRATE FORMAT** |

**Why Supersede:**
- Native subagents support isolated context heaps
- Tool permissions per agent (`allowed-tools`)
- First-class `/agents` command for management
- 90.2% improvement on complex tasks with native parallel execution

**Migration Path:**
1. Convert CLC agent personas to native `.claude/agents/` format
2. Add YAML frontmatter with `allowed-tools`, `model` specification
3. Keep philosophical approaches but leverage native orchestration

### 1.4 Basic MCP Server → Native Plugin System

| CLC Current | Native Alternative | Recommendation |
|-------------|-------------------|----------------|
| `mcp/clc_server.py` custom MCP | Plugin system with marketplace | **CONVERT TO MULTIPLE PLUGINS** |

**⚠️ CONFLICT RESOLVED:** See Section 7.5 - Split into multiple plugins for progressive loading

**Why Multiple Plugins (not single bundle):**
- Single plugin would load ALL CLC features (defeats progressive disclosure)
- Multiple plugins allow users to install only what they need
- Each plugin can have internal skill-based progressive disclosure

**Migration Path (REVISED):**
1. Package CLC as FOUR distributable plugins:
   - `clc-core` - query system, learning capture (~500 tokens)
   - `clc-dashboard` - visual monitoring (installs on demand)
   - `clc-swarm` - multi-agent coordination (installs on demand)
   - `clc-experiments` - isolation system (installs on demand)
2. Use `/plugin` commands for installation
3. Core plugin auto-installs; others prompted when features used

### 1.5 Manual Context Loading → Native Progressive Disclosure

| CLC Current | Native Alternative | Recommendation |
|-------------|-------------------|----------------|
| CLC query loads all tiers at startup | Skills system with 3-level progressive disclosure | **ADOPT PATTERN** |

**Key Insight from Anthropic:**
- Tier 1: Metadata only (~50 tokens) - name/description
- Tier 2: Full instructions when triggered
- Tier 3: Dynamic resources on demand

CLC currently loads Tier 1 (500 tokens) + Tier 2 (2-5k tokens) upfront. This is inefficient.

---

## 2. Improvements to EXISTING CLC Features

### 2.1 Query System Performance

**Current State:** `query/query.py` loads 500+ tokens at minimum (golden rules)

**Recommended Improvements:**

| Improvement | Impact | Priority |
|-------------|--------|----------|
| Implement progressive disclosure (metadata → full content) | -60% startup tokens | HIGH |
| Lazy-load heuristics only when domain-matched | -40% query tokens | HIGH |
| Cache frequently accessed patterns in memory | -20% latency | MEDIUM |
| Add `/context`-style token accounting | Visibility | MEDIUM |

**Implementation:**
```python
# Before: Load all golden rules at startup
# After: Load only rule names/descriptions, full text on demand

class ProgressiveQuery:
    def get_metadata(self):
        """Return ~50 tokens: rule names only"""

    def get_full_rule(self, rule_id):
        """Load full text only when needed"""
```

### 2.2 CLAUDE.md Size Optimization

**Current State:** CLC's CLAUDE.md instructions are ~400+ lines

**Industry Best Practice:** 100-200 lines maximum (62% token reduction possible)

**Recommended Changes:**

1. **Move to `.claude/rules/` directory:**
   - Split monolithic CLAUDE.md into focused rule files
   - Use conditional rules with `paths` frontmatter

2. **Remove redundant instructions:**
   - "Always query CLC before acting" - **NOW FULLY AUTOMATIC via SessionStart hook** (see Section 7.7)
   - Detailed examples - move to skills that load on demand
   - Code review guidelines - delegate to linter/reviewer tools

3. **Target Structure:**
   ```
   .claude/rules/
   ├── 01-core-protocol.md          # ~50 lines
   ├── 02-pr-workflow.md            # ~30 lines
   ├── 03-learning-capture.md       # ~20 lines
   └── 04-escalation.md             # ~20 lines
   ```

### 2.3 Hooks System Modernization

**Current State:** CLC uses custom hook implementations in `hooks/learning-loop/`

**Claude Code 2.0.76 Hook Features:**
- `PreCompact` hook - handle pre-compaction logic
- `SubagentStop` hook - evaluate task completion
- `PermissionRequest` hook - auto-approve/deny
- Custom timeouts per hook
- `PreToolUse` can modify tool inputs

**Recommended Improvements:**

| Hook | Current CLC | Improvement |
|------|-------------|-------------|
| `pre_tool_learning.py` | Pre-execution setup | Use native `PreToolUse` with input modification |
| `post_tool_learning.py` | Outcome capture | Add `SubagentStop` for subagent outcomes |
| (missing) | N/A | Add `PreCompact` to save context before compaction |
| (missing) | N/A | Add `PermissionRequest` for auto-approvals |

**New Hook: PreCompact**
```json
{
  "hooks": {
    "PreCompact": [{
      "matcher": "auto",
      "command": ["python3", "~/.claude/clc/hooks/pre_compact.py"],
      "timeout": 30000
    }]
  }
}
```

### 2.4 Dashboard Token Display

**Current State:** Dashboard shows learning analytics but not token usage

**Recommended Addition:**
- Add `/context`-style token breakdown to dashboard
- Show per-session token consumption trends
- Identify MCP servers consuming context
- Alert when approaching compaction threshold

### 2.5 Outcome Detection Enhancement

**Current State:** `outcome_detection.py` classifies success/failure

**Known Issue:** False positives when analyzing code containing error handling (per recent heuristic)

**Improvements:**
1. Expand false positive patterns for code analysis scenarios
2. Increase context window from 60 to 100 chars
3. Check success signals FIRST before failure patterns
4. Add confidence scoring with threshold tuning

### 2.6 Experiment Isolation Enhancement

**Current State:** Git worktrees + database cloning

**Recommended Addition:**
- Add `/experiment` slash command (native pattern)
- Auto-cleanup stale experiments after N days
- Experiment metrics tracking (success rate, duration)
- One-click merge from dashboard

---

## 3. Context Window Management Improvements

### 3.1 Implement Aggressive `/clear` Strategy

**Problem:** CLC maintains persistent context that grows over time

**Solution:**
```python
# Add to SessionStart hook
def check_context_freshness():
    if session_tokens > 30000:
        suggest_clear()
    if time_since_task_switch > 300:  # 5 minutes
        auto_clear_prompt()
```

### 3.2 MCP Server Management

**Current State:** CLC doesn't track MCP server token impact

**Recommended:**
1. Add MCP audit to dashboard (which servers, token cost each)
2. Auto-disable unused servers after N sessions
3. Warn when MCP tools exceed 5% of context

### 3.3 Subagent Delegation for Context Isolation

**Current State:** CLC conductor/executor handles multi-agent

**⚠️ CONFLICT RESOLVED:** See Section 7.4 - Subagents write to CLC BEFORE returning summaries

**Enhancement:**
- Leverage native isolated context heaps per subagent
- Only return summaries to main context (not full outputs)
- Use `run_in_background=true` by default (already a golden rule)
- **CRITICAL:** Subagent must record learnings BEFORE returning summary:
  ```python
  # Subagent completion pattern
  def complete_subagent_task():
      # 1. Do the work
      result = execute_task()

      # 2. Capture learnings BEFORE summarizing
      if result.has_failure:
          record_failure(result.failure_details)  # Full context preserved
      if result.has_heuristic:
          record_heuristic(result.pattern)

      # 3. Return summary (references learning IDs)
      return Summary(
          outcome=result.outcome,
          learning_refs=result.recorded_ids  # Dashboard can link to full details
      )
  ```

### 3.4 Pre-Compaction Hook

**New Feature:** Save critical context before auto-compaction

```python
# hooks/pre_compact.py
def handle_pre_compact():
    # Extract key decisions made this session
    # Save to memory/sessions/ for persistence
    # Summarize active tasks to PLAN.md
    pass
```

### 3.5 Token Budget Enforcement

**Current State:** No token budget tracking

**Recommended:**
- Set per-session token targets
- Dashboard warning at 50% capacity
- Auto-suggest compaction at 75%
- Hard recommend `/clear` at 90%

---

## 4. Additions to Improve Claude Code Performance

### 4.1 Checkpoint Pattern Integration

**Source:** Anthropic engineering best practice

**Implementation:**
- Before major operations, auto-save state to `checkpoints/`
- Include: architectural decisions, active tasks, file ownership
- Enable "resume from checkpoint" after compaction/crash

### 4.2 Claude Diary Pattern

**Source:** Zhang et al. 2025 research

**Structure:**
```
Generator → produces reasoning trajectories
Reflector → extracts lessons from successes/failures
Curator → integrates insights into structured updates
```

CLC already has pieces of this. Formalize into:
1. SessionEnd hook triggers Reflector
2. Reflector outputs to `memory/sessions/`
3. Curator (weekly cron) consolidates to heuristics

### 4.3 Native Skills Adoption

**Current:** CLC uses custom slash commands

**⚠️ CONFLICT RESOLVED:** See Section 7.3 - Skills are INTERFACE, query.py is BACKEND

**Recommended:** Convert to native skills format:
```
~/.claude/skills/
├── clc-query/
│   └── SKILL.md       # INVOKES query.py (doesn't replace it)
├── clc-record/
│   └── SKILL.md       # INVOKES record-*.sh scripts
└── clc-escalate/
    └── SKILL.md       # INVOKES CEO inbox creation
```

**Architecture:**
```
Native Skill (INTERFACE)     →    CLC Backend (IMPLEMENTATION)
─────────────────────────────────────────────────────────────
clc-query/SKILL.md          →    query/query.py
clc-record/SKILL.md         →    scripts/record-*.sh
clc-escalate/SKILL.md       →    ceo-inbox/ workflow
```

Benefits:
- Progressive disclosure (skill metadata ~50 tokens, full load on invocation)
- Native `/skills` command visibility
- YAML frontmatter for configuration
- query.py improvements (Section 2.1) still apply

### 4.4 Parallel Agent Farm

**Source:** Community best practice

**Pattern:**
- Complex tasks spawn 3-5 specialized subagents
- Each agent has isolated context + specific focus
- Only final summaries return to coordinator
- 4x+ speedup on research/analysis tasks

CLC conductor already supports this - document and promote the pattern.

### 4.5 Context Poisoning Prevention

**Problem:** Bad Claude outputs remain in history, affect subsequent turns

**Solution:**
- Add "context health" scoring in dashboard
- Identify turns with errors/corrections
- Suggest `/clear` after significant mistakes
- Auto-flag conversations with >3 corrections

### 4.6 Episodic Memory Formalization

**Source:** Community blog (blog.fsck.com)

**Key Insight:** "Code comments explain what, documentation explains how, episodic memory preserves WHY"

**Implementation:**
- Capture trade-offs discussed during sessions
- Store alternatives considered but rejected
- Preserve reasoning, not just outcomes

CLC's failure analysis partially does this - extend to ALL significant decisions.

---

## 5. Additions to Improve Context Window Management

### 5.1 Token Accounting Dashboard Tab

**New Dashboard Feature (Dual Data Source - see Section 7.7):**

**Real-Time (via PostToolUse hooks):**
- Per-tool token breakdown
- In-session alerts at 50%/75%/90% thresholds
- Live context health scoring

**Historical (via session JSONL parsing):**
- Trend charts over time
- Project comparison analytics
- Decay analysis (session degradation patterns)
- Alerts and recommendations based on patterns

### 5.2 Smart Compaction Summary

**Enhancement to PreCompact:**
- Extract and preserve:
  - Active task state
  - Key decisions made
  - Files being modified
  - Pending questions
- Store in `checkpoints/pre-compact/`
- Auto-restore after compaction

### 5.3 Conversation Scope Enforcement

**New Hook:**
```python
# hooks/scope_enforcer.py
def check_topic_drift():
    """Detect when conversation drifts to new topic"""
    if topic_similarity < 0.5:
        suggest_new_session()
```

### 5.4 MCP Server Auditor

**New Script:**
```bash
# scripts/audit-mcp-servers.sh
# List all enabled MCP servers
# Show token cost per server
# Recommend disabling unused servers
```

### 5.5 Progressive Rule Loading

**Restructure Golden Rules:**
```
Level 1 (always loaded): 3-5 critical rules (~100 tokens)
Level 2 (task-matched): Domain-specific rules (~200 tokens)
Level 3 (on-demand): Full documentation (unlimited)
```

### 5.6 Session Length Monitoring

**New Metric:**
- Track effective session length before degradation
- Industry average: 10-20 minutes autonomous work
- Alert when approaching typical degradation point
- Suggest checkpointing before decline

---

## 6. Implementation Priority Matrix (REVISED)

| Category | Item | Priority | Effort | Token Impact |
|----------|------|----------|--------|--------------|
| **Hybrid** | Critical rules → `.claude/rules/` (3-5 only) | HIGH | Low | -100 tokens |
| **Improve** | Query progressive disclosure | HIGH | High | -60% startup |
| **Improve** | CLAUDE.md size optimization | HIGH | Low | -62% possible |
| **Migrate** | Agent personas → native subagents | HIGH | Medium | -200 tokens |
| **Add** | Native skills (interface to query.py) | HIGH | Medium | Progressive |
| **Improve** | PreCompact hook addition | MEDIUM | Low | Preservation |
| **Improve** | Outcome detection fixes | MEDIUM | Low | Accuracy |
| **Add** | Token accounting dashboard | HIGH | Medium | Visibility |
| **Add** | Checkpoint pattern | HIGH | Medium | Recovery |
| **Add** | Claude Diary pattern | MEDIUM | High | Quality |
| **Context** | `/clear` strategy automation | HIGH | Low | -50% waste |
| **Context** | Subagent learning-before-summary pattern | HIGH | Medium | Learning preserved |
| **Context** | MCP server auditor | MEDIUM | Low | -5% per server |
| **Plugin** | Multi-plugin architecture (4 plugins) | MEDIUM | High | Modular install |
| **Context** | Session scope enforcer | LOW | Medium | Drift prevention |

**Note:** "Supersede" changed to "Hybrid" for golden rules - full migration would conflict with progressive loading.

---

## 7. CONFLICTS AND RESOLUTIONS

### 7.1 MAJOR CONFLICT: Golden Rules Migration vs. Progressive Loading

| Recommendation | Section | Problem |
|----------------|---------|---------|
| Migrate to `.claude/rules/` | 1.1 | Native rules auto-load ALL files |
| Progressive 3-tier loading | 5.5 | Requires on-demand loading |

**These are INCOMPATIBLE.** Native `.claude/rules/` has no progressive disclosure.

**RESOLUTION:**
- **CHOSEN APPROACH:** Hybrid model
- Put 3-5 critical rules in `.claude/rules/` (~100 tokens, always loaded)
- Keep detailed heuristics/domain rules in CLC query system (progressive)
- This preserves both native integration AND progressive disclosure

### 7.2 MAJOR CONFLICT: Query.py Deprecation vs. Improvement

| Recommendation | Section |
|----------------|---------|
| Deprecate query.py golden rules loading | 1.1 |
| Improve query.py with progressive disclosure | 2.1 |

**Cannot deprecate AND improve the same component.**

**RESOLUTION:**
- **CHOSEN APPROACH:** IMPROVE query.py, do NOT deprecate
- Native systems lack: confidence scoring, learning cycle, heuristics DB
- Query.py remains CLC's core - enhance it with progressive disclosure
- Native `.claude/rules/` used ONLY for critical bootstrapping rules

### 7.3 MAJOR CONFLICT: Skills vs. Query.py

| Recommendation | Section |
|----------------|---------|
| Convert to native skills (`clc-query/SKILL.md`) | 4.3 |
| Improve query.py | 2.1 |

**RESOLUTION:**
- **Skills are INTERFACE, query.py is BACKEND**
- `clc-query` skill INVOKES query.py (doesn't replace it)
- Progressive disclosure: skill metadata loads first, query.py runs on invocation
- Clarify this relationship in implementation

### 7.4 MAJOR CONFLICT: Subagent Summaries vs. Learning Capture

| Recommendation | Section | Problem |
|----------------|---------|---------|
| Return only summaries from subagents | 3.3 | Loses detailed learning data |
| Capture learnings (failures, heuristics) | CLC core | Needs full context |

**RESOLUTION:**
- **Subagents write to CLC BEFORE returning summary**
- Pattern:
  1. Subagent completes work
  2. Subagent calls CLC recording scripts (failure/heuristic)
  3. Subagent returns summary to main context
- Include `learning_refs` in summary pointing to CLC records

### 7.5 MAJOR CONFLICT: Plugin Bundling vs. Progressive Disclosure

| Recommendation | Section |
|----------------|---------|
| Package CLC as plugin | 1.4 |
| Progressive disclosure pattern | 1.5, 4.3 |

**RESOLUTION:**
- **Package CLC as MULTIPLE smaller plugins:**
  - `clc-core` - query system, learning capture (minimal footprint)
  - `clc-dashboard` - visual monitoring (loads on demand)
  - `clc-swarm` - multi-agent coordination (loads on demand)
  - `clc-experiments` - isolation system (loads on demand)
- Each plugin supports internal skill-based progressive disclosure

### 7.6 Minor Ambiguities (RESOLVED via User Input)

| Ambiguity | Resolution | User Decision |
|-----------|------------|---------------|
| Which CLAUDE.md to optimize? | **BOTH** global (~/.claude/CLAUDE.md) AND project (~/.claude/clc/CLAUDE.md) to 100-200 lines each | Confirmed |
| Hook enforcement vs. explicit query | **FULLY AUTOMATIC** - SessionStart hook loads full CLC context; remove need for explicit 'check in' | Confirmed |
| `/clear` at 90% vs PreCompact at 95% | PreCompact triggers on AUTO-compaction; `/clear` is manual recommendation | N/A (no conflict) |
| Dashboard token data source | **BOTH APPROACHES** - Hooks for real-time alerts + session parsing for historical trends | Confirmed |
| CEO escalation after migration | **HYBRID** - CEO decisions become native skills that write to ceo-inbox/ but are invokable via /skills | Confirmed |

### 7.7 Detailed Resolutions

**CLAUDE.md Optimization (Both Files):**
- Global `~/.claude/CLAUDE.md`: Split PR workflow, CLC protocol into `.claude/rules/`
- Project `~/.claude/clc/CLAUDE.md`: Move detailed examples to skills, keep core instructions
- Target: 100-200 lines each (currently ~400+ combined)

**Query Enforcement (Fully Automatic):**
- Remove mandatory "check in" command from protocol
- SessionStart hook automatically:
  1. Loads critical rules from `.claude/rules/` (native)
  2. Invokes `query.py --context` for heuristics/learnings
  3. Injects relevant context based on project detection
- Agent no longer needs to explicitly query - it happens automatically
- **Impact:** Update golden rule #1 from "always query CLC" to "CLC auto-loads on session start"

**Token Tracking (Dual Approach):**
```
┌─────────────────────────────────────────────────────────────┐
│ REAL-TIME (Hooks)                                           │
│ PostToolUse hook → capture token counts → SQLite            │
│ Enables: in-session alerts, per-tool breakdown              │
├─────────────────────────────────────────────────────────────┤
│ HISTORICAL (Session Parsing)                                │
│ Cron job → parse JSONL files → aggregate to SQLite          │
│ Enables: trend charts, project comparisons, decay analysis  │
└─────────────────────────────────────────────────────────────┘
```

**CEO Escalation (Hybrid with Native):**
- Create `clc-escalate/SKILL.md` as native skill
- Skill invokes ceo-inbox/ workflow (writes files, notifies)
- Visible via `/skills` command
- Maintains backward compatibility with existing ceo-inbox/ structure

---

## 8. Risks and Considerations

### 8.1 Migration Risks
- Native `.claude/rules/` lacks CLC's confidence scoring
- Native subagents don't persist learning (stateless)
- Plugin marketplace not mature for enterprise distribution

### 8.2 Backward Compatibility
- Existing CLC users have workflows built on current system
- Migration should be incremental, not breaking
- Provide fallback/hybrid mode during transition

### 8.3 Feature Gaps in Native Claude Code
- No structured learning cycle (TRY→BREAK→ANALYZE→LEARN→NEXT)
- No CEO escalation inbox
- No confidence-scored heuristics
- No failure analysis templates
- No experiment tracking with metrics

These remain **CLC value-adds** that should be enhanced, not deprecated.

---

## 9. Next Steps

1. **Immediate (This Week):**
   - Implement PreCompact hook
   - Add token accounting to dashboard
   - Create `.claude/rules/` migration script

2. **Short-Term (Next 2 Weeks):**
   - Convert agent personas to native format
   - Implement progressive disclosure in query system
   - Add MCP server auditor

3. **Medium-Term (Next Month):**
   - Package CLC as distributable plugin
   - Implement Claude Diary pattern
   - Add checkpoint pattern integration

4. **Long-Term (Next Quarter):**
   - Full native integration where applicable
   - Community plugin marketplace presence
   - Enterprise deployment patterns

---

## Sources

### Official Anthropic
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Agent Skills Progressive Disclosure](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

### Claude Code Documentation
- [Hooks Configuration](https://claude.com/blog/how-to-configure-hooks)
- [Context Management](https://claude.com/blog/context-management)
- [Memory Management](https://code.claude.com/docs/en/memory)

### Community SME
- [CLAUDE.md Best Practices](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [Token Optimization Guide](https://medium.com/@jpranav97/stop-wasting-tokens-how-to-optimize-claude-code-context-by-60-bfad6fd477e5)
- [Claude Diary Pattern](https://rlancemartin.github.io/2025/12/01/claude_diary/)
- [Episodic Memory](https://blog.fsck.com/2025/10/23/episodic-memory/)
- [400K Lines Management](https://blockhead.consulting/blog/claude_code_workflow_july_2025)
