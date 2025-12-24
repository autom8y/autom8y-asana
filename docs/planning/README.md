# Planning Documentation

## What Are Planning Docs?

Planning documents are temporary artifacts created during sprint planning, session planning, and other work coordination activities. Unlike formal PRDs and TDDs, planning docs are ephemeral and archived after completion.

## Planning Doc Types

### Sprint Decompositions
Location: [`/docs/planning/sprints/`](sprints/)

Sprint-specific decompositions of larger initiatives into actionable work items:
- `PRD-SPRINT-N-description.md` - Sprint requirements
- `TDD-SPRINT-N-description.md` - Sprint technical approach

These docs help teams break down complex features into sprint-sized chunks.

### Session Notes
Location: `/docs/planning/sessions/` (if created)

Notes from planning sessions, design sessions, or retrospectives.

## How Planning Docs Differ from Formal Docs

| Planning Doc | PRD/TDD |
|--------------|---------|
| Temporary planning artifact | Permanent feature specification |
| Sprint or session specific | Feature lifecycle |
| Archived after 2 weeks | Preserved for history |
| Operational coordination | Requirements and design |

**For permanent feature documentation**, see [`/docs/requirements/`](../requirements/) (PRDs) and [`/docs/design/`](../design/) (TDDs).

## Archival Policy

Planning docs are archived after completion:

### Sprint Docs
Archive 2 weeks after sprint end:

```bash
git mv planning/sprints/PRD-SPRINT-N-*.md .archive/planning/2025-Q4-sprints/
```

### Session Notes
Archive 1 month after session (if not actively referenced).

## See Also

- [Sprint Planning README](sprints/README.md) - Sprint decomposition details
- [PRD README](../requirements/README.md) - Formal requirements
- [TDD README](../design/README.md) - Formal technical design
