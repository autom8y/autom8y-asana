# TDD: Dynamic Field Normalization

## Overview

This design replaces the static `LEGACY_FIELD_MAPPING` dictionary with a dynamic hierarchical field normalization algorithm. The new approach uses entity aliasing to resolve field names through semantic domain relationships, eliminating per-field maintenance while providing bidirectional resolution.

## Context

**PRD Reference**: N/A (Technical debt refinement)

**Spike Reference**: `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-dynamic-field-normalization.md`

**Target Module**: `src/autom8_asana/services/resolver.py`

### Current Problem

The existing `LEGACY_FIELD_MAPPING` requires manual maintenance:

```python
LEGACY_FIELD_MAPPING = {
    "contact": {"email": "contact_email", "phone": "contact_phone"},
    "unit": {"phone": "office_phone"},
    "business": {"phone": "office_phone"},
    "offer": {"phone": "office_phone"},
}
```

**Issues**:
1. Manual maintenance burden for each new field
2. Prone to reversal bugs (recently fixed `contact_email` -> `email` being backwards)
3. Does not scale as schemas evolve
4. Hard to reason about mapping direction

### Design Goal

Replace static mappings with a semantic algorithm that:
1. Resolves fields through entity type hierarchy
2. Handles both `phone` -> `office_phone` AND `office_phone` -> `phone`
3. Requires zero per-field maintenance
4. Uses schema introspection for validation

## System Design

### Architecture Diagram

```
                             ┌─────────────────────────┐
                             │   _apply_legacy_mapping │
                             │      (entry point)      │
                             └────────────┬────────────┘
                                          │
                                          ▼
                             ┌─────────────────────────┐
                             │   SchemaRegistry        │
                             │   .get_schema()         │
                             │   .column_names()       │
                             └────────────┬────────────┘
                                          │
                                          ▼
                             ┌─────────────────────────┐
                             │   _normalize_field()    │
                             │   (per field)           │
                             └────────────┬────────────┘
                                          │
         ┌────────────────────────────────┼────────────────────────────────┐
         │                                │                                │
         ▼                                ▼                                ▼
┌─────────────────┐           ┌─────────────────────┐          ┌─────────────────────┐
│ 1. Exact Match  │           │ 2. Prefix Expansion │          │ 3. Prefix Removal   │
│   field in set  │           │   {entity}_{field}  │          │   strip {entity}_   │
└─────────────────┘           └─────────────────────┘          └─────────────────────┘
                                          │
                                          ▼
                             ┌─────────────────────────┐
                             │ 4. Alias Resolution     │
                             │    ENTITY_ALIASES       │
                             └────────────┬────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     ▼                     ▼
         ┌─────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
         │ 4a. Direct      │   │ 4b. Decomposition   │   │ (fallback)          │
         │ {alias}_{field} │   │ parent = rsplit("_")│   │ return unchanged    │
         └─────────────────┘   │ recurse to parent   │   └─────────────────────┘
                               └─────────────────────┘
```

### Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `ENTITY_ALIASES` | Semantic entity hierarchy definition | `resolver.py` (module constant) |
| `_normalize_field()` | Single field resolution with recursion | `resolver.py` (private function) |
| `_apply_legacy_mapping()` | Entry point, iterates criterion fields | `resolver.py` (existing, modified) |
| `SchemaRegistry` | Provides available field names | `dataframes/models/registry.py` (unchanged) |

### Data Model

#### ENTITY_ALIASES Constant

```python
ENTITY_ALIASES: dict[str, list[str]] = {
    "unit": ["business_unit"],      # unit IS-A business_unit
    "offer": ["business_offer"],    # offer IS-A business_offer
    "business": ["office"],         # business USES office_ prefix
    "contact": [],                  # contact uses its own prefix
}
```

**Semantic Interpretation**:
- `unit` is a type of `business_unit` (child relationship)
- `offer` is a type of `business_offer` (child relationship)
- `business` fields use the `office_` prefix in the schema
- `contact` has no aliases (uses `contact_` prefix directly)

**Resolution Chain**:
```
unit -> business_unit -> business -> office
offer -> business_offer -> business -> office
```

### Interface Design

#### _normalize_field() Function

```python
def _normalize_field(
    field_name: str,
    entity_type: str,
    available_fields: set[str],
    _visited: set[str] | None = None,
) -> str:
    """Normalize a single field name using hierarchical alias resolution.

    Args:
        field_name: The field name from the criterion (e.g., "phone", "email").
        entity_type: The entity type context (e.g., "contact", "unit").
        available_fields: Set of valid schema column names from SchemaRegistry.
        _visited: Internal set tracking visited entities to prevent infinite recursion.

    Returns:
        Normalized field name. Returns unchanged if no resolution found
        (validation will catch invalid fields downstream).

    Raises:
        No exceptions raised. Invalid fields pass through unchanged.
    """
```

#### _apply_legacy_mapping() Function (Updated)

```python
def _apply_legacy_mapping(
    entity_type: str,
    criterion: dict[str, Any],
) -> dict[str, Any]:
    """Apply field normalization with hierarchical alias resolution.

    Replaces static LEGACY_FIELD_MAPPING with dynamic algorithm.

    Args:
        entity_type: Entity type for context (e.g., "unit", "contact").
        criterion: Original criterion dict with field -> value pairs.

    Returns:
        New dict with fields normalized to schema column names.
    """
```

## Algorithm Specification

### Resolution Order (5 Steps)

```
Given: field_name, entity_type, available_fields, _visited

1. RECURSION GUARD
   if entity_type in _visited:
       return field_name  # Terminate recursion
   _visited = _visited | {entity_type}

2. EXACT MATCH
   if field_name in available_fields:
       return field_name

3. PREFIX EXPANSION
   prefixed = f"{entity_type}_{field_name}"
   if prefixed in available_fields:
       return prefixed

4. PREFIX REMOVAL
   prefix = f"{entity_type}_"
   if field_name.startswith(prefix):
       stripped = field_name[len(prefix):]
       if stripped in available_fields:
           return stripped

5. ALIAS RESOLUTION
   for alias in ENTITY_ALIASES.get(entity_type, []):
       # 5a. Direct alias expansion
       alias_prefixed = f"{alias}_{field_name}"
       if alias_prefixed in available_fields:
           return alias_prefixed

       # 5b. Alias decomposition (recurse to parent)
       if "_" in alias:
           parent = alias.rsplit("_", 1)[0]  # "business_unit" -> "business"
           result = _normalize_field(field_name, parent, available_fields, _visited)
           if result in available_fields:
               return result

6. FALLBACK
   return field_name  # Unchanged; validation catches invalid
```

### Implementation Reference

```python
from typing import Any

# Entity type aliases - semantic domain hierarchy
ENTITY_ALIASES: dict[str, list[str]] = {
    "unit": ["business_unit"],      # unit is a business_unit
    "offer": ["business_offer"],    # offer is a business_offer
    "business": ["office"],         # business fields use office_ prefix
    "contact": [],                  # contact uses its own prefix
}


def _normalize_field(
    field_name: str,
    entity_type: str,
    available_fields: set[str],
    _visited: set[str] | None = None,
) -> str:
    """Normalize a single field name using hierarchical alias resolution."""
    # 1. Recursion guard
    if _visited is None:
        _visited = set()
    if entity_type in _visited:
        return field_name
    _visited = _visited | {entity_type}

    # 2. Exact match
    if field_name in available_fields:
        return field_name

    # 3. Prefix expansion: {entity}_{field}
    prefixed = f"{entity_type}_{field_name}"
    if prefixed in available_fields:
        return prefixed

    # 4. Prefix removal: strip {entity}_
    prefix = f"{entity_type}_"
    if field_name.startswith(prefix):
        stripped = field_name[len(prefix):]
        if stripped in available_fields:
            return stripped

    # 5. Alias resolution
    for alias in ENTITY_ALIASES.get(entity_type, []):
        # 5a. Direct alias expansion: {alias}_{field}
        alias_prefixed = f"{alias}_{field_name}"
        if alias_prefixed in available_fields:
            return alias_prefixed

        # 5b. Alias decomposition: recurse to parent
        if "_" in alias:
            parent = alias.rsplit("_", 1)[0]
            result = _normalize_field(field_name, parent, available_fields, _visited)
            if result in available_fields:
                return result

    # 6. Fallback: return unchanged
    return field_name


def _apply_legacy_mapping(
    entity_type: str,
    criterion: dict[str, Any],
) -> dict[str, Any]:
    """Apply field normalization with hierarchical alias resolution."""
    from autom8_asana.dataframes.models.registry import SchemaRegistry

    # Get available fields from schema
    schema_registry = SchemaRegistry.get_instance()
    schema_key = entity_type.title()
    try:
        schema = schema_registry.get_schema(schema_key)
        available_fields = set(schema.column_names())
    except Exception:
        available_fields = set()

    # Normalize each field
    return {
        _normalize_field(field_name, entity_type, available_fields): value
        for field_name, value in criterion.items()
    }
```

## Edge Cases

### Unknown Entity Types

**Scenario**: `entity_type` not in `ENTITY_ALIASES`

**Behavior**: Algorithm still applies steps 1-4 (exact match, prefix expansion, prefix removal). Only alias resolution (step 5) is skipped. Returns field unchanged if no match.

**Example**:
```python
# entity_type="unknown", field_name="foo", available_fields={"foo"}
# Result: "foo" (exact match in step 2)
```

### Missing Schema

**Scenario**: `SchemaRegistry.get_schema()` raises exception

**Behavior**: `available_fields` becomes empty set. All normalization steps fail (no matches possible). Fields pass through unchanged. Validation in `validate_criterion_for_entity()` will catch invalid fields downstream.

**Example**:
```python
# entity_type="nonexistent", available_fields=set()
# Result: all fields unchanged
```

### Circular Alias Chains

**Scenario**: Hypothetical `ENTITY_ALIASES = {"a": ["b_a"], "b": ["a_b"]}`

**Behavior**: `_visited` set prevents infinite recursion. When an entity type is visited twice, the function returns the field unchanged immediately.

**Example**:
```python
# entity_type="a", field_name="x", _visited=set()
# Step 5b: parent="b", recurse with _visited={"a"}
# In recursion: entity_type="b", step 5b: parent="a"
# Recurse with _visited={"a", "b"}
# In recursion: entity_type="a", _visited check triggers, return "x"
```

### Empty Criterion

**Scenario**: `criterion = {}`

**Behavior**: Returns empty dict. No normalization needed.

### Field Already Normalized

**Scenario**: `field_name="office_phone"` when `"office_phone"` is in schema

**Behavior**: Returns on step 2 (exact match). No transformation needed.

### Unknown Fields

**Scenario**: Field not resolvable through any path

**Behavior**: Returns field unchanged. Downstream validation (`validate_criterion_for_entity()`) will report error with available fields list.

## Test Cases

### Resolution Path Matrix

| TC | Input Field | Entity | Schema Contains | Expected | Resolution Path |
|----|-------------|--------|-----------------|----------|-----------------|
| 1 | `contact_email` | contact | `contact_email` | `contact_email` | Exact match (step 2) |
| 2 | `email` | contact | `contact_email` | `contact_email` | Prefix expansion (step 3) |
| 3 | `phone` | contact | `contact_phone` | `contact_phone` | Prefix expansion (step 3) |
| 4 | `vertical` | unit | `vertical` | `vertical` | Exact match (step 2) |
| 5 | `office_phone` | unit | `office_phone` | `office_phone` | Exact match (step 2) |
| 6 | `phone` | business | `office_phone` | `office_phone` | Alias expansion: business->office (step 5a) |
| 7 | `phone` | unit | `office_phone` | `office_phone` | Chain: unit->business_unit->business->office (step 5b) |
| 8 | `phone` | offer | `office_phone` | `office_phone` | Chain: offer->business_offer->business->office (step 5b) |
| 9 | `unknown_field` | contact | `contact_email` | `unknown_field` | Fallback (step 6) |
| 10 | `email` | unknown | `email` | `email` | Exact match (step 2), no aliases needed |

### Unit Test Specifications

```python
class TestNormalizeField:
    """Test cases for _normalize_field() function."""

    def test_exact_match_returns_unchanged(self):
        """TC-1: Field already in schema returns as-is."""
        available = {"contact_email", "contact_phone", "gid"}
        result = _normalize_field("contact_email", "contact", available)
        assert result == "contact_email"

    def test_prefix_expansion_contact(self):
        """TC-2,3: Short name expands to {entity}_{field}."""
        available = {"contact_email", "contact_phone", "gid"}
        assert _normalize_field("email", "contact", available) == "contact_email"
        assert _normalize_field("phone", "contact", available) == "contact_phone"

    def test_exact_match_vertical(self):
        """TC-4: Field in schema without prefix returns as-is."""
        available = {"vertical", "office_phone", "gid"}
        result = _normalize_field("vertical", "unit", available)
        assert result == "vertical"

    def test_exact_match_office_phone(self):
        """TC-5: Fully qualified field returns as-is."""
        available = {"vertical", "office_phone", "gid"}
        result = _normalize_field("office_phone", "unit", available)
        assert result == "office_phone"

    def test_alias_expansion_business(self):
        """TC-6: business->office alias resolves phone."""
        available = {"office_phone", "gid"}
        result = _normalize_field("phone", "business", available)
        assert result == "office_phone"

    def test_chain_resolution_unit(self):
        """TC-7: unit->business_unit->business->office chain."""
        available = {"office_phone", "gid"}
        result = _normalize_field("phone", "unit", available)
        assert result == "office_phone"

    def test_chain_resolution_offer(self):
        """TC-8: offer->business_offer->business->office chain."""
        available = {"office_phone", "gid"}
        result = _normalize_field("phone", "offer", available)
        assert result == "office_phone"

    def test_unknown_field_passthrough(self):
        """TC-9: Unknown field returns unchanged."""
        available = {"contact_email", "gid"}
        result = _normalize_field("unknown_field", "contact", available)
        assert result == "unknown_field"

    def test_unknown_entity_with_exact_match(self):
        """TC-10: Unknown entity can still match exact fields."""
        available = {"email", "gid"}
        result = _normalize_field("email", "unknown", available)
        assert result == "email"

    def test_recursion_guard_prevents_infinite_loop(self):
        """Circular aliases terminate via _visited set."""
        # Hypothetical circular case
        available = {"x", "gid"}
        result = _normalize_field("x", "unit", available, _visited={"business"})
        # Should not infinitely recurse
        assert result == "x"

    def test_empty_available_fields_passthrough(self):
        """Missing schema causes passthrough."""
        result = _normalize_field("email", "contact", set())
        assert result == "email"


class TestApplyLegacyMapping:
    """Integration tests for _apply_legacy_mapping() with SchemaRegistry."""

    def test_normalizes_criterion_dict(self):
        """Full criterion dict is normalized."""
        criterion = {"email": "test@example.com", "phone": "+15551234567"}
        result = _apply_legacy_mapping("contact", criterion)
        assert result == {
            "contact_email": "test@example.com",
            "contact_phone": "+15551234567",
        }

    def test_preserves_already_normalized(self):
        """Already-normalized fields pass through."""
        criterion = {"contact_email": "test@example.com"}
        result = _apply_legacy_mapping("contact", criterion)
        assert result == {"contact_email": "test@example.com"}

    def test_unit_phone_resolution(self):
        """Unit phone resolves through chain."""
        criterion = {"phone": "+15551234567", "vertical": "dental"}
        result = _apply_legacy_mapping("unit", criterion)
        assert result == {
            "office_phone": "+15551234567",
            "vertical": "dental",
        }
```

## Non-Functional Considerations

### Performance

**Complexity**: O(d * a) per field, where:
- d = maximum alias chain depth (currently 3: unit->business_unit->business->office)
- a = average aliases per entity (currently 1-2)

**Real-world cost**: Negligible. Maximum 10-15 set lookups per field. Field count per criterion is typically 1-5.

**Optimization**: None needed. Current approach is already optimal for expected usage.

### Security

No security implications. This is an internal field name transformation with no external input validation bypass. Invalid fields still fail downstream validation.

### Reliability

**Failure mode**: SchemaRegistry unavailable
- **Behavior**: `available_fields` becomes empty set
- **Impact**: All fields pass through unchanged
- **Recovery**: Downstream validation catches invalid fields

**Monitoring**: No additional monitoring required. Existing validation error logging covers this path.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Schema changes break resolution | Low | Medium | Algorithm checks schema dynamically; new fields auto-resolve |
| New entity type added without aliases | Medium | Low | Unknown entities use steps 1-4; fields still resolve if prefixed |
| Alias chain grows too deep | Low | Low | `_visited` guard prevents infinite recursion; depth is O(d) |
| Performance regression | Low | Low | Algorithm is O(d*a) with small constants; monitor if d>5 |

## Migration Checklist

### Implementation Steps

1. [ ] Add `ENTITY_ALIASES` constant to `resolver.py`
2. [ ] Add `_normalize_field()` function to `resolver.py`
3. [ ] Update `_apply_legacy_mapping()` to use new algorithm
4. [ ] Remove `LEGACY_FIELD_MAPPING` constant
5. [ ] Update `__all__` export list (remove `LEGACY_FIELD_MAPPING`)
6. [ ] Add unit tests for `_normalize_field()`
7. [ ] Add integration tests for `_apply_legacy_mapping()`
8. [ ] Run full test suite to verify no regressions
9. [ ] Update any documentation referencing `LEGACY_FIELD_MAPPING`

### Validation Criteria

- [ ] All existing tests pass without modification (backward compatible)
- [ ] New tests cover all 10 resolution path scenarios
- [ ] `LEGACY_FIELD_MAPPING` is fully removed from codebase
- [ ] No references to `LEGACY_FIELD_MAPPING` remain

### Rollback Plan

If issues discovered post-deployment:
1. Revert `_apply_legacy_mapping()` to use static `LEGACY_FIELD_MAPPING`
2. Re-add `LEGACY_FIELD_MAPPING` constant
3. Investigate failure mode
4. Add missing test case for discovered scenario

## ADRs

### ADR-DFN-001: Hierarchical Alias Resolution Over Static Mapping

**Status**: Proposed

**Context**: The static `LEGACY_FIELD_MAPPING` dictionary requires manual maintenance and has caused bugs due to mapping direction confusion.

**Decision**: Replace with hierarchical alias resolution that uses entity type relationships and schema introspection.

**Alternatives Considered**:

1. **Enhanced Static Mapping**: Add more comprehensive mappings
   - Pros: Simple, explicit
   - Cons: Maintenance burden, scales poorly, error-prone

2. **Bidirectional Mapping**: Generate reverse mappings automatically
   - Pros: Handles both directions
   - Cons: Still requires per-field configuration, complex generation

3. **Hierarchical Alias Resolution** (chosen)
   - Pros: Semantic, scales automatically, zero per-field maintenance
   - Cons: More complex algorithm, requires understanding of entity hierarchy

**Rationale**: The hierarchical approach encodes domain knowledge (entity relationships) rather than field-level mappings. This is more maintainable and self-documenting. New fields automatically resolve correctly without configuration changes.

**Consequences**:
- Positive: Zero per-field maintenance, bidirectional resolution, semantic configuration
- Negative: Requires understanding of alias chain for debugging
- Neutral: Algorithm complexity is hidden in private function

## Open Items

None. Design is complete and ready for implementation.

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| TDD (this document) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-dynamic-field-normalization.md` | Yes |
| Spike Report | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-dynamic-field-normalization.md` | Yes |
| Target Module | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Yes |
| SchemaRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py` | Yes |
