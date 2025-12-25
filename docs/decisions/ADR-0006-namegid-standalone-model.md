# ADR-0006: NameGid as Standalone Frozen Model

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md), [TDD-0002](../design/TDD-0002-models-pagination.md), FR-SDK-036, [ADR-0005](ADR-0005-pydantic-model-config.md)

## Context

The PRD requires a `NameGid` model for lightweight resource references (FR-SDK-036). Asana API frequently returns compact resource objects containing only `gid`, `name`, and `resource_type`:

```json
{
  "assignee": {
    "gid": "12345",
    "name": "Alice Smith",
    "resource_type": "user"
  }
}
```

Currently, the Task model represents these as `dict[str, Any]`, which:
- Lacks type safety (no IDE autocomplete, no validation)
- Requires defensive coding (`task.assignee.get("gid")`)
- Makes the API harder to use correctly

We must decide:
1. Should NameGid inherit from `AsanaResource` or be standalone?
2. Should NameGid be mutable or frozen (immutable)?
3. What fields should be required vs optional?

Key considerations:
- `AsanaResource` requires `gid` and has optional `resource_type`
- NameGid needs `gid` (required), `name` (optional in some API responses), `resource_type` (optional)
- References appear in lists (projects, followers, tags) and may need deduplication
- Memory efficiency matters when loading many tasks with many references

## Decision

**NameGid is a standalone frozen Pydantic model, NOT inheriting from AsanaResource.**

```python
class NameGid(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
        frozen=True,  # Immutable
    )

    gid: str
    name: str | None = None
    resource_type: str | None = None

    def __hash__(self) -> int:
        return hash(self.gid)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, NameGid):
            return self.gid == other.gid
        return NotImplemented
```

### Key Properties

| Property | Value | Rationale |
|----------|-------|-----------|
| Inheritance | None (standalone) | Different semantics from full resources |
| Frozen | True | References shouldn't mutate; enables hashing |
| Hashable | Yes | Enables use in sets and dict keys for deduplication |
| Equality | Based on gid | Two refs to same resource are equal |
| extra | "ignore" | Forward compatibility per ADR-0005 |

## Rationale

### Why Standalone (Not Inheriting from AsanaResource)?

1. **Semantic difference**: A NameGid is a *reference* to a resource, not a *resource* itself. AsanaResource represents full resources with potential for additional fields.

2. **Field requirements differ**: AsanaResource was designed for full resources where we might want required fields (e.g., `name` required on Task). NameGid needs `name` to be optional because Asana sometimes returns minimal refs.

3. **Behavior differs**: NameGid should be frozen/hashable; AsanaResource should remain mutable for updates.

4. **Memory footprint**: Standalone model has less overhead than inheriting a base class with additional config.

5. **No shared behavior needed**: NameGid doesn't need methods from AsanaResource.

### Why Frozen?

1. **Immutability is correct**: A reference to "user 12345" shouldn't change. If you need a different reference, create a new one.

2. **Enables hashing**: Frozen Pydantic models are hashable, enabling:
   ```python
   # Deduplicate followers across multiple tasks
   all_followers = {f for task in tasks for f in task.followers or []}

   # Use as dict keys
   user_task_count = {task.assignee: 0 for task in tasks if task.assignee}
   ```

3. **Thread safety**: Immutable objects are inherently thread-safe.

4. **Matches mental model**: References are identifiers, not entities to modify.

### Why Custom __eq__ and __hash__?

1. **Identity by gid**: Two NameGid objects referring to the same resource (same gid) should be equal regardless of whether `name` was populated.

2. **API consistency**: Asana may return the same resource with different field populations:
   ```json
   {"gid": "123", "name": "Alice"}  // From one endpoint
   {"gid": "123"}                    // From another endpoint (compact)
   ```
   These should be equal because they reference the same resource.

3. **Set operations work correctly**:
   ```python
   ref1 = NameGid(gid="123", name="Alice")
   ref2 = NameGid(gid="123")  # Same resource, no name
   assert ref1 == ref2
   assert {ref1, ref2} == {ref1}  # Deduplicates
   ```

## Alternatives Considered

### Inherit from AsanaResource

- **Description**: `class NameGid(AsanaResource): ...`
- **Pros**:
  - Shared config (extra="ignore", etc.)
  - Consistent inheritance hierarchy
  - Could use AsanaResource methods if any existed
- **Cons**:
  - Wrong semantics (reference vs resource)
  - AsanaResource is mutable; would need to override
  - Inheritance for code sharing is an anti-pattern here
  - More complex to make frozen due to base class
- **Why not chosen**: Semantic mismatch. NameGid is not a resource.

### Keep as dict[str, Any]

- **Description**: Continue using untyped dicts for references
- **Pros**:
  - No code changes
  - Maximum flexibility
  - No validation overhead
- **Cons**:
  - No type safety
  - No IDE support
  - Defensive coding required
  - Doesn't satisfy FR-SDK-036
- **Why not chosen**: Typed model is explicitly required by PRD.

### Mutable NameGid

- **Description**: NameGid without frozen=True
- **Pros**:
  - Simpler (no custom __hash__)
  - Can modify after creation
- **Cons**:
  - Not hashable (can't use in sets/dicts)
  - Mutable reference is conceptually wrong
  - Thread safety concerns
- **Why not chosen**: References should be immutable identifiers.

### Named Tuple

- **Description**: Use `typing.NamedTuple` instead of Pydantic model
- **Pros**:
  - Automatically frozen and hashable
  - Minimal overhead
  - No Pydantic dependency
- **Cons**:
  - No validation
  - No extra="ignore" for forward compatibility
  - All fields required (or need defaults)
  - Doesn't integrate with Pydantic serialization
- **Why not chosen**: Need Pydantic validation and forward compatibility.

### Dataclass (frozen)

- **Description**: Use `@dataclass(frozen=True)` instead of Pydantic
- **Pros**:
  - Frozen and hashable
  - Standard library
  - Less overhead
- **Cons**:
  - No automatic validation
  - No extra="ignore" behavior
  - Doesn't integrate with Pydantic model hierarchy
  - Would need manual serialization logic
- **Why not chosen**: Need Pydantic's validation and serialization.

## Consequences

### Positive

- **Type safety**: IDE autocomplete, type checking for reference fields
- **Cleaner API**: `task.assignee.gid` instead of `task.assignee["gid"]`
- **Deduplication**: Can use sets for unique references
- **Dict keys**: Can index by reference
- **Validation**: Pydantic validates reference structure
- **Forward compatible**: Unknown fields in API response are ignored

### Negative

- **Breaking change**: Code using dict access (`task.assignee["gid"]`) must update
- **Migration effort**: Update all Task field accesses in autom8
- **Slightly more memory**: NameGid object vs dict (negligible)

### Neutral

- **Serialization unchanged**: `model_dump()` produces dict, same as before
- **Comparison semantics clear**: Equality by gid is documented and expected

## Compliance

To ensure this decision is followed:

1. **Type checking**: mypy enforces NameGid type on reference fields
2. **Code review**: Reject new `dict[str, Any]` for simple resource references
3. **Documentation**: Docstrings explain NameGid usage
4. **Migration guide**: Document dict-to-attribute access changes
5. **Tests**: Verify hashing, equality, and Pydantic integration
