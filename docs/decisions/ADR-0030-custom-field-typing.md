# ADR-0030: Custom Field Typing

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team
- **Related**: [PRD-0003](../requirements/PRD-0003-structured-dataframe-layer.md) (Design Decision 2), [TDD-0009](../design/TDD-0009-structured-dataframe-layer.md), [ADR-0029](ADR-0029-task-subclass-strategy.md)

## Context

Asana custom fields are identified by GIDs (globally unique identifiers). To extract custom field values into typed DataFrame columns, the SDK must map column names to custom field GIDs.

### Custom Field Structure in Asana

```json
{
  "custom_fields": [
    {
      "gid": "1205511992584993",
      "name": "MRR",
      "type": "number",
      "number_value": 5000.00
    },
    {
      "gid": "1205511992584994",
      "name": "Vertical",
      "type": "enum",
      "enum_value": {
        "gid": "1205511992585001",
        "name": "Healthcare"
      }
    }
  ]
}
```

### The GID vs. Name Problem

Custom field **names** can change (user-editable), but **GIDs** are permanent. Using names for lookup would break extraction if a user renames a field.

```python
# FRAGILE: Name-based lookup
mrr = task.get_custom_field_by_name("MRR")  # Breaks if renamed to "Monthly Revenue"

# STABLE: GID-based lookup
mrr = task.get_custom_field_by_gid("1205511992584993")  # Always works
```

### Forces at Play

| Force | Pull Toward |
|-------|-------------|
| Type safety | Static GIDs (compile-time checks) |
| IDE autocomplete | Static GIDs (constants) |
| Flexibility | Dynamic/config (runtime changes) |
| Deploy velocity | Dynamic/config (no code deploy) |
| Error detection | Static GIDs (early detection) |
| MVP simplicity | Static GIDs (hardcoded) |
| Post-MVP extensibility | Configurable |

### PRD-0003 Design Decision 2

PRD-0003 explicitly states:

> **Decision**: MVP uses static/hardcoded GIDs (Option A). Post-MVP supports hybrid with configurable extensions (Option C).

## Decision

**For MVP, custom field GIDs are hardcoded as constants. Post-MVP extends to support configurable field mappings.**

### MVP Implementation (Static GIDs)

```python
# autom8_asana/dataframes/models/custom_fields.py

"""Custom field GID constants for MVP task types.

These GIDs are stable identifiers in Asana. Names can change;
GIDs cannot. Each constant documents the current field name
for maintainability.

WARNING: These GIDs are environment-specific. Production GIDs
differ from staging/development. See environment configuration
for per-environment overrides.
"""

# === Unit Custom Fields ===

# MRR (Monthly Recurring Revenue)
# Type: number
MRR_GID = "1205511992584993"

# Weekly Ad Spend
# Type: number
WEEKLY_AD_SPEND_GID = "1205511992584994"

# Products
# Type: multi_enum
PRODUCTS_GID = "1205511992584995"

# Languages
# Type: multi_enum
LANGUAGES_GID = "1205511992584996"

# Discount
# Type: number (percentage)
DISCOUNT_GID = "1205511992584997"

# Vertical
# Type: enum
VERTICAL_GID = "1205511992584998"

# Specialty
# Type: text
SPECIALTY_GID = "1205511992584999"


# === Contact Custom Fields ===

# Full Name
# Type: text
FULL_NAME_GID = "1205511992585001"

# Nickname
# Type: text
NICKNAME_GID = "1205511992585002"

# Contact Phone
# Type: text
CONTACT_PHONE_GID = "1205511992585003"

# Contact Email
# Type: text
CONTACT_EMAIL_GID = "1205511992585004"

# Position
# Type: text
POSITION_GID = "1205511992585005"

# Employee ID
# Type: text
EMPLOYEE_ID_GID = "1205511992585006"

# Contact URL
# Type: text
CONTACT_URL_GID = "1205511992585007"

# Time Zone
# Type: enum or text
TIME_ZONE_GID = "1205511992585008"

# City
# Type: text
CITY_GID = "1205511992585009"
```

### Usage in Extractor

```python
from autom8_asana.dataframes.models.custom_fields import (
    MRR_GID,
    WEEKLY_AD_SPEND_GID,
    VERTICAL_GID,
)

class UnitExtractor(BaseExtractor):
    def extract(self, task: Task) -> UnitRow:
        return UnitRow(
            **self._extract_base_fields(task),
            mrr=self._extract_custom_field(task, MRR_GID, Decimal),
            weekly_ad_spend=self._extract_custom_field(task, WEEKLY_AD_SPEND_GID, Decimal),
            vertical=self._extract_custom_field(task, VERTICAL_GID, str),
            # ...
        )

    def _extract_custom_field(
        self,
        task: Task,
        gid: str,
        expected_type: type,
    ) -> Any:
        """Extract custom field value by GID with type coercion."""
        for cf in task.custom_fields or []:
            if cf.gid == gid:
                return self._coerce_value(cf, expected_type)
        return None  # Field not present
```

### Post-MVP Extension (Configurable)

```python
# Post-MVP: Configuration-based field mapping
# autom8_asana/dataframes/config/custom_fields.yaml

custom_field_mappings:
  Unit:
    mrr:
      gid: "1205511992584993"
      type: decimal
      nullable: true
    weekly_ad_spend:
      gid: "1205511992584994"
      type: decimal
      nullable: true
  Contact:
    full_name:
      gid: "1205511992585001"
      type: string
      nullable: true

# Environment-specific overrides
environments:
  production:
    Unit:
      mrr:
        gid: "1205511992584993"  # Production GID
  staging:
    Unit:
      mrr:
        gid: "9999999999999999"  # Staging GID
```

## Rationale

### Why Static GIDs for MVP?

**1. Type safety at development time**:
```python
# Static: IDE catches typos, refactoring is safe
mrr = extract(task, MRR_GID)  # IDE knows MRR_GID

# Dynamic: Runtime errors, no IDE help
mrr = extract(task, config["mrr"]["gid"])  # What if key missing?
```

**2. IDE autocomplete**:
```python
from autom8_asana.dataframes.models.custom_fields import (
    MRR_GID,        # IDE shows all available GIDs
    PRODUCTS_GID,   # Autocomplete works
    VERTICAL_GID,
)
```

**3. MVP scope is bounded**: Only Unit (11 fields) and Contact (9 fields) are in scope. 20 constants are manageable.

**4. GIDs are stable**: Asana guarantees GID stability. Once set, a custom field's GID never changes. The risk of hardcoding is low.

**5. Code change for field mapping is acceptable**: For MVP, if a new field is needed or a GID changes (rare), a code change is acceptable. This is simpler than building configuration infrastructure.

### Why Configurable Post-MVP?

**1. Scale**: 50+ task types would mean 100+ GID constants. Configuration is cleaner at scale.

**2. Environment differences**: Production, staging, and development may have different custom field GIDs. Configuration enables per-environment mapping.

**3. Customer customization**: If the SDK is used by external customers, they may have different custom fields. Configuration enables customization without code changes.

**4. Operational velocity**: Changing configuration is faster than code deploy for field mapping changes.

### Why Not Dynamic Discovery?

Asana's API could theoretically be used to discover custom fields by name:

```python
# ANTI-PATTERN: Don't do this
project = await client.projects.get("project_gid", opt_fields=["custom_field_settings"])
mrr_gid = next(
    cf["custom_field"]["gid"]
    for cf in project.custom_field_settings
    if cf["custom_field"]["name"] == "MRR"
)
```

This is problematic because:

1. **Extra API call**: Requires fetching project settings before extraction
2. **Name instability**: Field names can change; discovery would break
3. **Performance**: Discovery on every extraction is wasteful
4. **Type ambiguity**: Cannot statically type the extracted value

## Alternatives Considered

### Alternative 1: Dynamic Discovery by Name

- **Description**: Discover custom field GIDs by name at runtime by querying project custom field settings.
- **Pros**:
  - No hardcoded GIDs
  - Automatically adapts to field name changes (if names are stable)
  - Works across different Asana workspaces
- **Cons**:
  - Extra API call per extraction batch
  - Names can change, breaking discovery
  - No compile-time type safety
  - Performance overhead
  - Cannot type-check field values statically
- **Why not chosen**: Performance cost and name instability make this unsuitable. GIDs are designed to be stable identifiers.

### Alternative 2: Configuration File from Day 1

- **Description**: Use YAML/JSON configuration for field mappings from the start, even for MVP.
- **Pros**:
  - Consistent pattern from MVP to post-MVP
  - No code changes for field mapping updates
  - Environment-specific mappings immediately
- **Cons**:
  - Configuration loading infrastructure needed for MVP
  - No IDE autocomplete for GIDs
  - Configuration validation complexity
  - Over-engineering for 2 task types
- **Why not chosen**: MVP has only 2 task types with ~20 fields total. Static constants are simpler and provide better IDE support. Configuration infrastructure can wait for post-MVP.

### Alternative 3: Database-Driven Mapping

- **Description**: Store custom field mappings in a database, load at runtime.
- **Pros**:
  - Centralized management
  - Easy updates without deploys
  - Audit trail for changes
  - Multi-tenant support
- **Cons**:
  - Database dependency for SDK
  - Significant infrastructure complexity
  - Latency for mapping lookups
  - SDK is designed to be standalone
- **Why not chosen**: The SDK should not require database infrastructure. This is appropriate for a higher-level application layer, not the SDK itself.

### Alternative 4: Environment Variables

- **Description**: Store GIDs in environment variables.
- **Pros**:
  - Environment-specific without code changes
  - 12-factor app pattern
  - Easy to change in deployment
- **Cons**:
  - 20+ environment variables is unwieldy
  - No IDE autocomplete
  - No type checking
  - Hard to document and validate
- **Why not chosen**: Too many variables for 20 fields. Constants with post-MVP configuration is cleaner.

### Alternative 5: Hybrid from Day 1

- **Description**: Static constants that can be overridden by configuration.
- **Pros**:
  - Best of both: defaults with flexibility
  - IDE autocomplete for defaults
  - Configuration for overrides
- **Cons**:
  - More complex resolution logic
  - Two places to look for values
  - Potential confusion about which wins
- **Why not chosen**: Adds complexity for a problem MVP doesn't have. Post-MVP will implement this pattern when needed.

## Consequences

### Positive

- **Type safety**: GID constants are typed strings; IDE catches typos
- **IDE support**: Autocomplete shows all available GIDs
- **Documentation**: Constants file documents field purposes
- **Simplicity**: No configuration infrastructure for MVP
- **Reliability**: No runtime discovery means no discovery failures
- **Performance**: Direct lookup by known GID, no extra API calls

### Negative

- **Code change required**: Adding or changing a GID requires code change and deploy
- **Environment coupling**: Same GIDs assumed across environments (can use constants per environment)
- **Limited extensibility**: New fields require code changes until post-MVP
- **Not customer-ready**: External customers cannot customize field mappings in MVP

### Neutral

- **Post-MVP migration**: Static constants can coexist with configuration; not a breaking change
- **Documentation burden**: Constants file must be kept in sync with Asana field names (comments)
- **Testing**: Unit tests must use consistent GID mocks

## Compliance

### How This Decision Is Enforced

1. **Code review checklist**:
   - [ ] Custom field GIDs use constants from `custom_fields.py`
   - [ ] No hardcoded GID strings inline in extractor code
   - [ ] New fields added to constants file with documented name
   - [ ] GID source documented (where the GID came from)

2. **Linting rules**:
   ```python
   # Disallow inline GID strings in extractors
   # Bad:
   mrr = extract(task, "1205511992584993")

   # Good:
   from .custom_fields import MRR_GID
   mrr = extract(task, MRR_GID)
   ```

3. **Constants file structure**:
   ```python
   # Each constant must have:
   # 1. Field name comment
   # 2. Field type comment
   # 3. Optional notes about derivation

   # MRR (Monthly Recurring Revenue)
   # Type: number
   MRR_GID = "1205511992584993"
   ```

4. **Testing requirements**:
   - [ ] Unit tests mock custom field extraction
   - [ ] Test fixtures use consistent GID values
   - [ ] Integration tests (if using real Asana) verify GID correctness

5. **Documentation**:
   - [ ] `custom_fields.py` is self-documenting via comments
   - [ ] README section explains GID management
   - [ ] Migration guide for post-MVP configuration
