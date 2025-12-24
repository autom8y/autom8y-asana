# Sprint Decomposition Documentation

## What Are Sprint Decomposition Docs?

Sprint decomposition docs break down larger initiatives into sprint-sized work items. They help teams plan and execute complex features incrementally.

## Sprint Doc Types

### PRD-SPRINT-N Files
Format: `PRD-SPRINT-N-description.md`

Sprint-specific requirements decompositions:
- What features/stories are included in this sprint
- How they relate to the parent PRD
- Sprint-specific acceptance criteria
- Dependencies and blockers

Example: `PRD-SPRINT-1-PATTERN-COMPLETION.md`

### TDD-SPRINT-N Files
Format: `TDD-SPRINT-N-description.md`

Sprint-specific technical approach:
- How to implement sprint features
- Technical tasks and estimates
- Integration points with existing code
- Testing approach for sprint deliverables

Example: `TDD-SPRINT-1-PATTERN-COMPLETION.md`

## How Sprint Docs Relate to Formal PRDs/TDDs

Sprint docs are **temporary decompositions** of formal PRDs/TDDs:

**Parent PRD/TDD** (permanent):
- [PRD-CACHE-OPTIMIZATION-P2](../../requirements/PRD-CACHE-OPTIMIZATION-P2.md)

**Sprint Decompositions** (temporary):
- [PRD-SPRINT-3-DETECTION-DECOMPOSITION](PRD-SPRINT-3-DETECTION-DECOMPOSITION.md)
- [TDD-SPRINT-3-DETECTION-DECOMPOSITION](TDD-SPRINT-3-DETECTION-DECOMPOSITION.md)

The parent PRD/TDD defines the **full feature**. Sprint docs define **this sprint's scope**.

## When to Create Sprint Docs

Create sprint decomposition docs when:
- Parent feature is too large for single sprint
- Team needs to plan incremental delivery
- Sprint planning requires technical breakdown
- Dependencies span multiple sprints

Do NOT create sprint docs for:
- Simple features (1 sprint or less)
- Bug fixes
- Maintenance work

## Archival Policy

Sprint docs are archived **2 weeks after sprint end**:

```bash
git mv planning/sprints/PRD-SPRINT-N-*.md .archive/planning/2025-Q4-sprints/
git mv planning/sprints/TDD-SPRINT-N-*.md .archive/planning/2025-Q4-sprints/
```

This keeps the active planning directory focused on current and upcoming sprints.

## Current Sprint Docs

Check this directory for active sprint decompositions. Archived sprints are in [`.archive/planning/`](../../.archive/planning/).

## See Also

- [Planning README](../README.md) - Planning documentation overview
- [PRD README](../../requirements/README.md) - Formal requirements
- [TDD README](../../design/README.md) - Formal technical design
