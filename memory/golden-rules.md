# Golden Rules

Constitutional principles derived from hard-won experience.

1. **Always check existing knowledge before starting a task.** _(domain: general)_
   - Prevents repeating known mistakes and leverages accumulated wisdom.

2. **Record failures while context is fresh, before moving on.** _(domain: general)_
   - Details fade quickly; immediate documentation captures root causes.

3. **Don't just note what happened; extract the transferable principle.** _(domain: general)_
   - Outcomes are specific; heuristics apply broadly.

4. **Actively try to break your solution before declaring it done.** _(domain: general)_
   - You will find bugs now or users will find them later.

5. **When unsure about high-stakes decisions, escalate to CEO.** _(domain: general)_
   - Better to ask than to assume incorrectly on important matters.

6. **Before closing any significant work session, review and record what was learned.** _(domain: general)_
   - The system only works if you use it. We built an entire learning framework and almost forgot to record the bugs we found while building it. Ironic and instructive.

7. **When user gives a direct action command (close, stop, kill, quit), execute it FIRST before anything else.** _(domain: general)_
   - User trust depends on responsiveness. Ignoring direct commands causes frustration and breaks trust.

8. **Complete all logging to the building BEFORE giving the user a summary. The summary is the final step, not the trigger to log.** _(domain: general)_
   - Summaries signal "I'm done" to the user. If logging happens after, it requires user to remind you. Logging is part of completing the work, not a separate afterthought.

9. **useEffect with callback deps causes reconnect loops - use refs for callbacks, empty deps for mount-only effects** _(domain: general)_
   - React useEffect re-runs when dependencies change. Callbacks like onMessage are new references each render, causing effect to re-run and reconnect WebSocket. Fix: store callback in useRef, update ref in separate effect, use empty [] deps for connection effect.

10. **When user reports something is broken/empty/wrong, believe them immediately over tool outputs showing "valid" data.** _(domain: general)_
   - Tools can report files exist, sizes look right, headers check out, APIs confirm presence - but the actual content can still be empty/corrupt. The user sees the real result. Metadata lies; user experience doesn't.

11. **NEVER suggest external API calls (OpenAI, Anthropic API, etc.). This is a subscription-based app. Use Claude Code subagents via Task tool, covered by user's Max plan.** _(domain: general)_
   - User pays for Max subscription. Suggesting API calls means extra costs, API keys, external dependencies. Everything must work through Claude Code's existing infrastructure (Task tool with haiku/sonnet/opus models). No exceptions.

12. **Default to `run_in_background=True` for ALL subagent spawns. Block with TaskOutput only when you actually need the result. Never use synchronous subagents.** _(domain: general)_
   - Async lets you do other work while agents run. Multiple agents can run in parallel. Sync wastes time waiting. There's NO good reason to block immediately on spawn.

13. **Continuously poll PRs for reviewer feedback (every 2 minutes) and address ALL feedback before proceeding. Never run `/run-ci` until feedback exists AND is fully addressed. Never merge - only the CEO merges.** _(domain: general)_
   - Agents waste GitHub Actions credits by triggering CI prematurely. Feedback must be genuinely addressed (implemented or explained) before marking resolved. Merge authority belongs exclusively to the CEO; unauthorized merges must be reverted, recorded as failure, and escalated.
