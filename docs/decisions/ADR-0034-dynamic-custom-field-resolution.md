# ADR-0034: Dynamic Custom Field Resolution Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer
- **Related**:
  - [PRD-0003.1](../requirements/PRD-0003.1-dynamic-custom-field-resolution.md)
  - [TDD-0009.1](../design/TDD-0009.1-dynamic-custom-field-resolution.md)
  - [ADR-0030](ADR-0030-custom-field-typing.md) - Custom Field Typing (predecessor)
  - [ADR-0001](ADR-0001-protocol-extensibility.md) - Protocol-Based Extensibility

## Context

ADR-0030 established static GID constants for MVP custom field typing. While this approach provided type safety and IDE support, it has significant limitations that block progress on Phase 3 of TDD-0009:

1. **Environment-specific GIDs**: The 16 placeholder GIDs (`PLACEHOLDER_MRR_GID`, etc.) require manual population per environment (production, staging, development)
2. **Scaling limitations**: Each new custom field requires code changes in 3 places (constants, schema, extractor)
3. **No self-documentation**: `source=None` in schemas provides no information about which Asana field to look for
4. **Testing complexity**: Unit tests require mock GIDs that may not match real Asana data

The current state in `custom_fields.py`:
```python
MRR_GID = "PLACEHOLDER_MRR_GID"  # Must be replaced with actual GID
WEEKLY_AD_SPEND_GID = "PLACEHOLDER_WEEKLY_AD_SPEND_GID"
# ... 14 more placeholders
```

PRD-0003.1 specifies requirements for dynamic resolution using the task's existing `custom_fields` list, eliminating the need for static GID configuration.

### Forces at Play

| Force | Direction |
|-------|-----------|
| Type safety | Favors static (compile-time checks) |
| IDE autocomplete | Favors static (constants) |
| Environment agnosticism | Favors dynamic (runtime discovery) |
| Scalability | Favors dynamic (no code changes) |
| Testability | Favors protocol-based (mock injection) |
| Self-documentation | Favors dynamic (explicit field names) |
| Zero API calls | Favors using existing task data |

## Decision

**Implement dynamic custom field resolution using a protocol-based resolver with name normalization and session-level caching.**

Key elements:

1. **`CustomFieldResolver` protocol**: Define a protocol for field resolution, enabling dependency injection and mock implementations per ADR-0001
2. **`NameNormalizer`**: Normalize both schema field names (snake_case) and Asana field names (Title Case, etc.) to a canonical form for matching
3. **Session-cached index**: Build a `name -> gid` index from the first task's `custom_fields`, cache for the entire extraction session
4. **`source="cf:Name"` convention**: Self-documenting schema sources that specify the Asana field name to resolve
5. **Zero extra API calls**: Use custom fields data already present on loaded tasks

### Source Convention

```python
# Self-documenting schema definition
ColumnDef(name="mrr", source="cf:MRR")           # Resolve by name
ColumnDef(name="mrr", source="gid:123456")       # Explicit GID (testing/override)
ColumnDef(name="mrr", source=None)               # Use column name as field name
ColumnDef(name="created", source="created_at")   # Attribute path (not custom field)
```

### Resolution Algorithm

```
1. Parse source prefix ("cf:", "gid:", or attribute path)
2. For "cf:" sources:
   a. Normalize the field name (lowercase, remove non-alphanumeric)
   b. Look up in session-cached index
   c. Return GID if found, None if not
3. For "gid:" sources:
   a. Return the GID directly (bypass resolution)
4. Use GID to find custom field value in task.custom_fields
```

## Rationale

### Why Protocol-Based?

Per ADR-0001, protocols enable structural subtyping without inheritance. This allows:
- `MockCustomFieldResolver` for testing without live Asana
- Future `ConfigurableCustomFieldResolver` for post-MVP configuration files
- `DefaultCustomFieldResolver` for production use

### Why Name Normalization?

Asana custom field names can vary:
- "Weekly Ad Spend" (Title Case with spaces)
- "MRR" (ALL CAPS)
- "monthly-recurring-revenue" (hyphenated)

Schema field names use snake_case ("weekly_ad_spend"). Normalization to a canonical form (lowercase alphanumeric only) enables matching regardless of naming convention.

### Why Session-Cached Index?

Building the index once per extraction session provides:
- O(1) lookups after initial build
- Thread-safe concurrent access (RLock protected)
- No repeated iteration over custom_fields per task
- Predictable performance characteristics

### Why Zero Extra API Calls?

Tasks loaded via `get_tasks()` already include `custom_fields` with all field definitions and values. Using this existing data:
- Avoids additional API quota consumption
- Eliminates latency from extra requests
- Works offline with cached tasks

## Alternatives Considered

### Alternative 1: Static GIDs (Current Approach)

**Description**: Keep hardcoded GID constants in `custom_fields.py`, populated per environment.

**Pros**:
- Type safety at development time
- IDE autocomplete for GID constants
- No runtime resolution overhead

**Cons**:
- 16 placeholders blocking implementation
- Environment-specific configuration required
- No self-documentation in schemas
- Doesn't scale to 50+ task types

**Why not chosen**: Blocks progress; doesn't scale; environment-specific coupling.

### Alternative 2: API Discovery by Name

**Description**: Query Asana API to discover custom field GIDs by name before extraction.

```python
# Anti-pattern example
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

**Why not chosen**: Extra API calls; name instability; performance cost.

### Alternative 3: Configuration File (YAML/JSON)

**Description**: Store field mappings in configuration file, loaded at runtime.

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

**Why not chosen**: Over-engineering; no IDE support; configuration drift risk.

### Alternative 4: Database-Driven Mapping

**Description**: Store custom field mappings in a database, load at runtime.

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

### Alternative 5: Decorator Pattern on ColumnDef

**Description**: Add resolution behavior directly to ColumnDef class.

```python
@dataclass
class ColumnDef:
    def resolve(self, task: Task) -> str | None:
        # Resolution logic here
```

**Pros**:
- All resolution logic in one place
- No separate resolver component

**Cons**:
- Violates single responsibility
- Makes ColumnDef harder to test
- Couples data model to resolution logic

**Why not chosen**: Violates single responsibility; reduces testability.

## Consequences

### Positive

- **Environment-agnostic**: GIDs discovered at runtime from task data
- **Self-documenting schemas**: `source="cf:MRR"` tells you what to look for
- **Testable without Asana**: `MockCustomFieldResolver` enables offline testing
- **Scales to any number of fields**: No code changes for new fields
- **Zero extra API calls**: Uses existing task.custom_fields data
- **Protocol-based extensibility**: Follows established ADR-0001 pattern

### Negative

- **Slight complexity increase**: New resolver package with 4-5 files
- **First task requirement**: First task must have all custom fields defined
- **Name changes require schema updates**: If Asana field name changes, schema source must be updated

### Neutral

- **Deprecates static GIDs**: `custom_fields.py` constants will emit deprecation warnings
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

4. **Documentation**:
   - [ ] Schema source convention documented in TDD-0009.1
   - [ ] Migration guide for existing code
   - [ ] Expected Asana field names documented per schema
