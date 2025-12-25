# Technical Design Documents (TDDs)

## What Are TDDs?

Technical Design Documents (TDDs) define **how** we implement features. They specify architecture, components, interfaces, data structures, and testing strategies.

## When to Create a TDD

Create a TDD for:
- Every feature with a corresponding PRD
- Significant architectural changes
- Complex technical implementations
- Features requiring design review

Every TDD should have a corresponding PRD. The PRD answers "what and why," the TDD answers "how."

## Naming Conventions

### Numbered TDDs (Legacy)
Format: `TDD-NNNN-descriptive-name.md`
Example: `TDD-0001-sdk-architecture.md`

Used for early sequential allocation. Preserved for git history.

### Named TDDs (Preferred)
Format: `TDD-FEATURE-NAME.md`
Example: `TDD-CACHE-INTEGRATION.md`

**Use named TDDs for all new documents.** Match the corresponding PRD name for clarity.

## Status Lifecycle

Every TDD has a `status:` field in frontmatter. See [/docs/CONVENTIONS.md](../CONVENTIONS.md) for complete lifecycle specification.

Common status values:
1. **Draft** - Initial design, not yet reviewed
2. **In Review** - Under technical review
3. **Approved** - Approved for implementation
4. **Active** - Currently being implemented
5. **Implemented** - Code in production, feature live
6. **Superseded** - Replaced by different approach (must link to replacement)
7. **Rejected** - Decided not to implement (must link to ADR)

**Critical Rule**: Status in frontmatter is the canonical source of truth. INDEX.md must match frontmatter.

## PRD-TDD Pairing

[INDEX.md](../INDEX.md) is the source of truth for PRD-TDD pairings. Every TDD entry includes a "PRD" column linking to its corresponding PRD.

**Example pairing**:
- PRD: [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md)
- TDD: [TDD-CACHE-INTEGRATION](TDD-CACHE-INTEGRATION.md)

## When TDD Precedes PRD

In rare cases, exploratory technical designs may be written before formal requirements:
- Spike investigations
- Technical feasibility studies
- Prototype evaluations

These TDDs may have `status: Draft` or `status: NO-GO` if the approach is rejected.

## Architecture vs. Implementation TDDs

**Architecture TDDs** define high-level system design:
- Component boundaries
- Integration patterns
- Technology selection

**Implementation TDDs** define detailed technical approach:
- Class structures
- API signatures
- Error handling

Both are valid. Choose based on the scope of the feature.

## Creating a New TDD

1. Verify corresponding PRD exists (or create it)
2. Copy template from existing TDD (e.g., TDD-CACHE-INTEGRATION.md)
3. Use named format: `TDD-FEATURE-NAME.md` (match PRD name)
4. Fill out frontmatter (status, created, updated)
5. Write sections: Architecture Overview, Components, Interfaces, Data Structures, Error Handling, Testing Strategy
6. Add entry to [INDEX.md](../INDEX.md) with PRD reference

## Archival Policy

When marking a TDD as **Superseded**, add prominent notice:

```markdown
> **SUPERSESSION NOTICE**: This document has been superseded by [TDD-XXXX](TDD-XXXX-new.md).
> The design below is no longer active. Refer to the replacement document for current architecture.
```

When marking a TDD as **Rejected**, add notice with decision reference:

```markdown
> **REJECTION NOTICE**: This design was rejected per [ADR-XXXX](../decisions/ADR-XXXX.md).
> See the ADR for rationale. This document is retained for historical reference.
```

## Consolidated Family Summaries

For related features that evolved through multiple design iterations, we create consolidated "Family" summaries that synthesize the technical evolution:

- **[TDD-SDK-FAMILY.md](TDD-SDK-FAMILY.md)** - SDK design evolution (Foundation → Expansion → Hardening → Validation)
  - Archived: TDD-0001, TDD-0012, TDD-0014, TDD-0029

These summaries preserve architectural decisions and patterns while reducing file count. Original documents are archived in `docs/.archive/2025-12-tdds/`.

## See Also

- [PRD README](../requirements/README.md) - How TDDs relate to PRDs
- [INDEX.md](../INDEX.md) - Full TDD registry
- [CONTRIBUTION-GUIDE.md](../CONTRIBUTION-GUIDE.md) - Documentation standards

TDDs are rarely archived - they serve as historical design record even after implementation. See [CONVENTIONS.md](../CONVENTIONS.md) for complete archival guidance.
