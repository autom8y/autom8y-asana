# ADR-0144: HealingResult Type Consolidation

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-19
- **Deciders**: Architect, Engineering Lead
- **Related**: ADR-0095 (Self-Healing Integration), ADR-0118 (Self-Healing Design), TDD-SPRINT-5-CLEANUP

## Context

The codebase has two `HealingResult` dataclasses with different attributes serving different contexts:

| Location | Attributes | Purpose |
|----------|------------|---------|
| `healing.py:50` | `entity_gid`, `expected_project_gid`, `success`, `dry_run`, `error: Exception` | Standalone healing functions |
| `models.py:375` | `entity_gid`, `entity_type`, `project_gid`, `success`, `error: str` | SaveSession healing integration |

This creates confusion:
1. Which type to import depends on calling context
2. Different attribute names for same concept (`expected_project_gid` vs `project_gid`)
3. Different error types (`Exception` vs `str`)
4. `healing.py` must import `models.HealingResult` as `ModelHealingResult` to avoid conflict

Per TDD-SPRINT-5-CLEANUP (FR-ABS-001): Consolidate to single source of truth.

## Decision

**Consolidate to a single `HealingResult` in `models.py`** with unified attributes supporting both contexts.

```python
@dataclass(frozen=True, slots=True)
class HealingResult:
    """Outcome of a healing operation.

    Per ADR-0095/0118/0120: Unified result for all healing contexts.
    """
    entity_gid: str
    entity_type: str       # Added: useful for logging/debugging
    project_gid: str       # Renamed: shorter than expected_project_gid
    success: bool
    dry_run: bool = False  # Added: needed for standalone API
    error: str | None = None  # Changed: str for serialization

    def __bool__(self) -> bool:
        """Return True if healing succeeded."""
        return self.success
```

**Key design choices:**

1. **`entity_type: str`** - Added from `models.py` version; valuable for logging and debugging
2. **`project_gid: str`** - Renamed from `expected_project_gid` for brevity (both mean the same thing)
3. **`dry_run: bool = False`** - Added from `healing.py` version; needed for `heal_entity_async()` API
4. **`error: str | None`** - Changed from `Exception` to `str` for serialization and simpler API
5. **`__bool__`** - Added for truthiness testing (`if result:`)

## Rationale

1. **Single source of truth**: One type reduces cognitive load and import confusion
2. **Superset design**: Unified type has all attributes needed by both contexts
3. **String errors**: Converting Exception to str at creation time:
   - Simplifies serialization (can be JSON-encoded)
   - Avoids carrying exception objects through the system
   - Exception message is the useful part anyway
4. **Slot optimization preserved**: `frozen=True, slots=True` for immutability and memory efficiency
5. **`models.py` as canonical home**: This is where all other persistence result types live (`SaveResult`, `ActionResult`, etc.)

## Alternatives Considered

### Alternative 1: Keep Both Types

- **Description**: Rename one to `StandaloneHealingResult` vs `SessionHealingResult`
- **Pros**: No migration needed
- **Cons**: Perpetuates confusion, two types to maintain, unclear which to use
- **Why not chosen**: Complexity is not justified; use cases are not different enough

### Alternative 2: Keep Exception in Error Field

- **Description**: Use `error: Exception | str | None` union type
- **Pros**: Preserves full exception information
- **Cons**: Complex type, hard to serialize, callers must handle both types
- **Why not chosen**: Exception message is sufficient; full stacktrace can be logged at source

### Alternative 3: Abstract Protocol

- **Description**: Define `HealingResultProtocol` with common attributes, keep both implementations
- **Pros**: Allows polymorphic handling
- **Cons**: Over-engineered for internal API; no code needs polymorphic healing results
- **Why not chosen**: YAGNI - no current need for protocol-based abstraction

## Consequences

### Positive
- Single import: `from autom8_asana.persistence.models import HealingResult`
- Consistent attributes across all healing contexts
- Cleaner code in `healing.py` (no more `ModelHealingResult` alias)
- Serializable error messages

### Negative
- Breaking change for `heal_entity_async()` return type (error is now `str | None`, not `Exception | None`)
- Callers using `.error` must handle string instead of exception
- Migration effort (small - update 2 files)

### Neutral
- Tests need update to reflect new attributes
- Documentation needs update

## Migration Path

1. Update `models.py` HealingResult with unified attributes
2. Remove `healing.py` HealingResult class
3. Update `healing.py` to import from models
4. Update `heal_entity_async()` to convert Exception to str before storing
5. Update tests to use new attribute names
6. Run full test suite

## Compliance

- [ ] TDD-SPRINT-5-CLEANUP FR-ABS-001 addressed
- [ ] healing.py imports from models.py
- [ ] All healing-related tests pass
- [ ] Documentation updated
