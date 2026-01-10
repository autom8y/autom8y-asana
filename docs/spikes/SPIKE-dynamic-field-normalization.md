# SPIKE: Dynamic Field Normalization

**Date**: 2026-01-10
**Status**: Complete
**Timebox**: 15 minutes

## Question

Can we replace the static `LEGACY_FIELD_MAPPING` dictionary with a dynamic approach that:
1. First checks if the field name is valid as-is
2. Falls back to stripping the entity type prefix (e.g., `contact_email` → `email` for contact entity)

## Current Problem

The current approach requires maintaining a static dictionary:

```python
LEGACY_FIELD_MAPPING = {
    "contact": {
        "email": "contact_email",
        "phone": "contact_phone",
    },
    "unit": {
        "phone": "office_phone",
    },
    # ... manual maintenance required
}
```

**Issues**:
1. Manual maintenance burden
2. Easy to get backwards (we just fixed `contact_email` → `email` being reversed)
3. Doesn't scale as schemas evolve
4. Hard to reason about which direction the mapping goes

## Proposed Solution

**Algorithm**: Hierarchical resolution with entity aliasing

```python
# Entity type aliases - semantic hierarchy
# unit = business_unit (a type of business)
# offer = business_offer (a type of business)
# business → office (the actual prefix in schema)
ENTITY_ALIASES = {
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
    """Normalize field name with hierarchical alias resolution.

    Resolution order:
    1. Exact match: field_name in available_fields
    2. Prefix expansion: {entity_type}_{field_name}
    3. Prefix removal: strip {entity_type}_ from field_name
    4. Alias expansion: {alias}_{field_name} for each alias
    5. Alias decomposition: strip entity suffix from alias, recurse
       e.g., business_unit → business, then resolve via business's aliases

    Examples:
        - contact + "email" → "contact_email" (prefix expansion)
        - business + "phone" → "office_phone" (alias: business→office)
        - unit + "phone" → "office_phone" (chain: unit→business_unit→business→office)
        - offer + "phone" → "office_phone" (chain: offer→business_offer→business→office)
    """
    # Prevent infinite recursion
    if _visited is None:
        _visited = set()
    if entity_type in _visited:
        return field_name
    _visited = _visited | {entity_type}

    # 1. Exact match
    if field_name in available_fields:
        return field_name

    # 2. Prefix expansion: {entity}_{field}
    prefixed = f"{entity_type}_{field_name}"
    if prefixed in available_fields:
        return prefixed

    # 3. Prefix removal: contact_email → email
    prefix = f"{entity_type}_"
    if field_name.startswith(prefix):
        stripped = field_name[len(prefix):]
        if stripped in available_fields:
            return stripped

    # 4. Try each alias
    for alias in ENTITY_ALIASES.get(entity_type, []):
        # 4a. Direct alias expansion: {alias}_{field}
        alias_prefixed = f"{alias}_{field_name}"
        if alias_prefixed in available_fields:
            return alias_prefixed

        # 4b. Alias decomposition: strip entity suffix, recurse
        # business_unit → business, then check business's aliases
        if "_" in alias:
            parent = alias.rsplit("_", 1)[0]  # business_unit → business
            result = _normalize_field(field_name, parent, available_fields, _visited)
            if result in available_fields:
                return result

    # Return unchanged - validation will catch
    return field_name
```

## Analysis

### Resolution Chain Examples

**unit + phone → office_phone**:
```
1. "phone" not in schema                    ❌
2. "unit_phone" not in schema               ❌
3. N/A (no prefix to strip)
4. alias "business_unit":
   4a. "business_unit_phone" not in schema  ❌
   4b. decompose → parent="business", recurse:
       1. "phone" not in schema             ❌
       2. "business_phone" not in schema    ❌
       4. alias "office":
          4a. "office_phone" in schema      ✅ FOUND
```

**offer + phone → office_phone**:
```
Same chain: offer → business_offer → business → office → office_phone ✅
```

**contact + email → contact_email**:
```
1. "email" not in schema                    ❌
2. "contact_email" in schema                ✅ FOUND
```

### What This Handles Automatically

| Input | Entity | Schema Column | Resolution Chain |
|-------|--------|---------------|------------------|
| `contact_email` | contact | `contact_email` | Exact match |
| `email` | contact | `contact_email` | Prefix expansion |
| `phone` | contact | `contact_phone` | Prefix expansion |
| `vertical` | unit | `vertical` | Exact match |
| `office_phone` | unit | `office_phone` | Exact match |
| `phone` | business | `office_phone` | business→office |
| `phone` | unit | `office_phone` | unit→business_unit→business→office |
| `phone` | offer | `office_phone` | offer→business_offer→business→office |

### Why This Works

The `ENTITY_ALIASES` encodes the **domain hierarchy**:
- `unit` IS-A `business_unit` (child of business)
- `offer` IS-A `business_offer` (child of business)
- `business` USES `office_` prefix for phone/address fields

This is semantic, not a field-by-field hack. Adding new fields "just works".

## Recommended Implementation

```python
from typing import Any

# Entity type aliases - semantic domain hierarchy
# Encodes: unit IS-A business_unit, offer IS-A business_offer, business USES office_ prefix
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
    """Normalize a single field name using hierarchical alias resolution.

    Resolution order:
    1. Exact match: field_name in available_fields
    2. Prefix expansion: {entity_type}_{field_name}
    3. Prefix removal: strip {entity_type}_ from field_name
    4. Alias expansion: {alias}_{field_name} for each alias
    5. Alias decomposition: strip suffix, recurse to parent entity

    Args:
        field_name: The field name from the criterion.
        entity_type: The entity type (e.g., "contact", "business").
        available_fields: Set of valid schema column names.
        _visited: Internal set to prevent infinite recursion.

    Returns:
        Normalized field name (may be unchanged if no resolution found).
    """
    # Prevent infinite recursion
    if _visited is None:
        _visited = set()
    if entity_type in _visited:
        return field_name
    _visited = _visited | {entity_type}

    # 1. Exact match
    if field_name in available_fields:
        return field_name

    # 2. Prefix expansion: {entity}_{field}
    prefixed = f"{entity_type}_{field_name}"
    if prefixed in available_fields:
        return prefixed

    # 3. Prefix removal: contact_email → email
    prefix = f"{entity_type}_"
    if field_name.startswith(prefix):
        stripped = field_name[len(prefix):]
        if stripped in available_fields:
            return stripped

    # 4. Try each alias
    for alias in ENTITY_ALIASES.get(entity_type, []):
        # 4a. Direct alias expansion: {alias}_{field}
        alias_prefixed = f"{alias}_{field_name}"
        if alias_prefixed in available_fields:
            return alias_prefixed

        # 4b. Alias decomposition: strip entity suffix, recurse
        # business_unit → business, then check business's aliases
        if "_" in alias:
            parent = alias.rsplit("_", 1)[0]  # business_unit → business
            result = _normalize_field(field_name, parent, available_fields, _visited)
            if result in available_fields:
                return result

    # Return unchanged - validation will catch invalid fields
    return field_name


def _apply_legacy_mapping(
    entity_type: str,
    criterion: dict[str, Any],
) -> dict[str, Any]:
    """Apply field normalization with hierarchical alias resolution.

    Replaces static LEGACY_FIELD_MAPPING with dynamic algorithm.

    Args:
        entity_type: Entity type for context.
        criterion: Original criterion dict.

    Returns:
        New dict with fields normalized to schema column names.
    """
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

## Benefits

1. **Zero field-level maintenance** - no per-field mappings to maintain
2. **Self-documenting** - algorithm is clear, order of operations is explicit
3. **Bidirectional** - handles both `email` → `contact_email` AND `contact_email` → `email`
4. **Semantic config** - `ENTITY_ALIASES` declares domain relationships, not field hacks
5. **Scales automatically** - new fields work without changes
6. **Eliminates reversal bugs** - no way to get mappings backwards

## Migration Path

1. Add `ENTITY_ALIASES` constant
2. Add `_normalize_field()` function
3. Replace `_apply_legacy_mapping()` implementation
4. Delete `LEGACY_FIELD_MAPPING` entirely
5. Update tests

## Recommendation

**Implement this dynamic approach.**

Key advantages over current approach:
- **No per-field mappings** - just one semantic config (`ENTITY_ALIASES`)
- **Bidirectional resolution** - works whether schema or API uses prefixed names
- **Domain-driven** - "business uses office_ prefix" is meaningful, not "phone→office_phone"
