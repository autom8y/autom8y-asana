# CLAUDE.md Anti-Patterns

What NOT to put in CLAUDE.md, with examples and correct alternatives.

---

## Anti-Pattern 1: Session State in CLAUDE.md

### The Violation

```markdown
## Current Work

Currently implementing authentication flow for user login.
Last decision: Use JWT tokens instead of sessions.
```

### Why Wrong

- Changes every session (or multiple times per session)
- Creates maintenance burden (constantly updating)
- Stale within hours
- Clutters the behavioral contract with noise

### Correct Approach

Session state lives in SESSION_CONTEXT (`.claude/sessions/session-id/`):

```markdown
# SESSION_CONTEXT

## Current Initiative
Implementing authentication flow for user login.

## Decisions Made
- Use JWT tokens instead of sessions (rationale: stateless, scales horizontally)
```

Current context is injected by hooks at session start. CLAUDE.md remains stable between sessions.

---

## Anti-Pattern 2: Dynamic Git References

### The Violation

```markdown
## Development Status

Branch: feature/auth-redesign
Uncommitted: 5 files
Last commit: abc123 "Added login form"
```

### Why Wrong

- Git state changes constantly
- Stale immediately after any git operation
- Creates false confidence in inaccurate data
- Requires manual updates that never happen

### Correct Approach

Hooks inject git state at session start:

```markdown
## Project Context (auto-loaded by hook)

| Property | Value |
|----------|-------|
| **Git** | feature/auth-redesign (5 uncommitted) |
```

This content is:
- Generated fresh each session start
- Never written to CLAUDE.md
- Only exists in conversation context

---

## Anti-Pattern 3: Duplicating Roster State

### The Violation

```markdown
## Team

Active Team: doc-team-pack
Swapped: 2024-12-25
Previous Team: dev-pack
```

### Why Wrong

- Duplicates ACTIVE_TEAM file (can desync)
- Dates become stale immediately
- History belongs in git, not CLAUDE.md
- Creates two sources of truth

### Correct Approach

Team sections are regenerated from ACTIVE_TEAM + agents/:

```markdown
## Quick Start

This project uses a 4-agent workflow (doc-team-pack):

| Agent | Role |
|-------|------|
| **documentation-engineer** | Migration specialist |
...
```

The team name and agent list come from roster state, not manual entries.

---

## Anti-Pattern 4: Personal Preferences in Project File

### The Violation

```markdown
## My Preferences

I prefer TypeScript over JavaScript for this project.
Use 2-space indentation.
Always use arrow functions.
```

### Why Wrong

- User-specific, not project-specific
- Other team members have different preferences
- Project file should be team-neutral
- Creates conflict in shared repositories

### Correct Approach

Personal preferences belong in ~/.claude/CLAUDE.md:

```markdown
# ~/.claude/CLAUDE.md (user global)

## Coding Style
- Prefer TypeScript
- 2-space indentation
- Arrow functions when possible
```

Project-specific conventions belong in .editorconfig or project linting configs:

```ini
# .editorconfig
[*]
indent_size = 2
```

---

## Anti-Pattern 5: Hardcoded Dynamic Values

### The Violation

```markdown
## Project Status

Sprint: Sprint 23 (ends Jan 15)
Velocity: 42 points
Blockers: Waiting on API design review
```

### Why Wrong

- Sprint info changes every 2 weeks
- Velocity changes each sprint
- Blockers resolve and new ones appear
- All become stale quickly

### Correct Approach

Dynamic project state lives in project management tools or session files:

- Sprint info: Jira, Linear, project board
- Blockers: Session files or PRD
- Status: Not in CLAUDE.md at all

---

## Anti-Pattern 6: Session History

### The Violation

```markdown
## Session History

- 2024-12-24: Worked on auth, parked for holidays
- 2024-12-20: Completed user model design
- 2024-12-18: Started authentication initiative
```

### Why Wrong

- Session history belongs in session files
- CLAUDE.md is not a changelog
- Creates stale audit trail
- Grows without bound

### Correct Approach

Session summaries live in `.claude/sessions/`:

```
.claude/sessions/
  session-20241224-143022/
    SUMMARY.md
  session-20241220-091500/
    SUMMARY.md
```

Use `/sessions` command to list sessions. CLAUDE.md is timeless (no dates, no history).

---

## Anti-Pattern 7: Copying Skeleton Team to Satellites

### The Violation

```markdown
# satellite CLAUDE.md (after CEM sync)

## Quick Start

This project uses a 6-agent workflow (ecosystem-pack):
| ecosystem-analyst | ... |
| context-architect | ... |
```

### Why Wrong

- Satellite has its own team (e.g., doc-team-pack)
- Team content should come from satellite's ACTIVE_TEAM + agents/
- Skeleton's team is irrelevant to satellite
- Creates incorrect agent routing

### Correct Approach

Team sections are:
- PRESERVE (keep satellite's existing content)
- Or REGENERATE (rebuild from satellite's roster state)
- Never SYNC (copy from skeleton)

---

## Anti-Pattern 8: "Last Updated" Timestamps

### The Violation

```markdown
# CLAUDE.md

Last updated: 2024-12-25 14:30:22
Version: 1.4.2
```

### Why Wrong

- Immediately stale after any change
- Requires manual updates
- Provides false confidence
- Git provides this automatically

### Correct Approach

Use git for version history:

```bash
git log --oneline -5 .claude/CLAUDE.md
```

No timestamps in the file itself.

---

## Anti-Pattern 9: Task Lists in CLAUDE.md

### The Violation

```markdown
## TODO

- [ ] Implement login form
- [ ] Add password validation
- [x] Create user model
```

### Why Wrong

- Task state is session-scoped
- Completed tasks become noise
- Multiple sessions create conflicts
- Better tools exist (todo tools, issue trackers)

### Correct Approach

Use appropriate task tracking:
- Session tasks: TodoWrite tool
- Project tasks: Issue tracker (GitHub Issues, Linear)
- Sprint tasks: Project board

---

## Anti-Pattern 10: Environment-Specific Configuration

### The Violation

```markdown
## Environment

Database: postgresql://localhost:5432/myapp
API_KEY: sk-1234567890abcdef
Debug: true
```

### Why Wrong

- Environment varies by machine
- Secrets should never be in version control
- Debug settings are personal/temporary
- Creates security and portability issues

### Correct Approach

Environment configuration lives in:
- `.env` files (gitignored)
- Environment variables
- Secret managers
- `.env.example` for templates (without real values)

---

## Anti-Pattern 11: Misplaced or Missing Ownership Markers

### The Violation

```markdown
## Quick Start

Content here.

<!-- PRESERVE: satellite-owned -->  # WRONG - marker AFTER section
## Agent Routing
```

Or:

```markdown
## Quick Start  # WRONG - no marker at all

Content here.
```

### Why Wrong

- Markers must precede sections for CEM to parse correctly
- Misplaced markers cause sync to lose ownership context
- Missing markers create ambiguity about section ownership
- Results in markers appearing between sections after sync

### Correct Approach

```markdown
<!-- PRESERVE: satellite-owned, regenerated from ACTIVE_TEAM + agents/ -->
## Quick Start

Content here.

<!-- SYNC: skeleton-owned -->
## Agent Routing
```

**Rules**:
1. Marker appears on the line **immediately before** the section header
2. No blank line between marker and `## Header`
3. Every section should have an ownership marker

### How to Fix

If markers are misplaced after sync:
1. Re-sync from skeleton with fixed CEM
2. Or manually move markers to correct positions

---

## Quick Reference: Red Flags

| If You See... | It's Wrong Because... | Move To... |
|---------------|----------------------|------------|
| "Currently working on X" | Session state | SESSION_CONTEXT |
| "Last updated: DATE" | Stale metadata | Git history |
| "Git branch: X" | Changes constantly | Hook output |
| Skeleton team in satellite | Wrong team source | ACTIVE_TEAM |
| Personal preferences | Wrong scope | ~/.claude/CLAUDE.md |
| Sprint/initiative details | Too dynamic | PRD, session files |
| Task checkboxes | Session-scoped | Todo tools |
| Hardcoded secrets | Security risk | .env, secret manager |
| Version numbers (unless stable) | Creates maintenance | Package manifests |

---

## The Test

Before adding content, ask:

1. **Would this be stale tomorrow?** -> Do not add
2. **Does this belong to a single session?** -> SESSION_CONTEXT
3. **Is this personal, not project-wide?** -> ~/.claude/CLAUDE.md
4. **Does this duplicate another source?** -> Reference, do not duplicate
5. **Can Claude work without this?** -> Consider removing

---

## Related Files

- [first-principles.md](first-principles.md) - Core architectural principles
- [ownership-model.md](ownership-model.md) - Section ownership details
- [boundary-test.md](boundary-test.md) - Validation checklist
