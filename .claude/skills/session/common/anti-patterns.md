# Session Lifecycle Anti-Patterns

> Common mistakes and how to avoid them.

## Overview

This document catalogs anti-patterns observed across all session-lifecycle commands. Understanding these helps users avoid common pitfalls and maintain clean session hygiene.

## Universal Anti-Patterns

### Ignoring Session State

**Pattern**: Running commands without checking current state

**Symptoms**:
- Error: "No active session" after thinking you had one
- Error: "Session already parked" when trying to park
- Confusion about which agent or phase you're in

**Fix**:
- Run `/status` before any session command
- Use hooks to display session context automatically
- Trust error messages—they guide to correct state

**Prevention**: Session state hook displays current state on each command

---

### Direct SESSION_CONTEXT Edits

**Pattern**: Using Edit/Write tools directly on SESSION_CONTEXT.md

**Symptoms**:
- PreToolUse hook blocks operation
- Error: "Use moirai agent for SESSION_CONTEXT mutations"
- Inconsistent session state

**Fix**:
- Always use moirai agent via Task tool
- Follow [moirai invocation pattern](../shared/moirai-invocation.md)

**Prevention**: PreToolUse hook enforces this rule

**Why Bad**: Direct edits bypass validation, break audit trail, cause inconsistent state

---

### Abandoning Sessions

**Pattern**: Starting new session without wrapping previous one

**Symptoms**:
- Error: "Session already active"
- Orphaned SESSION_CONTEXT files
- Lost work context

**Fix**:
- Always /wrap before /start
- Or /park if work isn't complete

**Prevention**: /start validates no existing session

**Why Bad**: Creates orphaned sessions, loses session history

---

### Excessive Handoffs (Ping-Pong)

**Pattern**: More than 6-8 handoffs in a single session

**Symptoms**:
- `handoff_count` > 8
- Agents repeating work or contradicting each other
- Session bloat, loss of direction

**Fix**:
- Re-scope initiative (likely too complex)
- Break into multiple sessions
- /wrap current session, /start smaller sessions

**Prevention**: Track `handoff_count` in SESSION_CONTEXT

**Why Bad**: Indicates scope creep, confused requirements, or design issues

---

## /start Anti-Patterns

### Under-classifying Complexity

**Pattern**: Marking MODULE work as SCRIPT to "skip design"

**Symptoms**:
- Implementation discovers need for architecture
- Rework required
- Missing TDD and ADRs

**Fix**:
- /handoff architect to add design phase
- Or /wrap, /start new session with correct complexity

**Prevention**: When uncertain, classify one level higher

**Why Bad**: Skips critical design thinking, causes rework

---

### Starting PLATFORM as Single Session

**Pattern**: Attempting massive initiative in one session

**Symptoms**:
- PRD > 30 pages
- TDD tries to cover too much
- Context overflow, confusion

**Fix**:
- /wrap planning session (PRD + high-level TDD)
- Break into MODULE/SERVICE sessions
- Each phase gets separate session

**Prevention**: PLATFORM warning during /start

**Why Bad**: Session scope exceeds manageable size, guaranteed context drift

---

### Starting Without Rite Context

**Pattern**: Starting session without verifying rite

**Symptoms**:
- Wrong agents for the work
- Missing specialized expertise
- Handoff to agent that doesn't exist

**Fix**:
- Check ACTIVE_RITE before /start
- Use --rite flag to switch explicitly

**Prevention**: /start displays rite confirmation

**Why Bad**: Wrong agents mean wrong deliverables

---

## /park Anti-Patterns

### Parking with Uncommitted Changes Indefinitely

**Pattern**: Parking session with dirty git status for weeks

**Symptoms**:
- Stale work when resuming
- Merge conflicts
- Forgotten context

**Fix**:
- Commit or stash before extended park
- Add park reason noting git state
- Consider /wrap if work is abandoned

**Prevention**: Park captures `parked_git_status` and warns

**Why Bad**: Stale branches create merge pain, work may be lost

---

### Parking Without Reason

**Pattern**: Using /park with no reason or generic "break"

**Symptoms**:
- Context loss on resume
- Unclear why work was paused
- Can't determine if blocker resolved

**Fix**:
- Always provide descriptive reason
- Examples: "Waiting for design review", "Blocked on API team"

**Prevention**: Prompt for reason if not provided

**Why Bad**: Resume loses context, can't tell if blockers resolved

---

### Multiple Consecutive Parks

**Pattern**: Parking same session 5+ times

**Symptoms**:
- High `resume_count`
- Session stretches across weeks
- Context drift

**Fix**:
- Identify blockers and resolve
- Re-scope session if too large
- Consider /wrap and fresh /start

**Prevention**: Track `resume_count`, warn if > 5

**Why Bad**: Indicates scope or dependency issues, context becomes stale

---

### Parking to Avoid Quality Gates

**Pattern**: Parking instead of wrapping to skip validation

**Symptoms**:
- Session never completes
- Quality issues ship
- Incomplete artifacts

**Fix**:
- Face quality gates head-on
- Fix issues, then /wrap
- Or use /wrap --skip-checks if truly spike work

**Prevention**: Quality gates run on /wrap, not /park

**Why Bad**: Defeats workflow purpose, technical debt accumulates

---

## /resume Anti-Patterns

### Resuming After Major Code Changes

**Pattern**: Codebase changed significantly since park

**Symptoms**:
- SESSION_CONTEXT references outdated files
- PRD/TDD no longer align with code
- Agent confusion

**Fix**:
- Review changes with agent
- Update artifacts if needed
- Consider /wrap stale session, /start fresh

**Prevention**: Resume displays git status changes since park

**Why Bad**: Session context no longer valid, rework likely

---

### Ignoring Rite Mismatch Warning

**Pattern**: Resuming session with different rite than when started

**Symptoms**:
- Target agents don't exist
- Different agent interpretations
- Handoff failures

**Fix**:
- /rite to switch back to session's rite
- Or explicitly override if intentional

**Prevention**: Resume validates rite consistency, warns on mismatch

**Why Bad**: Wrong agents for the work, inconsistent deliverables

---

### Resuming Stale Sessions (Weeks/Months Old)

**Pattern**: Resuming session parked months ago

**Symptoms**:
- Requirements changed
- Technology evolved
- Context completely lost

**Fix**:
- Review PRD/TDD freshness
- Consider /wrap old session
- /start fresh session with updated context

**Prevention**: Resume displays park duration, warns if > 2 weeks

**Why Bad**: Context drift, requirements likely changed, wasted effort

---

### Skipping Git Status Review

**Pattern**: Resuming without reviewing uncommitted changes

**Symptoms**:
- Conflicting work directions
- Overwriting changes
- Git merge disasters

**Fix**:
- Always review git diff when resuming
- Commit or stash before continuing
- Sync with remote if needed

**Prevention**: Resume displays git status changes

**Why Bad**: May conflict with session work, loses changes

---

## /wrap Anti-Patterns

### Habitual --skip-checks

**Pattern**: Always using --skip-checks to avoid validation

**Symptoms**:
- Quality issues ship
- Technical debt accumulates
- Tests fail in production

**Fix**:
- Face quality gates
- Fix issues before wrapping
- Only skip for spikes/prototypes

**Prevention**: --skip-checks logs warning, adds flag to session summary

**Why Bad**: Defeats quality gates, ships incomplete work

---

### Wrapping Mid-Implementation

**Pattern**: Wrapping when work is half-done

**Symptoms**:
- Incomplete artifacts
- Quality gate failures
- Unclear session outcome

**Fix**:
- /park instead if pausing
- Complete implementation before /wrap
- Or use --skip-checks if truly abandoning

**Prevention**: Quality gates check completeness

**Why Bad**: Incomplete work gets "archived" as complete

---

### Ignoring Quality Gate Failures

**Pattern**: Seeing quality gate failures and wrapping anyway

**Symptoms**:
- Technical debt
- Failing tests
- Incomplete artifacts

**Fix**:
- Fix failures before wrapping
- /handoff appropriate agent to fix
- Document why skipping if truly needed

**Prevention**: Quality gates block wrap unless --skip-checks

**Why Bad**: Ships known issues, creates maintenance burden

---

### Wrapping Parked Session Without Review

**Pattern**: /wrap on parked session (auto-resume) without checking state

**Symptoms**:
- Resume context missed
- Changes since park ignored
- Premature completion

**Fix**:
- Explicit /resume first
- Review session state
- Then /wrap after verification

**Prevention**: /wrap auto-resumes but surfaces warnings

**Why Bad**: Misses validation checks from resume

---

## /handoff Anti-Patterns

### Handoff to Same Agent

**Pattern**: /handoff to current `last_agent`

**Symptoms**:
- Error: "Already working with {agent}"
- Wasted command
- Confusion

**Fix**:
- Continue working with current agent
- Or specify different agent

**Prevention**: Handoff validates agent differs from last_agent

**Why Bad**: No-op, wastes tokens, indicates confusion

---

### Handoff Without Artifacts

**Pattern**: Handing off before agent completes deliverables

**Symptoms**:
- Next agent lacks context
- Rework required
- Ping-pong handoffs

**Fix**:
- Let current agent finish artifacts
- Verify artifacts exist before handoff
- Include artifact paths in handoff note

**Prevention**: Handoff note includes current artifacts list

**Why Bad**: Next agent has no foundation to work from

---

### Handoff While Parked

**Pattern**: Trying to handoff a parked session

**Symptoms**:
- Error: "Session parked, use /resume first"
- Handoff blocked

**Fix**:
- /resume first
- Then /handoff

**Prevention**: Handoff validates session state (active required)

**Why Bad**: Handoff requires active session to invoke agent

---

## Cross-Cutting Anti-Patterns

### Proactive Branch/Worktree Creation

**Pattern**: Creating git branches or worktrees without the user explicitly requesting parallel work

**Symptoms**:
- Branch created that the user did not ask for
- Worktree suggested when user just wants to work in current directory
- `git checkout -b` commands appearing in workflow without user keyword trigger
- Output displays branch state as a primary status element

**Fix**:
- Only create branches or worktrees when the user uses explicit keywords: `branch`, `worktree`, `isolate`, `parallel`
- Work on the current branch unless the user requests otherwise
- Do not display branch name as a primary status field
- Do not suggest worktree creation as a default option

**Prevention**: Branch/worktree operations require explicit user intent

**Why Bad**: Creates unwanted git artifacts, pollutes branch namespace, adds complexity the user did not request, and derails the user's intended workflow

---

### Treating Sessions as Todo Lists

**Pattern**: One massive session tracking unrelated tasks

**Symptoms**:
- Session never completes
- Blocker list grows indefinitely
- Context becomes junk drawer

**Fix**:
- One session per initiative
- Break large work into multiple sessions
- Use /wrap and /start for separate concerns

**Prevention**: Initiative scoping during /start

**Why Bad**: Loses focused context, becomes unmaintainable

---

### Skipping Documentation Review

**Pattern**: Never reading PRD/TDD before implementation

**Symptoms**:
- Implementation doesn't match requirements
- Missed edge cases
- Rework during QA

**Fix**:
- Read PRD thoroughly before /handoff engineer
- Review TDD before implementation
- Ask questions if unclear

**Prevention**: Handoff notes reference artifacts to review

**Why Bad**: Builds wrong thing, guaranteed rework

---

### State Confusion

**Pattern**: Not knowing if session is parked or active

**Symptoms**:
- Running wrong commands
- Errors about session state
- Lost work

**Fix**:
- Run /status when uncertain
- Read session state from hook display
- Trust error messages

**Prevention**: Hooks display session state automatically

**Why Bad**: Wrong commands fail, wastes time, causes frustration

---

## Recovery Patterns

When you've fallen into an anti-pattern:

1. **Don't panic**: Sessions are recoverable
2. **Check state**: /status shows current situation
3. **Read errors**: They guide to correct action
4. **Ask for help**: /handoff or /park to regroup
5. **Clean up**: /wrap abandoned sessions, /start fresh

## Prevention Summary

| Anti-Pattern | Prevention Mechanism |
|--------------|----------------------|
| Direct edits | PreToolUse hook blocks |
| Abandoned sessions | /start validates no existing session |
| Excessive handoffs | Track handoff_count, warn at 6+ |
| Wrong complexity | Upgrade prompt during session |
| Uncommitted parks | Capture git status, warn |
| Rite mismatch | Validate on resume, warn |
| Stale resumes | Display park duration, warn > 2 weeks |
| Quality skip | Log flag, add to summary |
| Same agent handoff | Validate agent differs |

## Cross-References

- [Session Validation](session-validation.md) - Pre-flight checks that prevent anti-patterns
- [Error Messages](error-messages.md) - Standard error guidance
- [Session State Machine](session-state-machine.md) - Valid state transitions
