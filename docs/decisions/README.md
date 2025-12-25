# Architecture Decision Records (ADRs)

## What Are ADRs?

Architecture Decision Records (ADRs) document **significant technical decisions** and their rationale. They capture the context, options considered, decision made, and consequences—creating a historical record of why the system works the way it does.

## When to Create an ADR

Create an ADR for:
- Architectural patterns or framework choices
- Technology selection (libraries, protocols, data stores)
- API design decisions with long-term impact
- Trade-offs between competing approaches
- Changes to existing architectural decisions

Do NOT create an ADR for:
- Feature requirements (use PRD instead)
- Implementation details (document in code)
- Temporary workarounds
- Obvious or uncontroversial choices

## Naming Convention

Format: `ADR-XXXX-decision-title.md`

Examples:
- `ADR-0001-protocol-extensibility.md`
- `ADR-0016-cache-protocol-extension.md`
- `ADR-0019-staleness-detection-algorithm.md`

**Numbering**: Sequential, starting from 0001. Never reuse numbers, even for rejected or superseded ADRs.

## ADR Structure

All ADRs follow this format:

1. **Metadata** - Status, author, date, deciders, related documents
2. **Context** - What problem or constraint triggered this decision?
3. **Decision** - What did we decide to do?
4. **Rationale** - Why did we choose this option?
5. **Alternatives Considered** - What other options did we evaluate?
6. **Consequences** - What are the implications (positive and negative)?

## Status Lifecycle

Every ADR has a `status:` field in metadata. See [/docs/CONVENTIONS.md](../CONVENTIONS.md) for complete lifecycle specification.

Common status values:
1. **Proposed** - Decision under discussion, not yet accepted
2. **Accepted** - Decision approved and implemented
3. **Deprecated** - Decision no longer recommended (but not replaced)
4. **Superseded** - Decision replaced by newer ADR (must link to replacement)

**Important**: ADRs are historical records. Even superseded ADRs remain in the repository to preserve decision history.

## Relationship to Other Docs

ADRs often reference or are referenced by:
- **PRDs** - May reject a feature proposal (PRD links to ADR explaining why)
- **TDDs** - Provide architectural constraints for technical designs
- **Other ADRs** - Supersede or build upon previous decisions

ADRs answer "Why did we make this choice?" while TDDs answer "How does this work?"

## Creating a New ADR

1. Identify the next sequential ADR number:
   ```bash
   ls docs/decisions/ADR-*.md | tail -1
   ```
2. Copy template from existing ADR (e.g., ADR-0001-protocol-extensibility.md)
3. Use format: `ADR-XXXX-decision-title.md`
4. Fill out metadata (status, author, date, deciders)
5. Write sections: Context, Decision, Rationale, Alternatives, Consequences
6. Add references to related PRDs, TDDs, or other ADRs
7. Commit with message format: `docs(adr): Add ADR-XXXX decision-title`

## Archival Policy

**ADRs are rarely archived.** They serve as permanent historical record of architectural decisions, even after being superseded.

When marking an ADR as **Superseded**:
1. Update metadata: `status: "Superseded"`
2. Add `superseded_by` field with replacement ADR number
3. Add notice at top of document:

```markdown
> **SUPERSESSION NOTICE**: This decision has been superseded by [ADR-XXXX](ADR-XXXX-new.md).
> See the replacement ADR for current guidance. This document is retained for historical reference.
```

**Do not delete or move superseded ADRs.** They document the evolution of system architecture.

## Finding ADRs

ADRs are organized by:
- **Sequential number** - Browse chronologically
- **Topic** - Search by filename or content
- **Related documents** - Follow references from PRDs/TDDs

To find ADRs related to a feature:
```bash
grep -r "ADR-" docs/requirements/ docs/design/
```

## See Also

- [TDD README](../design/README.md) - How ADRs relate to technical designs
- [PRD README](../requirements/README.md) - How ADRs affect requirements
- [CONVENTIONS.md](../CONVENTIONS.md) - Documentation standards
- [INDEX.md](../INDEX.md) - Cross-document references
