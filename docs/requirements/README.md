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

Every PRD has a `status:` field in frontmatter:

1. **Draft** - Initial authoring, not yet reviewed
2. **In Review** - Under stakeholder review
3. **Approved** - Approved for implementation
4. **Active** - Currently being implemented
5. **Implemented** - Code in production, feature live
6. **Superseded** - Replaced by different approach (includes link to replacement)
7. **Rejected** - Decided not to implement (includes decision rationale)

**Critical Rule**: STATUS in INDEX.md MUST match status in document frontmatter.

## PRD-TDD Pairing

Every PRD should have a corresponding TDD (Technical Design Document):
- PRD defines WHAT and WHY
- TDD defines HOW

Pairings are tracked in [INDEX.md](../INDEX.md) "PRD" column.

## What Happened to PROMPT-* Files?

PROMPT-0-* and PROMPT-MINUS-1-* files are **orchestrator work coordination files**, not requirements. They have been moved to [`/docs/initiatives/`](../initiatives/).

If you're looking for an initiative kickoff prompt, check `/docs/initiatives/`.

## Creating a New PRD

1. Copy template from existing PRD (e.g., PRD-CACHE-INTEGRATION.md)
2. Use named format: `PRD-FEATURE-NAME.md`
3. Fill out frontmatter (status, created, updated)
4. Write sections: Problem, Solution, Requirements, Success Criteria
5. Add entry to [INDEX.md](../INDEX.md)
6. Create corresponding TDD in `/docs/design/`

## See Also

- [TDD README](../design/README.md) - How PRDs relate to TDDs
- [INDEX.md](../INDEX.md) - Full PRD registry
- [CONTRIBUTION-GUIDE.md](../CONTRIBUTION-GUIDE.md) - Documentation standards
