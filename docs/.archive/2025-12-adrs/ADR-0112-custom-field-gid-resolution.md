# ADR-0112: Custom Field GID Resolution Pattern

## Metadata
- **Status**: Accepted
- **Author**: Architect (Claude)
- **Date**: 2025-12-18
- **Deciders**: Engineering Team
- **Related**: [PRD-PIPELINE-AUTOMATION-ENHANCEMENT](../requirements/PRD-PIPELINE-AUTOMATION-ENHANCEMENT.md), [TDD-PIPELINE-AUTOMATION-ENHANCEMENT](../design/TDD-PIPELINE-AUTOMATION-ENHANCEMENT.md)

## Context

When seeding fields on a newly created Process, the FieldSeeder computes field values using human-readable field names like "Vertical", "Office Phone", or "Started At". However, Asana's API requires custom field updates to use GIDs (globally unique identifiers), not names:

```python
# What we have (from FieldSeeder):
seeded_fields = {
    "Vertical": "Dental",
    "Office Phone": "555-1234",
    "Started At": "2025-12-18",
}

# What Asana API requires:
custom_fields = {
    "1234567890": "dental_option_gid",  # Vertical (enum)
    "2345678901": "555-1234",           # Office Phone (text)
    "3456789012": "2025-12-18",         # Started At (date)
}
```

We need a pattern to resolve field names to GIDs and format values for the API.

**Forces at play**:
- Field names are human-readable and used throughout the SDK
- GIDs are required for API calls
- Different projects may have the same field name with different GIDs
- Enum fields require both field GID and option GID resolution
- The SDK already has `CustomFieldAccessor` for this purpose
- We want consistency with existing patterns

## Decision

**Use the existing `CustomFieldAccessor` class with its `_resolve_gid()` method for all field name to GID resolution, and `to_api_dict()` for formatting the API payload.**

Specifically:
```python
async def write_fields_async(
    self,
    target_task_gid: str,
    fields: dict[str, Any],
) -> WriteResult:
    # 1. Fetch target task with custom field definitions
    target_task = await client.tasks.get_async(
        target_task_gid,
        opt_fields=["custom_fields", "custom_fields.enum_options"],
    )

    # 2. Build accessor from target's field definitions
    accessor = CustomFieldAccessor(
        data=target_task.custom_fields,
        strict=False,  # Don't fail on unknown fields
    )

    # 3. Set values by name - accessor handles resolution
    for name, value in fields.items():
        try:
            accessor.set(name, value)
        except NameNotFoundError:
            log.warning("Field '%s' not found on target", name)

    # 4. Convert to API format
    api_payload = accessor.to_api_dict()

    # 5. Single API call
    await client.tasks.update_async(
        target_task_gid,
        custom_fields=api_payload,
    )
```

## Rationale

Using `CustomFieldAccessor` is the right approach because:

1. **Existing Proven Code**: `CustomFieldAccessor` is battle-tested, used throughout the SDK for custom field operations (per TDD-TRIAGE-FIXES, ADR-0056).

2. **Name-to-GID Resolution**: The `_resolve_gid()` method already handles:
   - Direct GID passthrough (if input is numeric)
   - Case-insensitive name lookup from local index
   - Optional resolver fallback for workspace-level resolution

3. **Type Conversion**: The `_format_value_for_api()` method handles:
   - Decimal to float conversion
   - Enum dict to GID extraction
   - Multi-enum list formatting
   - People field GID extraction

4. **Enum Option Resolution**: When the accessor has `enum_options` data (from `opt_fields`), it can resolve enum display names to option GIDs.

5. **Strict Mode Control**: Setting `strict=False` allows graceful handling of fields that don't exist on the target project.

## Alternatives Considered

### Alternative 1: Manual GID Mapping

- **Description**: Build a separate mapping dict from field names to GIDs by iterating over target task's `custom_fields`.
- **Pros**:
  - No dependency on CustomFieldAccessor
  - Clear, explicit mapping
- **Cons**:
  - Duplicates logic already in CustomFieldAccessor
  - Must handle case-insensitivity, type formatting manually
  - Enum option resolution is complex to implement
  - Higher maintenance burden
- **Why not chosen**: Reinventing the wheel when proven code exists.

### Alternative 2: Workspace-Level Field Registry

- **Description**: Maintain a workspace-level registry mapping field names to GIDs, shared across all projects.
- **Pros**:
  - Single source of truth for field GIDs
  - One fetch at startup, then cache
- **Cons**:
  - Field GIDs can differ between projects (same name, different field)
  - Registry maintenance overhead
  - Stale data risk
  - Overkill for per-task resolution
- **Why not chosen**: Field GIDs are project-specific; a global registry doesn't capture this. Per-task resolution is simpler and accurate.

### Alternative 3: GIDs in Seeder Configuration

- **Description**: Configure FieldSeeder with explicit GID mappings instead of names.
- **Pros**:
  - No resolution needed at runtime
  - Fastest execution
- **Cons**:
  - Brittle: GIDs change if fields are recreated
  - Not portable across workspaces/projects
  - Configuration burden
  - Loses human readability
- **Why not chosen**: Names are more stable and maintainable than GIDs.

### Alternative 4: Project-Level Field Cache

- **Description**: When a project is first accessed, cache its field name-to-GID mapping for future use.
- **Pros**:
  - Faster subsequent lookups
  - Reduces API calls
- **Cons**:
  - Cache invalidation complexity
  - Memory overhead for many projects
  - Still need initial fetch per project
- **Why not chosen**: For a single-shot conversion, the overhead of caching isn't justified. The target task fetch already includes field data.

## Consequences

### Positive
- **Code Reuse**: Leverages existing, tested CustomFieldAccessor implementation.
- **Consistency**: Same pattern used throughout SDK for custom field operations.
- **Type Safety**: `_format_value_for_api()` handles all type conversions.
- **Graceful Degradation**: `strict=False` mode skips unknown fields with warnings.

### Negative
- **Extra API Call**: Must fetch target task with `opt_fields=["custom_fields"]` before writing. This is acceptable for a one-time conversion.
- **Enum Options Required**: For enum resolution to work by name, must include `custom_fields.enum_options` in fetch.

### Neutral
- **No New Code**: Extends existing FieldSeeder using existing CustomFieldAccessor.
- **Well-Understood Pattern**: Team is familiar with accessor pattern.

## Compliance

- [ ] `write_fields_async()` uses `CustomFieldAccessor` for GID resolution
- [ ] Target task is fetched with `opt_fields=["custom_fields", "custom_fields.enum_options"]`
- [ ] Accessor is created with `strict=False` for graceful degradation
- [ ] Unknown fields are logged as warnings, not errors
- [ ] Unit tests verify name-to-GID resolution for text, enum, and date fields
