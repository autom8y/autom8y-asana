# Product Requirements Documents (PRDs)

## What Are PRDs?

Product Requirements Documents (PRDs) define **what** we're building and **why** it's valuable. They capture the business need, user stories, success criteria, and feature specifications before implementation begins.

## When to Create a PRD

Create a PRD for:
- New features or capabilities
- Significant enhancements to existing features
- Cross-cutting infrastructure changes
- Features requiring stakeholder approval

Do NOT create a PRD for:
- Bug fixes (unless architectural)
- Refactoring (use ADR instead)
- Documentation updates
- Dependency upgrades

## Naming Conventions

### Numbered PRDs (Legacy)
Format: `PRD-NNNN-descriptive-name.md`
Example: `PRD-0001-sdk-extraction.md`

Used for early sequential allocation. Preserved for git history.

### Named PRDs (Preferred)
Format: `PRD-FEATURE-NAME.md`
Example: `PRD-CACHE-INTEGRATION.md`

**Use named PRDs for all new documents.** They are:
- More searchable
- Self-documenting
- Easier to reference

## Status Lifecycle

Every PRD has a `status:` field in frontmatter. See [/docs/CONVENTIONS.md](../CONVENTIONS.md) for complete lifecycle specification.

Common status values:
1. **Draft** - Initial authoring, requirements gathering in progress
2. **Active** - Approved for implementation, work may be in progress
3. **Implemented** - Code complete, feature shipped
4. **Superseded** - Replaced by newer design (must link to replacement)
5. **Rejected** - Decided not to implement (must link to ADR)
6. **Archived** - Historical record, implementation complete and stable

**Critical Rule**: Status in frontmatter is the canonical source of truth. INDEX.md must match frontmatter.

## PRD-TDD Pairing

Every PRD should have a corresponding TDD (Technical Design Document):
- PRD defines WHAT and WHY
- TDD defines HOW

Pairings are tracked in [INDEX.md](../INDEX.md) "PRD" column.

## What Happened to PROMPT-* Files?

PROMPT-0-* and PROMPT-MINUS-1-* files are **orchestrator work coordination files**, not requirements. They have been moved to [`/docs/initiatives/`](../initiatives/).

If you're looking for an initiative kickoff prompt, check `/docs/initiatives/`.

## Archival Policy

When marking a PRD as **Superseded**, add prominent notice:

```markdown
> **SUPERSESSION NOTICE**: This document has been superseded by [PRD-XXXX](PRD-XXXX-new.md).
> The requirements below are no longer active. Refer to the replacement document for current design.
```

When marking a PRD as **Rejected**, add notice with decision reference:

```markdown
> **REJECTION NOTICE**: This feature was rejected per [ADR-XXXX](../decisions/ADR-XXXX.md).
> See the ADR for rationale. This document is retained for historical reference.
```

See [CONVENTIONS.md](../CONVENTIONS.md) for complete supersession and rejection guidance.

## Creating a New PRD

1. Copy template from existing PRD (e.g., PRD-CACHE-INTEGRATION.md)
2. Use named format: `PRD-FEATURE-NAME.md`
3. Fill out frontmatter with required fields:
   - `id`, `title`, `status`, `created`, `updated`
   - Optional: `paired_tdd`, `supersedes`, `superseded_by`, `related_adr`
4. Write sections: Problem, Solution, Requirements, Success Criteria
5. Add entry to [INDEX.md](../INDEX.md)
6. Create corresponding TDD in `/docs/design/`

## See Also

- [TDD README](../design/README.md) - How PRDs relate to TDDs
- [INDEX.md](../INDEX.md) - Full PRD registry
- [CONTRIBUTION-GUIDE.md](../CONTRIBUTION-GUIDE.md) - Documentation standards
