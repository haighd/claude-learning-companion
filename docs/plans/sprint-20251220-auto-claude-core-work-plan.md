# Sprint Work Plan: Auto-Claude Core
**Sprint Branch:** `sprint/auto-claude-core`
**Worktree:** `/Users/danhaight/.claude/clc-worktrees/sprint-20251220-auto-claude-core`
**Specialist:** backend-developer
**Created:** 2025-12-20

---

## Assigned Issues

### Issue #30 - [Auto-Claude] Wire up Self-Healing QA loops to hooks/conductor
- **Priority:** high
- **Effort:** high
- **Description:** Self-healing infrastructure exists but is disconnected from the execution flow. Need to integrate automatic failure recovery into the PostToolUse hook and conductor workflow.

### Issue #31 - [Auto-Claude] Install /experiment slash command
- **Priority:** medium
- **Effort:** low
- **Description:** Experiment management script exists but is not installed to user's Claude commands directory. Need to install and test.

---

## File Impact Analysis

| File Path | Change Type | Shared? | Risk |
|-----------|-------------|---------|------|
| `/Users/danhaight/.claude/hooks/learning-loop/post_tool_learning.py` | Modify | Yes (production hook) | High - Active production code |
| `/Users/danhaight/.claude/clc/conductor/conductor.py` | Modify | Yes (used by workflows) | Medium - Add optional healing integration |
| `/Users/danhaight/.claude/clc/query/self_healer.py` | Test/Verify | No | Low - Already complete |
| `/Users/danhaight/.claude/clc/query/failure_classifier.py` | Test/Verify | No | Low - Already complete |
| `/Users/danhaight/.claude/clc/query/fix_strategies.py` | Test/Verify | No | Low - Already complete |
| `/Users/danhaight/.claude/clc/config/self-healing.yaml` | Review/Tune | No | Low - Configuration only |
| `/Users/danhaight/.claude/clc/setup/install.sh` | Modify | Yes (setup script) | Medium - Add experiment command install |
| `/Users/danhaight/.claude/clc/setup/commands/experiment.md` | Exists | No | Low - Already exists |
| `/Users/danhaight/.claude/commands/experiment.md` | Create | No | Low - User command install |
| Database schema: `healing_attempts` table | Verify | Yes (shared DB) | Low - Already exists |

**Shared Files Requiring Coordination:**
- `post_tool_learning.py` - Used by all Claude sessions with hooks enabled
- `conductor.py` - Used by workflow orchestration
- `install.sh` - Used by setup/update process

---

## Implementation Steps

### Phase 1: Issue #31 - Install /experiment command (Quick Win)
**Estimated Time:** 30 minutes

1. **Review existing implementation**
   - ✓ `scripts/experiment.py` exists (15KB, fully implemented)
   - ✓ `setup/commands/experiment.md` exists (command definition)
   - ✓ Script handles: start, status, list, merge, discard, clean

2. **Modify install.sh**
   - Add experiment.md to commands installation
   - Ensure it's copied to `~/.claude/commands/experiment.md`
   - Test installation process

3. **Test command installation**
   - Run install.sh to verify command appears
   - Test basic command: `/experiment status`
   - Verify all subcommands work

4. **Documentation**
   - Update any setup docs if needed
   - Add to list of available commands

### Phase 2: Issue #30 - Wire Self-Healing to PostToolUse Hook
**Estimated Time:** 3-4 hours

#### Step 1: Hook Integration (1.5 hours)
1. **Modify post_tool_learning.py**
   - Line 52-60 already imports self_healer with fallback
   - Add healing trigger in failure detection section
   - After `determine_outcome()` detects failure, call `process_failure()`
   - Pass: error_output, tool_name, tool_input, exec_id (if available)

2. **Handle healing response**
   - If action="heal": Spawn Task with healing prompt
   - If action="escalate": Create CEO inbox item
   - Log healing attempt to database
   - Track healing attempts in session state

3. **Spawn healing agent**
   - Use Task tool with model from healing result
   - Pass generated healing prompt
   - Set run_in_background=True for async healing
   - Store healing agent task_id for outcome tracking

#### Step 2: Conductor Integration (1 hour)
1. **Add optional healing to conductor**
   - Import self_healer in conductor.py
   - Add healing config flag to workflow config
   - In `record_node_failure()`, optionally trigger healing
   - Link healing_attempt_id to node_execution via exec_id

2. **Healing workflow**
   - When node fails, check if healing is enabled
   - Call process_failure() with error details
   - If healing initiated, wait for result
   - Record healing outcome to node_executions

3. **Circuit breaker state management**
   - Ensure circuit breaker state persists across sessions
   - Already handled by healing-state.json
   - Verify state file location: `~/.claude/hooks/learning-loop/healing-state.json`

#### Step 3: Database Verification (30 minutes)
1. **Verify healing_attempts table**
   - ✓ Table exists with correct schema
   - ✓ Indexes present: failure_id, success, created_at, strategy
   - Test write/read operations

2. **Add exec_id foreign key (optional)**
   - Consider linking healing_attempts to node_executions
   - Migration script if schema change needed
   - Test referential integrity

#### Step 4: Testing & Validation (1 hour)
1. **Unit tests**
   - Test failure detection triggers healing
   - Test circuit breaker prevents cascading attempts
   - Test CEO escalation for unfixable errors
   - Test max attempts enforcement

2. **Integration tests**
   - Trigger a syntax error via Edit tool
   - Verify healing agent spawned
   - Verify healing attempt recorded to DB
   - Test successful healing closes the loop

3. **Edge cases**
   - Test with self-healing disabled
   - Test with circuit breaker open
   - Test with max attempts reached
   - Test with unfixable error patterns

### Phase 3: Configuration & Tuning (30 minutes)
1. **Review self-healing.yaml**
   - Verify pattern coverage
   - Add missing common failure types
   - Tune confidence thresholds
   - Review model escalation strategy

2. **Document integration points**
   - Hook trigger conditions
   - Conductor workflow integration
   - Configuration options
   - Troubleshooting guide

---

## Implementation Details

### PostToolUse Hook Integration

**Location:** `/Users/danhaight/.claude/hooks/learning-loop/post_tool_learning.py`

**Integration Point:** After failure detection (around line 180-220)

```python
# Existing failure detection
outcome, reason = determine_outcome(tool_output)

if outcome == "failure":
    # Existing failure recording...

    # NEW: Trigger self-healing if available
    if SELF_HEALING_AVAILABLE:
        tool_name = hook_input.get("tool_name")
        tool_input_params = hook_input.get("tool_input", {})
        error_output = content  # From tool_output

        healing_result = process_failure(
            error_output=error_output,
            tool_name=tool_name,
            tool_input=tool_input_params,
            exec_id=None  # Could link to workflow if available
        )

        if healing_result:
            if healing_result["action"] == "heal":
                # Spawn healing agent asynchronously
                # Note: Would need Task tool integration here
                pass
            elif healing_result["action"] == "escalate":
                # CEO escalation already handled by self_healer
                pass
```

### Conductor Integration

**Location:** `/Users/danhaight/.claude/clc/conductor/conductor.py`

**Integration Point:** In `record_node_failure()` method (around line 512-553)

```python
def record_node_failure(self, exec_id: int, error_message: str,
                        error_type: str = "error", duration_ms: int = None):
    """Record failure of a node execution."""
    # Existing failure recording...

    # NEW: Optional self-healing for workflow nodes
    if hasattr(self, 'enable_healing') and self.enable_healing:
        try:
            from query.self_healer import process_failure

            healing_result = process_failure(
                error_output=error_message,
                tool_name="workflow_node",
                tool_input={"node_id": node_id},
                exec_id=exec_id
            )

            if healing_result and healing_result.get("action") == "heal":
                # Store healing metadata in node_executions
                # Could retry node with healing prompt
                pass
        except ImportError:
            pass  # Self-healing not available
```

### Install Script Modification

**Location:** `/Users/danhaight/.claude/clc/setup/install.sh`

**Modification:** In `install_commands()` function (line 25-33)

Already handles copying all files from `setup/commands/` directory. Just need to ensure `experiment.md` exists there.

---

## Dependencies

### From Other Sprint Groups
None - auto-claude-core is independent

### External Dependencies
- Task tool availability for spawning healing agents
- Database write access to `healing_attempts` table
- Hook system enabled in Claude settings.json

### Blocked By
None

---

## Blockers/Risks

### High Risk Items

1. **Production Hook Modification**
   - Risk: Breaking existing learning loop functionality
   - Mitigation: Extensive testing, feature flag for self-healing
   - Rollback: Git revert, disable self-healing config

2. **Async Healing Agent Coordination**
   - Risk: Healing agent results not properly tracked
   - Mitigation: Robust state management, timeout handling
   - Note: Need to determine how to spawn Task from hook context

3. **Database Contention**
   - Risk: Multiple healing attempts writing concurrently
   - Mitigation: SQLite UNIQUE constraint on (failure_id, attempt_number)
   - Already handled by schema

### Medium Risk Items

1. **Circuit Breaker State Persistence**
   - Risk: State file corruption or missing
   - Mitigation: Graceful degradation, state validation
   - Already handled by self_healer.py

2. **Model Selection for Healing**
   - Risk: Expensive opus model used too early
   - Mitigation: Configurable escalation strategy in YAML
   - Already implemented

### Low Risk Items

1. **Experiment Command Installation**
   - Risk: Minimal - just copying a file
   - Mitigation: Test installation process

2. **Configuration Tuning**
   - Risk: Suboptimal pattern matching
   - Mitigation: Iterative tuning based on real failures

---

## Success Criteria

### Issue #31 (Experiment Command)
- [ ] `/experiment` command available in Claude Code
- [ ] All subcommands functional: start, status, merge, discard, clean
- [ ] Successfully create and discard a test experiment
- [ ] Documentation updated

### Issue #30 (Self-Healing Integration)
- [ ] PostToolUse hook triggers healing on detectable failures
- [ ] Healing attempts recorded to `healing_attempts` table
- [ ] Circuit breaker prevents cascading failures
- [ ] CEO escalation for unfixable errors
- [ ] Model escalation follows configured strategy
- [ ] Max attempts enforcement working
- [ ] Integration tests pass
- [ ] No regression in existing learning loop functionality

---

## Testing Strategy

### Unit Tests
- Test failure classification accuracy
- Test healing prompt generation
- Test circuit breaker state machine
- Test max attempts enforcement

### Integration Tests
1. **Syntax Error Healing**
   - Create file with syntax error via Edit
   - Verify healing agent spawned
   - Verify attempt recorded
   - Verify circuit breaker state

2. **Type Error Healing**
   - Create TypeScript type mismatch
   - Verify model escalation on retry
   - Verify max attempts respected

3. **Unfixable Error Handling**
   - Trigger permission error
   - Verify immediate CEO escalation
   - Verify no healing attempt

4. **Circuit Breaker**
   - Trigger 3 consecutive failures
   - Verify circuit opens
   - Verify subsequent attempts blocked
   - Wait for timeout, verify half-open state

### Manual Testing
- Install experiment command and test all subcommands
- Trigger various error types manually
- Verify healing feedback visible to user
- Test with self-healing disabled

---

## Rollback Plan

If issues are discovered post-integration:

1. **Immediate:** Disable self-healing via config
   ```yaml
   self_healing:
     enabled: false
   ```

2. **Quick Rollback:** Revert post_tool_learning.py changes
   - Git revert specific commit
   - Hook continues to work without healing

3. **Full Rollback:** Revert entire sprint branch
   - Switch back to main
   - Remove worktree
   - Delete sprint branch

---

## Estimated Time

### Issue #31 - Install /experiment command
- **Total:** 30 minutes
  - Review: 10 min
  - Modify install.sh: 10 min
  - Test: 10 min

### Issue #30 - Wire Self-Healing QA loops
- **Total:** 4 hours
  - Hook integration: 1.5 hours
  - Conductor integration: 1 hour
  - Database verification: 30 min
  - Testing: 1 hour

**Sprint Total:** ~4.5 hours

---

## Next Steps After Plan Approval

1. Implement Issue #31 first (quick win)
2. Test experiment command installation
3. Implement Issue #30 in phases
4. Run comprehensive tests
5. Create PR with detailed testing notes
6. Request review from CEO

---

## Notes

- Self-healing infrastructure is remarkably complete (21KB + 11KB + 16KB of logic)
- Main challenge is integration points, not implementation
- Consider making healing opt-in per workflow via config
- May need to handle Task tool spawning from hook context specially
- Circuit breaker already has excellent state management
- Database schema is production-ready with proper indexes
