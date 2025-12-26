# ADR-0071: Resolution Ambiguity Handling

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: Architect
- **Related**: PRD-RESOLUTION (Q1), TDD-RESOLUTION, ADR-0040 (Partial Failure Handling)

## Context

When resolving an AssetEdit to its owning Unit, a resolution strategy may find multiple matching Units. For example, the CUSTOM_FIELD_MAPPING strategy matches AssetEdit.vertical to Unit.vertical, but multiple Units could share the same vertical.

**Question from PRD (Q1)**: Should ambiguous results return first match or None in the `entity` field?

### Use Cases

1. **Webhook handler**: Needs some Unit for context, even if ambiguous
2. **Reporting aggregation**: May want to filter out ambiguous results
3. **Manual resolution**: User can inspect candidates and choose

### Forces

1. **Convenience**: Returning first match allows simple code paths for callers who don't care
2. **Correctness**: Returning None is "safer" and forces callers to handle ambiguity
3. **Transparency**: `ambiguous` flag and `candidates` list provide full information either way
4. **Consistency**: Similar patterns in other systems (e.g., database queries) often return first match

## Decision

**Ambiguous results return the first match in the `entity` field**, with `ambiguous=True` and all matches in `candidates`.

### Implementation

```python
@dataclass
class ResolutionResult(Generic[T]):
    entity: T | None = None           # First match (for convenience)
    strategy_used: ResolutionStrategy | None = None
    strategies_tried: list[ResolutionStrategy] = field(default_factory=list)
    ambiguous: bool = False           # True if multiple matches
    candidates: list[T] = field(default_factory=list)  # All matches
    error: str | None = None

    @property
    def success(self) -> bool:
        """True only if exactly one match (not ambiguous)."""
        return self.entity is not None and not self.ambiguous
```

### Behavior

```python
# Example: Two Units match the vertical
result = await asset_edit.resolve_unit_async(client)

result.entity        # First matching Unit (not None)
result.ambiguous     # True
result.success       # False (ambiguous is not success)
result.candidates    # [Unit1, Unit2]

# Caller can choose:
if result.success:
    # Unambiguous - use entity directly
    unit = result.entity
elif result.ambiguous:
    # Multiple matches - caller decides
    unit = result.candidates[0]  # Or prompt user, or filter further
else:
    # No match found
    handle_no_match()
```

### Strategy Priority Order

To minimize ambiguity, strategies are ordered by reliability:

1. **DEPENDENT_TASKS** (most reliable): Task dependencies encode explicit relationships
2. **CUSTOM_FIELD_MAPPING**: Vertical matching may have duplicates
3. **EXPLICIT_OFFER_ID**: Direct reference, but may be stale

AUTO mode continues to the next strategy if ambiguity is found, seeking a non-ambiguous result.

## Rationale

**Why return first match instead of None?**

1. **Pragmatic**: Many callers only need "a" Unit for context, even if not certain
2. **Progressive disclosure**: Simple callers get simple behavior; sophisticated callers check `ambiguous`
3. **No information loss**: All candidates are available for inspection
4. **Matches user mental model**: "Find the Unit" suggests returning something if found

**Why not fail on ambiguity?**

1. **Ambiguity is not an error**: Finding multiple matches is a valid outcome
2. **Caller control**: Different use cases handle ambiguity differently
3. **Composability**: Batch operations can aggregate ambiguous results

## Alternatives Considered

### Option A: Return None on Ambiguity

- **Description**: `entity=None` when `ambiguous=True`
- **Pros**: Forces callers to handle ambiguity; cleaner semantics
- **Cons**: Requires extra code for common "just give me something" use case
- **Why not chosen**: Adds friction for simple use cases; information available via `candidates[0]`

### Option B: Raise Exception on Ambiguity

- **Description**: Throw `AmbiguousResolutionError` when multiple matches found
- **Pros**: Fail-fast; makes ambiguity explicit
- **Cons**: Breaks simple iteration over collections; conflates "error" with "multiple matches"
- **Why not chosen**: Ambiguity is a normal outcome, not an exceptional condition

### Option C: Return All Matches as Entity

- **Description**: `entity: T | list[T]` depending on count
- **Pros**: Direct access to all matches
- **Cons**: Type instability; caller must check type; breaks generic usage
- **Why not chosen**: Poor API ergonomics; union types are harder to work with

## Consequences

### Positive

- **Simple default path**: `result.entity` always usable when `entity is not None`
- **Explicit ambiguity detection**: `result.ambiguous` and `result.success` separate concerns
- **Full transparency**: `candidates` provides all matches for advanced use cases
- **Composable**: Works well with batch operations

### Negative

- **Possible misuse**: Callers might ignore `ambiguous` flag and assume entity is authoritative
- **Non-deterministic order**: "First match" depends on iteration order (could be arbitrary)

### Neutral

- Logging includes candidate count for debugging ambiguous results
- AUTO mode prefers non-ambiguous results when continuing to next strategy

## Compliance

- `ResolutionResult.success` MUST return False when `ambiguous=True`
- `entity` MUST be set to first candidate when ambiguous (not None)
- `candidates` MUST contain all matching entities, including the one in `entity`
- Logging MUST include candidate count when result is ambiguous
- Documentation MUST explain that `entity` may not be authoritative when `ambiguous=True`
