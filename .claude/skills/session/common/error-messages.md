# Standard Error Messages

> Consistent error message templates for session-lifecycle commands.

## Overview

This document defines standard error messages used across all session-lifecycle commands. Consistent messaging helps users understand what went wrong and how to fix it.

## Error Message Format

All error messages follow this structure:

```
{Icon} {Error Title}

{Detailed explanation}

{Current state information}

{Resolution steps}

{Related commands}
```

**Icons**:
- ⚠ - Warning (non-blocking)
- ✗ - Error (blocking)
- ℹ - Information

## Session Existence Errors

### No Active Session

**When**: Any command requiring session (park, resume, wrap, handoff) but none exists

```
✗ No Active Session

No session found for current project.

Resolution:
- Use /start to begin a new session
- Check if you're in the correct directory

Related: /start, /status
```

**Variables**: `{command}` - the verb being attempted

**Code**: `NO_SESSION`

---

### Session Already Exists

**When**: /start when session already active

```
✗ Session Already Active

Active session: {initiative}
Created: {created_at}
Phase: {current_phase}
Rite: {active_rite}

Resolution:
- Use /resume to continue this session
- Use /wrap to complete it before starting new session
- Use /status to check session details

Related: /resume, /wrap, /status
```

**Variables**: `{initiative}`, `{created_at}`, `{current_phase}`, `{active_rite}`

**Code**: `SESSION_EXISTS`

---

## Session State Errors

### Session Already Parked

**When**: /park on already-parked session

```
✗ Session Already Parked

Parked: {parked_at}
Reason: {parked_reason}
Duration: {park_duration}

This session is already paused.

Resolution:
- Use /resume to continue working
- Use /status to check session state

Related: /resume, /status
```

**Variables**: `{parked_at}`, `{parked_reason}`, `{park_duration}`

**Code**: `ALREADY_PARKED`

---

### Session Not Parked

**When**: /resume on active (not parked) session

```
ℹ Session Not Parked

This session is already active (not paused).

Current state:
- Phase: {current_phase}
- Agent: {last_agent}

Continue working or use /park to pause.

Related: /park, /handoff, /status
```

**Variables**: `{current_phase}`, `{last_agent}`

**Code**: `NOT_PARKED`

---

### Session Must Be Active

**When**: /park, /wrap, /handoff on parked session

```
✗ Session Is Parked

Parked: {parked_at}
Reason: {parked_reason}

This command requires an active (not parked) session.

Resolution:
- Use /resume to continue first
- Then retry this command

Related: /resume
```

**Variables**: `{parked_at}`, `{parked_reason}`

**Code**: `SESSION_PARKED`

---

## Rite Context Errors

### Rite Not Found

**When**: --rite specified but doesn't exist

```
✗ Rite Not Found

Rite '{rite_name}' does not exist in knossos.

Available rites:
{rite_list}

Resolution:
- Choose rite from list above
- Check KNOSSOS_HOME: {knossos_home}
- Use /rite to see rite details

Related: /rite
```

**Variables**: `{rite_name}`, `{rite_list}`, `{knossos_home}`

**Code**: `RITE_NOT_FOUND`

---

### Knossos System Unavailable

**When**: KNOSSOS_HOME not set or invalid

```
✗ Knossos System Unavailable

Knossos system not found or configured.

Checks:
- KNOSSOS_HOME: {knossos_home_value}
- Directory exists: {exists}

Resolution:
- Set KNOSSOS_HOME environment variable
- Point to knossos installation directory
- Example: export KNOSSOS_HOME=~/Code/knossos

Related: /help, /status
```

**Variables**: `{knossos_home_value}`, `{exists}`

**Code**: `KNOSSOS_UNAVAILABLE`

---

## Agent Errors

### Agent Not Found

**When**: /handoff to agent that doesn't exist

```
✗ Agent Not Found

Agent '{agent_name}' not found in rite '{rite}'.

Available agents in {rite}:
{agent_list}

Resolution:
- Choose agent from list above
- Use /rite to see agent descriptions
- Switch rites with /rite if needed

Related: /rite
```

**Variables**: `{agent_name}`, `{rite}`, `{agent_list}`

**Code**: `AGENT_NOT_FOUND`

---

### Same Agent Handoff

**When**: /handoff to current agent

```
ℹ Already Working With This Agent

Current agent: {last_agent}
Target agent: {target_agent}

These are the same. No handoff needed.

Resolution:
- Continue working with current agent
- Or specify different agent

Related: /status, /rite
```

**Variables**: `{last_agent}`, `{target_agent}`

**Code**: `SAME_AGENT`

---

## Quality Gate Errors

### Quality Gate Failure: PRD

**When**: /wrap but PRD missing or incomplete

```
⚠ Quality Gate Failure: PRD

Issues:
{issue_list}

Examples:
- PRD file not found: {expected_path}
- PRD missing sections: Acceptance Criteria, Success Metrics
- PRD has 2 unanswered blocking questions

Resolution:
1. Complete PRD before wrapping
2. Use /handoff requirements-analyst to fix PRD
3. Use /wrap --skip-checks to skip validation (not recommended)

Related: /handoff, /wrap --skip-checks
```

**Variables**: `{issue_list}`, `{expected_path}`

**Code**: `QUALITY_GATE_PRD`

---

### Quality Gate Failure: TDD/ADRs

**When**: /wrap but TDD or ADRs missing (MODULE+)

```
⚠ Quality Gate Failure: TDD/ADRs

Issues:
{issue_list}

Examples:
- TDD file not found: {expected_path}
- TDD references 3 decisions but only 1 ADR found
- TDD missing component interfaces section

Resolution:
1. Complete TDD and ADRs before wrapping
2. Use /handoff architect to address issues
3. Use /wrap --skip-checks to skip validation (not recommended)

Related: /handoff, /wrap --skip-checks
```

**Variables**: `{issue_list}`, `{expected_path}`

**Code**: `QUALITY_GATE_TDD`

---

### Quality Gate Failure: Implementation

**When**: /wrap but code quality issues

```
⚠ Quality Gate Failure: Implementation

Issues:
{issue_list}

Examples:
- Uncommitted changes: 3 files
- Tests failing: 2/15 failed
- Type safety errors: mypy found 1 issue

Git Status:
{git_status}

Resolution:
1. Commit all changes
2. Fix failing tests
3. Address type safety and lint issues
4. Re-run /wrap

Or use /wrap --skip-checks (not recommended)

Related: /handoff, /wrap --skip-checks
```

**Variables**: `{issue_list}`, `{git_status}`

**Code**: `QUALITY_GATE_CODE`

---

### Quality Gate Failure: Validation

**When**: /wrap but QA validation incomplete

```
⚠ Quality Gate Failure: Validation

Issues:
{issue_list}

Examples:
- Test Plan shows 2 open defects (1 critical)
- 1 acceptance criterion not validated
- Edge case testing incomplete

Defects:
{defect_list}

Resolution:
1. Address critical defects
2. Document medium/low as known issues
3. Complete validation of all criteria
4. Re-run /wrap

Or use /wrap --skip-checks (not recommended)

Related: /handoff, /wrap --skip-checks
```

**Variables**: `{issue_list}`, `{defect_list}`

**Code**: `QUALITY_GATE_QA`

---

## Validation Warnings (Non-Blocking)

### Rite Mismatch

**When**: /resume but ACTIVE_RITE differs from session rite

```
⚠ Rite Mismatch

Session rite:  {session_rite}
Active rite:   {active_rite}

This may cause agent availability issues.

Options:
1. Switch to session rite: /rite {session_rite}
2. Continue with current rite (agents may differ)
3. Cancel and investigate

Continue? [1/2/cancel]:
```

**Variables**: `{session_rite}`, `{active_rite}`

**Code**: `RITE_MISMATCH`

---

### Git Status Changed

**When**: /resume and git status differs from park time

```
⚠ Git Status Changed Since Park

Parked git status: {parked_git_status}
Current git status: {current_git_status}

Uncommitted files: {file_count}
{file_list}

Review changes before continuing? [y/n]:
```

**Variables**: `{parked_git_status}`, `{current_git_status}`, `{file_count}`, `{file_list}`

**Code**: `GIT_STATUS_CHANGED`

---

### Uncommitted Changes

**When**: /park or /wrap with dirty git status

```
⚠ Uncommitted Changes Detected

{file_count} uncommitted files:
{file_list}

{git_status}

Recommendation:
- Commit changes before {command}
- Or stash for later

Continue anyway? [y/n]:
```

**Variables**: `{file_count}`, `{file_list}`, `{git_status}`, `{command}`

**Code**: `UNCOMMITTED_CHANGES`

---

### Stale Session

**When**: /resume session parked > 2 weeks ago

```
⚠ Stale Session

Parked: {parked_at}
Duration: {park_duration}

This session has been parked for {days} days.
Context may be outdated.

Recommendations:
- Review PRD and TDD for relevance
- Check if requirements changed
- Consider /wrap and /start fresh

Continue resuming? [y/n]:
```

**Variables**: `{parked_at}`, `{park_duration}`, `{days}`

**Code**: `STALE_SESSION`

---

### High Handoff Count

**When**: handoff_count > 8

```
⚠ High Handoff Count

This session has {handoff_count} handoffs.

High handoff counts may indicate:
- Scope creep or unclear requirements
- Need to break into multiple sessions
- Complexity underestimated

Recommendations:
- Review session scope with requirements-analyst
- Consider breaking into multiple sessions
- Use /wrap to complete current session

Continue with handoff? [y/n]:
```

**Variables**: `{handoff_count}`

**Code**: `HIGH_HANDOFF_COUNT`

---

## Moirai Errors

### Lifecycle Violation

**When**: Moirai rejects operation due to invalid state transition

```
✗ Lifecycle Violation

{moirai_message}

Current state: {current_state}
Attempted operation: {operation}

{moirai_hint}

Related: {suggested_commands}
```

**Variables**: `{moirai_message}`, `{current_state}`, `{operation}`, `{moirai_hint}`, `{suggested_commands}`

**Code**: `LIFECYCLE_VIOLATION`

---

### Validation Error

**When**: Moirai detects invalid field or value

```
✗ Validation Error

{moirai_message}

Field: {field}
Value: {value}
Expected: {expected}

Resolution:
{moirai_hint}

Related: {suggested_commands}
```

**Variables**: `{moirai_message}`, `{field}`, `{value}`, `{expected}`, `{moirai_hint}`, `{suggested_commands}`

**Code**: `VALIDATION_ERROR`

---

### Moirai Unavailable

**When**: Moirai agent doesn't respond

```
✗ Moirai Unavailable

Session state mutations require Moirai agent.

Checks:
- Moirai agent file: {agent_file_exists}
- Task tool available: {task_available}

Resolution:
- Check agent configuration
- Verify moirai.md exists
- Retry operation

If issue persists, contact support.

Related: /status, /help
```

**Variables**: `{agent_file_exists}`, `{task_available}`

**Code**: `MOIRAI_UNAVAILABLE`

---

## Skip Checks Warning

**When**: --skip-checks flag used

```
⚠ Skipping Quality Gates

You've used --skip-checks flag.

This skips validation:
{validation_list}

Quality issues may exist in artifacts.

This is not recommended except for:
- Spike/prototype work
- Emergency fixes
- Exploratory sessions

Continue wrap without validation? [y/n]:
```

**Variables**: `{validation_list}`

**Code**: `SKIP_CHECKS`

---

## Error Code Reference

| Code | Blocking | Commands |
|------|----------|----------|
| NO_SESSION | Yes | park, resume, wrap, handoff |
| SESSION_EXISTS | Yes | start |
| ALREADY_PARKED | Yes | park |
| NOT_PARKED | No | resume |
| SESSION_PARKED | Yes | park, wrap, handoff |
| RITE_NOT_FOUND | Yes | start, resume, handoff |
| KNOSSOS_UNAVAILABLE | Yes | start, resume, handoff |
| AGENT_NOT_FOUND | Yes | handoff, resume |
| SAME_AGENT | No | handoff |
| QUALITY_GATE_* | Yes* | wrap |
| RITE_MISMATCH | No | resume |
| GIT_STATUS_CHANGED | No | resume |
| UNCOMMITTED_CHANGES | No | park, wrap |
| STALE_SESSION | No | resume |
| HIGH_HANDOFF_COUNT | No | handoff |
| LIFECYCLE_VIOLATION | Yes | Any (via moirai) |
| VALIDATION_ERROR | Yes | Any (via moirai) |
| MOIRAI_UNAVAILABLE | Yes | park, resume, wrap |
| SKIP_CHECKS | No | wrap |

*Unless --skip-checks used

## Usage in Code

Error messages should be generated using these templates:

```bash
# Example: No active session
error_no_session() {
  local command=$1
  cat <<EOF
✗ No Active Session

No session found for current project.

Resolution:
- Use /start to begin a new session
- Check if you're in the correct directory

Related: /start, /status
EOF
  return 1
}
```

## Cross-References

- [Session Validation](session-validation.md) - Validation patterns that trigger errors
- [Anti-Patterns](anti-patterns.md) - Common mistakes and how to avoid them
- [Session State Machine](session-state-machine.md) - Valid state transitions
