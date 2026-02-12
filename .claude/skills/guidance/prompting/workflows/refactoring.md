# Complete Workflow: Refactoring (No Behavior Change)

> Structural improvements without changing functionality

---

## Context

Analytics service has grown too large—needs decomposition.

## Session

**Prompt:**
```
Act as the Architect, then Engineer.

/src/domain/services/analytics_service.py is 800 lines and does too much:
- Dashboard metrics
- Report generation
- Data export
- Alert threshold checking

Design a decomposition:
1. What services should this become?
2. What's the dependency structure?
3. How do we migrate incrementally without breaking things?

Create ADR-0010 for the decomposition decision.
Then implement Phase 1 as Engineer.

Constraint: All existing tests must pass after each change.
No behavior changes—this is purely structural.
```

**Expected Output:**
- ADR documenting why we're splitting and how
- Phased migration plan
- Phase 1 implementation (extract first service)
- Verification that tests still pass

---

## Refactoring Constraints

1. **Tests must exist first** - If no tests, add them before refactoring
2. **Incremental changes** - Each step should pass tests
3. **No feature creep** - Resist adding features during refactoring
4. **Document decisions** - ADR explains the "why"

---

## Signs You Need This Workflow

- File exceeds 500 lines
- Class has more than one clear responsibility
- "God object" accumulating unrelated methods
- Circular dependencies emerging
- Hard to test in isolation

