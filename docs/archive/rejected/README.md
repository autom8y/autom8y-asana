# Rejected Proposals Archive

> PRDs and TDDs for approaches that were explicitly rejected or marked as NO-GO.

## Archived: 2025-12-25

These documents represent proposals that were evaluated and rejected. They are preserved for historical context but should not be used as implementation guidance.

## Contents

### PRD-0021-async-method-generator.md
**Status**: Rejected
**Reason**: The `@async_method` decorator pattern was chosen instead
**See**: Current async patterns in codebase

### PRD-0022-crud-base-class.md
**Status**: Explicit NO-GO
**Reason**: See TDD-0026 evaluation document
**Decision**: CRUD operations remain in individual entity classes

### TDD-0026-crud-base-class-evaluation.md
**Status**: NO-GO Decision Document
**Reason**: Evaluation concluded base class approach creates more problems than it solves
**Decision**: Maintain current explicit CRUD patterns per entity type

## Why These Were Rejected

These proposals represent valid engineering ideas that, upon evaluation, were determined to be:
- Not aligned with project architecture
- Creating unnecessary abstraction
- Solving problems that don't exist
- Introducing complexity without proportional benefit

## Using This Archive

If someone proposes similar approaches in the future, these documents provide:
1. Prior art showing the idea was considered
2. Rationale for why it was rejected
3. Context to avoid re-evaluating settled decisions

## Related ADRs

- ADR-0XXX (if applicable - add cross-reference if an ADR captures the decision)
