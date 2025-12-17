# Glossary

> Core terminology. SDK-specific terms are in `autom8-asana-domain/glossary.md`.

---

## How to Use

- **When writing**: Use exact terms, not synonyms
- **SDK terms**: See `skills/autom8-asana-domain/glossary.md`
- **When introducing new concepts**: Add here or to skill glossary

---

## Core Terms

### SaveSession

Unit of Work pattern for batched Asana operations. See skill glossary for details.

### GID

Asana's globally unique identifier. Format: numeric string (e.g., `"1234567890123456"`).

### ActionOperation

Operation using Asana's action endpoints (add_tag, move_to_section, etc.).

---

## Document Acronyms

| Acronym | Expansion | Definition |
|---------|-----------|------------|
| PRD | Product Requirements Document | Defines what and why |
| TDD | Technical Design Document | Defines how (architecture) |
| ADR | Architecture Decision Record | Captures why a decision was made |
| NFR | Non-Functional Requirement | Quality attributes |

---

## Anti-Glossary

| Avoid | Use Instead | Why |
|-------|-------------|-----|
| "User" (ambiguous) | Customer, Admin, Assignee | Different contexts |
| "Data" (vague) | Specify: records, payload, etc. | Too generic |
| "System" (vague) | Name the component | Unclear scope |
| "Handle" (vague) | process, validate, transform | Unclear action |

---

## Full SDK Glossary

For comprehensive SDK terminology including:
- SaveSession, EntityState, PlannedOperation
- ChangeTracker, DependencyGraph
- CacheProtocol, AuthProtocol
- opt_fields, Membership, Batch Request

See: `skills/autom8-asana-domain/glossary.md`
