# ADR-0006: Custom Field Resolution Strategy

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0030, ADR-0034, ADR-0112
- **Related**: reference/CUSTOM-FIELDS.md

## Context

Asana custom fields are identified by GIDs (globally unique identifiers) but users refer to them by names (human-readable). The SDK must map between these representations while providing type safety, environment agnosticism, and zero additional API overhead.

Custom fields have environment-specific GIDs but human-readable names. For example, an "MRR" custom field might have GID `1205511992584993` in production but `9999999999999999` in staging. Hardcoding GIDs blocks portability and requires manual configuration per environment.

The SDK evolved from static GID constants (MVP approach for 20 fields) to dynamic name-based resolution that scales to 100+ fields across 50+ task types without code changes.

## Decision

**Use dynamic name-based resolution with session-level caching. Field names are normalized to lowercase alphanumeric for case-insensitive matching. The name-to-GID index is built from task data already loaded by the API, requiring zero extra API calls.**

### Resolution Algorithm

```
1. Parse source prefix from schema:
   - "cf:Name" → Resolve by name
   - "gid:123" → Explicit GID (testing/override)
   - attribute path → Not a custom field

2. For "cf:" sources:
   a. Normalize field name: lowercase, remove non-alphanumeric
   b. Look up in session-cached index
   c. Return GID if found, None if not

3. Use GID to find value in task.custom_fields
```

### Implementation

```python
# Self-documenting schema definition
ColumnDef(name="mrr", source="cf:MRR")           # Resolve by name
ColumnDef(name="mrr", source="gid:123456")       # Explicit GID
ColumnDef(name="created", source="created_at")   # Attribute path
```

### Name Normalization

Asana custom field names vary in format:
- "Weekly Ad Spend" (Title Case with spaces)
- "MRR" (ALL CAPS)
- "monthly-recurring-revenue" (hyphenated)

Schema field names use snake_case ("weekly_ad_spend"). Normalization to lowercase alphanumeric enables matching regardless of naming convention.

### Session-Cached Index

Built once per extraction session from the first task's `custom_fields`:
- O(1) lookups after initial build
- Thread-safe concurrent access (RLock protected)
- No repeated iteration over custom_fields per task
- Predictable performance characteristics

### GID Resolution for API Calls

When seeding fields or automating pipelines, values are computed using human-readable names but API requires GIDs:

```python
# Use existing CustomFieldAccessor for all resolution
target = await client.tasks.get_async(
    gid,
    opt_fields=["custom_fields", "custom_fields.enum_options"]
)

# Build accessor from target's field definitions
accessor = target.get_custom_fields()

# Set values by name - accessor handles resolution
accessor.set("Priority", "High")
accessor.set("MRR", 1000)

# Convert to API format
payload = {"custom_fields": accessor.to_api_dict()}

# Single API call with formatted payload
await client.tasks.update_async(gid, **payload)
```

## Rationale

### Why Dynamic Resolution?

**Static GIDs (MVP approach)**:
```python
# Blocked progress with placeholders
MRR_GID = "PLACEHOLDER_MRR_GID"  # Must be replaced per environment
```

**Dynamic resolution**:
```python
# Self-documenting, environment-agnostic
ColumnDef(name="mrr", source="cf:MRR")
```

Advantages:
1. **Environment-agnostic**: GIDs discovered at runtime from task data
2. **Self-documenting schemas**: `source="cf:MRR"` indicates exactly what to look for
3. **Scales to any number of fields**: No code changes for new fields
4. **Zero extra API calls**: Uses existing `task.custom_fields` data already loaded
5. **Testable without Asana**: Mock resolver enables offline testing

### Why Session-Level Caching?

Building the index once per extraction session provides:
- O(1) lookups after initial build
- Thread-safe concurrent access
- No repeated iteration
- Predictable performance

### Why Reuse CustomFieldAccessor for GID Resolution?

Centralizes resolution logic in one tested location:
- Handles case-insensitivity automatically
- Performs type conversion
- Resolves enum option GIDs
- Avoids reinventing the wheel

## Alternatives Considered

### Alternative 1: Static GIDs (MVP Approach - ADR-0030)

**Description**: Hardcoded GID constants in `custom_fields.py`, populated per environment.

```python
MRR_GID = "1205511992584993"
VERTICAL_GID = "1205511992584998"
```

**Pros**:
- Type safety at development time
- IDE autocomplete for GID constants
- No runtime resolution overhead

**Cons**:
- 16 placeholders blocking implementation
- Environment-specific configuration required
- No self-documentation in schemas
- Doesn't scale to 50+ task types
- Code change required for each new field

**Why not chosen**: Blocked progress; doesn't scale; environment-specific coupling.

### Alternative 2: API Discovery by Name

**Description**: Query Asana API to discover custom field GIDs by name before extraction.

```python
project = await client.projects.get(gid, opt_fields=["custom_field_settings"])
mrr_gid = next(cf["gid"] for cf in settings if cf["name"] == "MRR")
```

**Pros**:
- No hardcoded GIDs
- Works across different Asana workspaces

**Cons**:
- Extra API call per extraction batch
- Field names can change, breaking discovery
- Performance overhead
- Cannot type-check values statically
- Consumes API quota unnecessarily

**Why not chosen**: Extra API calls; name instability; performance cost.

### Alternative 3: Configuration File (YAML/JSON)

**Description**: Store field mappings in configuration file.

```yaml
custom_field_mappings:
  Unit:
    mrr:
      gid: "1205511992584993"
      type: decimal
```

**Pros**:
- Environment-specific without code changes
- Consistent pattern for all environments

**Cons**:
- Configuration loading infrastructure needed
- No IDE autocomplete
- Configuration validation complexity
- Over-engineering for current scope
- Configuration drift risk

**Why not chosen**: Over-engineering; no IDE support; adds deployment complexity.

### Alternative 4: Database-Driven Mapping

**Description**: Store custom field mappings in a database.

**Pros**:
- Centralized management
- Easy updates without deploys
- Audit trail for changes

**Cons**:
- Database dependency for SDK
- Significant infrastructure complexity
- Latency for mapping lookups
- SDK should be standalone

**Why not chosen**: SDK should not require database infrastructure.

## Consequences

### Positive

- **Environment-agnostic**: GIDs discovered at runtime from task data
- **Self-documenting schemas**: `source="cf:MRR"` indicates what to look for
- **Testable without Asana**: MockCustomFieldResolver enables offline testing
- **Scales to any number of fields**: No code changes for new fields
- **Zero extra API calls**: Uses existing task.custom_fields data
- **Centralized resolution**: Single source of truth prevents divergence
- **Type safety**: IDE autocomplete works through descriptors (see ADR-0008)

### Negative

- **Slight complexity increase**: New resolver package with 4-5 files
- **First task requirement**: First task must have all custom fields defined
- **Name changes require schema updates**: If Asana field name changes, schema source must be updated
- **Normalization edge cases**: Unusual field names may need manual GID specification

### Neutral

- **Deprecates static GIDs**: `custom_fields.py` constants emit deprecation warnings
- **Index built once per session**: Not per-task, but not globally cached either
- **Thread-safety via RLock**: Standard synchronization pattern

## Compliance

### How This Decision Is Enforced

1. **Code review checklist**:
   - [ ] Custom field columns use `cf:` prefix in source
   - [ ] No new static GID constants added to `custom_fields.py`
   - [ ] Tests use `MockCustomFieldResolver` for isolation
   - [ ] Resolver injected via constructor (not global)

2. **Linting rules**:
   ```python
   # Deprecated - emit warning
   from autom8_asana.dataframes.models.custom_fields import MRR_GID

   # Preferred
   ColumnDef(name="mrr", source="cf:MRR")
   ```

3. **Testing requirements**:
   - [ ] Unit tests use `MockCustomFieldResolver`
   - [ ] Integration tests verify name normalization patterns
   - [ ] Thread-safety tested with concurrent extraction
   - [ ] GID resolution tested for all field types

4. **Documentation**:
   - [ ] Schema source convention documented
   - [ ] Migration guide for existing code
   - [ ] Expected Asana field names documented per schema
   - [ ] Normalization rules explained
