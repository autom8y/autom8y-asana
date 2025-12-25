---
name: resume
description: "Resume a parked work session. Restores context, checks for team/git changes, offers agent selection. Removes park metadata and continues work. Triggers: /resume, continue session, resume work, unpause session, restore session."
---

# /resume - Resume Parked Work Session

> **Category**: Session Lifecycle | **Phase**: Session Restoration

## Purpose

Resume a previously parked work session by restoring full context to Claude. Displays session summary (initiative, artifacts, blockers), checks for team or git changes since parking, allows agent selection, and continues work where it was paused.

Use `/resume` when:
- Returning to work after using `/park`
- Continuing a session after a break or blocker resolution
- Picking up work after external dependencies are met
- Restarting work after context switch

---

## Usage

```bash
/resume [--agent=NAME]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--agent` | No | `last_agent` | Agent to continue with (overrides SESSION_CONTEXT last_agent) |

---

## Behavior

When `/resume` is invoked, the following sequence occurs:

### 1. Pre-flight Validation

- **Check for parked session**: Verify `.claude/SESSION_CONTEXT` file exists
  - If missing → Error: "No parked session found. Use `/start` to begin a new session"
- **Check park status**: Verify `parked_at` field is set
  - If not set → Error: "Session is already active (not parked). Continue working or use `/status`"

### 2. Load and Display Session Summary

Read SESSION_CONTEXT and display summary:

```
Resuming Session: {initiative-name}

Session Details:
- Started: {created_at}
- Parked: {parked_at} ({duration ago})
- Park reason: {parked_reason}
- Complexity: {complexity}
- Team: {active_team}
- Current phase: {parked_phase}
- Last agent: {last_agent}

Artifacts produced:
✓ PRD: /docs/requirements/PRD-{slug}.md
✓ TDD: /docs/design/TDD-{slug}.md
⧗ Implementation: In progress [if applicable]

Blockers: {count}
{list blockers if any}

Open Questions: {count}
{list questions if any}

Next steps:
1. {first next step}
2. {second next step}
```

### 3. Validate Context

Perform context validation checks:

#### Team Consistency Check

- Read current `.claude/ACTIVE_TEAM`
- Compare to SESSION_CONTEXT `active_team` field
- If different:

```
⚠ Team Mismatch Detected

Session started with: {session.active_team}
Current active team: {current ACTIVE_TEAM}

This session's agents may not be available in the current team.

Options:
1. Switch back to {session.active_team} (recommended)
2. Continue with {current ACTIVE_TEAM} (may cause issues)
3. Cancel resume

Choice [1/2/3]:
```

If user chooses option 1: Invoke `~/Code/roster/swap-team.sh {session.active_team}`

#### Git Status Check

- Run `git status` to get current working directory state
- Compare to `parked_git_status` from SESSION_CONTEXT
- If mismatch (was clean, now dirty) or new uncommitted files:

```
⚠ Git Changes Detected

Git status at park time: {parked_git_status}
Current git status: {current status}

New/modified files since park:
- {file1}
- {file2}

This may indicate:
1. Work done outside this session
2. Merge conflicts from branch updates
3. Unrelated changes

Review changes before continuing? [y/n]:
```

If yes: Display `git diff --stat` output

### 4. Agent Selection

Confirm which agent to continue with:

```
Resume with agent: {last_agent} [default]

Available agents in {active_team}:
- requirements-analyst
- architect
- principal-engineer
- qa-adversary

Continue with {last_agent}? [Y/n]:
```

If user provides `--agent=NAME` parameter, use that instead of prompting.

Validate agent exists in current team:
- Check `.claude/agents/{agent}.md` file exists
- If not found → Error: "Agent '{agent}' not found in team '{active_team}'"

### 5. Remove Park Metadata

Update SESSION_CONTEXT by removing park fields from YAML frontmatter:

```yaml
---
# Remove these fields:
# parked_at
# parked_reason
# parked_phase
# parked_git_status
# parked_uncommitted_files

# Keep all other fields
---
```

### 6. Invoke Selected Agent

Use Task tool to invoke the selected agent with full session context:

```markdown
Act as **{Agent Name}**.

You are resuming a parked work session.

Initiative: {initiative}
Complexity: {complexity}
Current phase: {current_phase}
Session parked: {parked_at} (resumed {now})
Park reason: {parked_reason}

Artifacts completed:
{list artifacts from SESSION_CONTEXT}

Blockers:
{list blockers from SESSION_CONTEXT}

Open Questions:
{list questions from SESSION_CONTEXT}

Context from SESSION_CONTEXT:
{full context section from SESSION_CONTEXT body}

Next steps:
{next_steps from SESSION_CONTEXT}

Continue work from where the session was paused. Review existing artifacts before proceeding.
```

### 7. Update SESSION_CONTEXT

After agent invoked, update metadata:

```yaml
---
resumed_at: "2025-12-24T16:00:00Z"
resume_count: {increment or set to 1}
last_agent: "{selected-agent}"
---
```

### 8. Confirmation

Display confirmation message:

```
Session resumed: {initiative-name}
Duration parked: {parked_at → now}
Continuing with: {selected-agent}
Current phase: {current_phase}

Next: {first item from next_steps}

Commands:
- /park - Pause again if needed
- /handoff - Switch to different agent
- /wrap - Complete session
```

---

## State Changes

### Fields Modified in SESSION_CONTEXT

| Field | Action | Description |
|-------|--------|-------------|
| `parked_at` | REMOVED | Park timestamp deleted |
| `parked_reason` | REMOVED | Park reason deleted |
| `parked_phase` | REMOVED | Phase at park time deleted |
| `parked_git_status` | REMOVED | Git status at park deleted |
| `parked_uncommitted_files` | REMOVED | Uncommitted file count deleted |
| `resumed_at` | ADDED/UPDATED | Most recent resume timestamp |
| `resume_count` | ADDED/UPDATED | Number of times resumed |
| `last_agent` | UPDATED | Agent selected for resume |

### Agent Invocation

Selected agent receives full SESSION_CONTEXT as context and continues work.

---

## Examples

### Example 1: Simple Resume (Same Day)

```bash
/resume
```

Output:
```
Resuming Session: Add dark mode toggle

Session Details:
- Started: 2025-12-24 10:00:00
- Parked: 2025-12-24 12:30:00 (3 hours ago)
- Park reason: Lunch break
- Complexity: MODULE
- Team: 10x-dev-pack
- Current phase: design
- Last agent: architect

Artifacts produced:
✓ PRD: /docs/requirements/PRD-dark-mode.md
✓ TDD: /docs/design/TDD-dark-mode.md

✓ No blockers
✓ Git status: Clean
✓ Team consistent

Continue with architect? [Y/n]: Y

Session resumed: Add dark mode toggle
Duration parked: 3 hours
Continuing with: architect
Current phase: design

Architect is reviewing TDD and ready to proceed with ADR creation.
```

### Example 2: Resume After Team Change

```bash
/resume
```

Output:
```
Resuming Session: Multi-tenant authentication

Session Details:
- Started: 2025-12-23 14:00:00
- Parked: 2025-12-23 17:00:00 (1 day ago)
- Park reason: Waiting for design review
- Complexity: SERVICE
- Team: 10x-dev-pack
- Current phase: design
- Last agent: architect

⚠ Team Mismatch Detected

Session started with: 10x-dev-pack
Current active team: doc-team-pack

Options:
1. Switch back to 10x-dev-pack (recommended)
2. Continue with doc-team-pack (may cause issues)
3. Cancel resume

Choice [1/2/3]: 1

Switching to team: 10x-dev-pack
✓ Swapped to 10x-dev-pack (5 agents loaded)

Continue with architect? [Y/n]: Y

Session resumed: Multi-tenant authentication
Duration parked: 1 day
Continuing with: architect
```

### Example 3: Resume with Different Agent

```bash
/resume --agent=principal-engineer
```

Output:
```
Resuming Session: API retry logic

Session Details:
- Started: 2025-12-24 09:00:00
- Parked: 2025-12-24 12:00:00 (4 hours ago)
- Park reason: Design approved, ready for implementation
- Complexity: MODULE
- Team: 10x-dev-pack
- Current phase: design
- Last agent: architect

Artifacts produced:
✓ PRD: /docs/requirements/PRD-api-retry.md
✓ TDD: /docs/design/TDD-api-retry.md
✓ ADR-0043: Exponential backoff strategy

✓ No blockers
✓ Git status: Clean

Resuming with principal-engineer (overriding last_agent: architect)

Session resumed: API retry logic
Duration parked: 4 hours
Continuing with: principal-engineer
Current phase: implementation

Principal Engineer ready to implement based on approved TDD.
```

### Example 4: Resume with Git Changes

```bash
/resume
```

Output:
```
Resuming Session: Database migration

Session Details:
- Started: 2025-12-20 10:00:00
- Parked: 2025-12-20 16:00:00 (4 days ago)
- Park reason: End of sprint
- Complexity: SERVICE
- Current phase: implementation
- Last agent: principal-engineer

⚠ Git Changes Detected

Git status at park time: clean
Current git status: dirty

New/modified files since park:
- src/db/migrations/0012_add_indexes.sql (new)
- src/db/schema.py (modified)
- tests/test_migration.py (modified)

This may indicate work done outside this session.

Review changes before continuing? [y/n]: y

git diff --stat:
 src/db/migrations/0012_add_indexes.sql | 15 +++++++++++++++
 src/db/schema.py                       |  5 +++--
 tests/test_migration.py                |  8 ++++++++
 3 files changed, 26 insertions(+), 2 deletions(-)

Continue with principal-engineer? [Y/n]: Y

Session resumed: Database migration
Duration parked: 4 days
⚠ Note: Review external changes before proceeding
```

---

## Prerequisites

- Parked session exists (`.claude/SESSION_CONTEXT` with `parked_at` field)
- Target agent exists in active team (or team can be switched)

---

## Success Criteria

- SESSION_CONTEXT park metadata removed
- Agent invoked with full session context
- User receives clear summary and continuation guidance
- Team and git inconsistencies detected and surfaced
- Work continues seamlessly from park point

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| No parked session | `.claude/SESSION_CONTEXT` missing | Use `/start` to begin new session |
| Session not parked | `parked_at` field not set | Session is already active, continue working |
| Invalid agent | Agent not in current team | Specify valid agent or switch teams |
| Team unavailable | Session team not in roster | Install team pack or choose different team |
| Merge conflicts | Git detects conflicts | Resolve conflicts before resuming |

---

## Related Commands

- `/start` - Begin new session
- `/park` - Pause current session
- `/status` - View session state without resuming
- `/handoff` - Switch agents after resuming
- `/switch` - Change active team

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Understanding workflow phases and handoffs
- [documentation](../documentation/SKILL.md) - Reviewing PRD/TDD/ADR artifacts

---

## Agent Delegation

This command uses the Task tool to invoke the selected agent (default: `last_agent` from SESSION_CONTEXT, override with `--agent` parameter).

Agent receives full SESSION_CONTEXT as context including:
- Initiative and complexity
- All produced artifacts
- Current blockers and open questions
- Next steps from park time
- Park duration and reason

---

## Design Notes

### Why Validate Team Consistency?

Team packs contain different agents. If session started with `10x-dev-pack` but current team is `doc-team-pack`, the expected agents may not be available. This check prevents confusing errors and guides users to restore proper context.

### Why Check Git Status?

Git changes since park indicate:
1. **Concurrent work**: Files modified outside the session
2. **Merge issues**: Branch diverged, conflicts possible
3. **Stale session**: Session may no longer be relevant

Early detection prevents wasted effort on stale work and surfaces integration issues immediately.

### Why Allow Agent Override?

Session phases evolve. A session parked during design (last_agent: architect) may be ready for implementation when resumed. Allowing `--agent` override supports natural phase transitions without requiring a separate `/handoff` call.

### Resume Count Tracking

The `resume_count` field tracks park/resume cycles. This helps:
1. Identify frequently interrupted sessions (potential issues)
2. Audit session timeline in retrospective
3. Surface sessions that may need breaking into smaller chunks

Multiple resumes aren't inherently bad, but high counts may indicate scope creep or external dependencies that should be addressed.
