---
user-invocable: false
---

# Parking Summary Template

> Template for the parking summary appended to SESSION_CONTEXT.

## Template

```markdown
## Parking Summary - {timestamp}

**Parked**: {ISO 8601 timestamp}
**Reason**: {user-provided reason or "Manual park"}
**Duration so far**: {created_at → parked_at}
**Current phase**: {requirements|design|implementation|validation}
**Last agent**: {agent-name}

### Progress

Artifacts completed:
- ✓ PRD: /docs/requirements/PRD-{slug}.md
- ✓ TDD: /docs/design/TDD-{slug}.md
- ⧗ Implementation: In progress

### State

Git status: {clean | N uncommitted files}
Blockers: {count} active
Open questions: {count} unresolved

### Next Steps on Resume

1. {first next step}
2. {second next step}
```

## Field Values

| Field | Source | Format |
|-------|--------|--------|
| timestamp | Current time | YYYY-MM-DD HH:MM:SS |
| reason | User parameter or default | String |
| duration | `created_at` to now | Human-readable (e.g., "2h 15m") |
| phase | SESSION_CONTEXT.current_phase | Enum value |
| agent | SESSION_CONTEXT.last_agent | Agent identifier |
| artifacts | SESSION_CONTEXT.artifacts | Markdown list with status icons |
| git status | `git status` command | "clean" or file count |
| blockers | SESSION_CONTEXT.blockers.length | Integer |
| next steps | SESSION_CONTEXT.next_steps | Numbered list |

## Status Icons

| Icon | Meaning |
|------|---------|
| ✓ | Completed |
| ⧗ | In progress |
| ✗ | Blocked |
| ⚠ | Warning (needs attention) |
