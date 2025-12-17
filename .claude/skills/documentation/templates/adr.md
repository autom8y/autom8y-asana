# ADR (Architecture Decision Record) Template

## When to Create an ADR

**Owner**: Architect (primary), Engineer (implementation-level)
**Location**: `/docs/decisions/ADR-{NNNN}-{slug}.md`
**Purpose**: Captures WHY a specific architectural decision was made. Provides context for future maintainers.

Create an ADR when:
- Choosing between multiple viable approaches
- Adopting a new pattern, library, or technology
- Deviating from established patterns
- Making trade-offs with long-term implications
- Any decision someone might later ask "why did we do it this way?"

---

## Template

```markdown
# ADR-{NNNN}: {Decision Title}

## Metadata
- **Status**: Proposed | Accepted | Deprecated | Superseded by ADR-{NNNN}
- **Author**: {name}
- **Date**: {date}
- **Deciders**: {who was involved in the decision}
- **Related**: PRD-{NNNN}, TDD-{NNNN}, ADR-{NNNN}

## Context
What is the situation? What forces are at play? What problem or question triggered this decision?

## Decision
What is the decision? State it clearly and directly.

## Rationale
Why this decision over the alternatives? What trade-offs were considered?

## Alternatives Considered

### {Alternative 1}
- **Description**: {What this option entails}
- **Pros**: {Benefits}
- **Cons**: {Drawbacks}
- **Why not chosen**: {Specific reason}

### {Alternative 2}
- **Description**: {What this option entails}
- **Pros**: {Benefits}
- **Cons**: {Drawbacks}
- **Why not chosen**: {Specific reason}

## Consequences
What are the implications of this decision?
- **Positive**: {Good outcomes}
- **Negative**: {Costs, risks, or limitations we're accepting}
- **Neutral**: {Other effects}

## Compliance
How do we ensure this decision is followed?
- {Linting rules, PR checklist items, architectural tests, etc.}
```

---

## Quality Gates

An ADR is ready for approval when:

- [ ] Context clearly explains the situation
- [ ] Decision is stated unambiguously
- [ ] Alternatives were genuinely considered
- [ ] Rationale explains why this choice
- [ ] Consequences (positive and negative) are honest
