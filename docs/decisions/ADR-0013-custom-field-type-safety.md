# ADR-0013: Custom Field Type Safety

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0030, ADR-0051, ADR-0082, ADR-0083
- **Related**: reference/DATA-MODEL.md

## Context

Asana custom fields are identified by GIDs (globally unique identifiers). The SDK needs type-safe access to 80+ business-specific custom fields across Business, Contact, and Unit models with:

1. **GID Mapping**: Map column names to custom field GIDs for extraction
2. **Type Safety**: Provide typed property accessors with validation
3. **Change Tracking**: Integrate with existing CustomFieldAccessor for SaveSession
4. **Field Discovery**: Auto-generate constants for IDE discoverability
5. **Date Handling**: Rich date API for 8 date-like custom fields

The existing `CustomFieldAccessor` provides string-based access:
```python
accessor = task.get_custom_fields()
accessor.set("Priority", "High")  # Untyped - accepts any value
value = accessor.get("MRR")       # Returns Any
```

Custom field **names** can change (user-editable), but **GIDs** are permanent. Using names for lookup would break extraction if a user renames a field.

## Decision

Implement four-component custom field type safety:

1. **Static GID constants for MVP** with configurable post-MVP extension
2. **Typed property descriptors** delegating to CustomFieldAccessor
3. **Auto-generated Fields class** from descriptor definitions
4. **Arrow library integration** for date fields

### Static GID Constants (MVP)

```python
# autom8_asana/dataframes/models/custom_fields.py

"""Custom field GID constants for MVP task types.

These GIDs are stable identifiers in Asana. Names can change;
GIDs cannot. Each constant documents the current field name
for maintainability.

WARNING: These GIDs are environment-specific. Production GIDs
differ from staging/development.
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
```

### Typed Property Descriptors

```python
class Business(Task):
    """Business entity with typed custom field accessors."""

    class Fields:
        """Field name constants for IDE discoverability."""
        COMPANY_ID = "Company ID"
        BOOKING_TYPE = "Booking Type"
        MRR = "MRR"

    @property
    def company_id(self) -> str | None:
        """Company identifier (custom field)."""
        return self.get_custom_fields().get(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

    @property
    def mrr(self) -> Decimal | None:
        """Monthly recurring revenue (custom field)."""
        value = self.get_custom_fields().get(self.Fields.MRR)
        return Decimal(str(value)) if value is not None else None

    @mrr.setter
    def mrr(self, value: Decimal | None) -> None:
        self.get_custom_fields().set(
            self.Fields.MRR,
            float(value) if value else None
        )
```

### Auto-Generated Fields Class

```python
# Module-level registry for pending field registrations
_pending_fields: dict[int, dict[str, str]] = {}  # owner_id -> {CONSTANT_NAME: "Field Name"}

def _register_custom_field(owner: type[Any], descriptor: CustomFieldDescriptor[Any]) -> None:
    """Called during descriptor.__set_name__() to register field for Fields generation."""
    owner_id = id(owner)
    if owner_id not in _pending_fields:
        _pending_fields[owner_id] = {}
    _pending_fields[owner_id][descriptor._constant_name] = descriptor.field_name

class BusinessEntity(Task):
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        # Fields class generation from registered descriptors
        owner_id = id(cls)
        if owner_id in _pending_fields:
            field_constants = _pending_fields.pop(owner_id)

            if field_constants:
                existing_fields = getattr(cls, "Fields", None)

                if existing_fields is not None:
                    # Extend existing Fields class (preserves manual constants)
                    new_constants = {
                        k: v for k, v in field_constants.items()
                        if not hasattr(existing_fields, k)
                    }
                    if new_constants:
                        fields_cls = type("Fields", (existing_fields,), new_constants)
                        cls.Fields = fields_cls
                else:
                    # Create new Fields class
                    fields_cls = type("Fields", (), field_constants)
                    cls.Fields = fields_cls

class CustomFieldDescriptor(Generic[T]):
    ABBREVIATIONS: ClassVar[frozenset[str]] = frozenset({
        "mrr", "ai", "url", "id", "num", "cal", "vca", "sms", "ad"
    })

    def _derive_field_name(self, name: str) -> str:
        """Derive 'Title Case' field name from snake_case property.

        Examples:
            company_id -> "Company ID"
            mrr -> "MRR"
            num_ai_copies -> "Num AI Copies"
        """
        parts = name.split("_")
        result = []
        for part in parts:
            if part.lower() in self.ABBREVIATIONS:
                result.append(part.upper())
            else:
                result.append(part.capitalize())
        return " ".join(result)
```

### Arrow Date Integration

```python
import arrow

class DateField(CustomFieldDescriptor[arrow.Arrow | None]):
    """Date field descriptor using Arrow library."""

    def __get__(self, instance: Any, owner: type) -> arrow.Arrow | None:
        if instance is None:
            return self

        value = instance.get_custom_fields().get(self.field_name)
        if value is None:
            return None

        # Parse ISO date format from Asana
        if isinstance(value, str):
            return arrow.get(value, "YYYY-MM-DD")
        return value

    def __set__(self, instance: Any, value: arrow.Arrow | None) -> None:
        if value is None:
            instance.get_custom_fields().set(self.field_name, None)
        else:
            # Serialize to ISO date format for Asana API
            instance.get_custom_fields().set(self.field_name, value.format("YYYY-MM-DD"))

# Usage
class Process(Task):
    process_due_date = DateField()

process = Process(...)
due = process.process_due_date  # Returns Arrow | None
if due:
    print(due.humanize())       # "in 2 days"
    print(due.format("MMMM D"))  # "December 16"

process.process_due_date = arrow.now().shift(days=7)  # Setter accepts Arrow
```

### Post-MVP Extension (Configurable)

```yaml
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

**Type safety at development time:**
```python
# Static: IDE catches typos, refactoring is safe
mrr = extract(task, MRR_GID)  # IDE knows MRR_GID

# Dynamic: Runtime errors, no IDE help
mrr = extract(task, config["mrr"]["gid"])  # What if key missing?
```

**MVP scope is bounded**: Only Unit (11 fields) and Contact (9 fields) are in scope. 20 constants are manageable.

**GIDs are stable**: Asana guarantees GID stability. Once set, a custom field's GID never changes.

**Code change for field mapping is acceptable**: For MVP, if a new field is needed or a GID changes (rare), a code change is acceptable.

### Why Hybrid Property Pattern?

**Leverages existing CustomFieldAccessor**: The SDK already has `CustomFieldAccessor` with:
- Name-to-GID resolution (case-insensitive)
- Change tracking via `_modifications` dict
- Integration with `model_dump()` for SaveSession

**Properties provide ergonomics:**
```python
# With properties (IDE autocomplete works)
business.company_id = "ABC123"
business.mrr = Decimal("5000.00")

# Without properties (stringly-typed)
business.get_custom_fields().set("Company ID", "ABC123")
```

**Type conversion centralized**: Property getters/setters handle type coercion:
- `mrr` getter: API returns float/int, property returns `Decimal`
- `booking_type` getter: API returns `{"gid": "...", "name": "..."}`, property returns `BookingType` enum

**Change tracking preserved**: All modifications flow through `CustomFieldAccessor`.

### Why Auto-Generate Fields Class?

**DRY Principle**: Field names should not be declared twice (descriptor + Fields constant).

**Two-phase approach works with Pydantic**:
1. `__set_name__` fires for each descriptor as class is being created
2. `__init_subclass__` fires after class creation is complete, with access to all registrations

This matches the pattern already established for `_CACHED_REF_ATTRS` discovery.

**Backward Compatible**: Existing explicit `Fields` classes are extended via inheritance, preserving manual constants.

### Why Arrow Library?

User explicitly requested Arrow. Provides:
- Timezone handling
- Humanization ("2 hours ago")
- Flexible parsing
- Rich comparison operations
- More intuitive API than stdlib datetime with minimal dependency cost

## Alternatives Considered

### Alternative 1: Dynamic Discovery by Name

- **Description**: Discover custom field GIDs by name at runtime by querying project custom field settings
- **Pros**: No hardcoded GIDs; automatically adapts to field name changes
- **Cons**: Extra API call per extraction batch; names can change, breaking discovery; no compile-time type safety; performance overhead
- **Why not chosen**: Performance cost and name instability; GIDs are designed to be stable identifiers

### Alternative 2: Configuration File from Day 1

- **Description**: Use YAML/JSON configuration for field mappings from the start, even for MVP
- **Pros**: Consistent pattern from MVP to post-MVP; no code changes for field mapping updates
- **Cons**: Configuration loading infrastructure needed for MVP; no IDE autocomplete; over-engineering for 2 task types
- **Why not chosen**: MVP has only 2 task types with ~20 fields total; static constants are simpler

### Alternative 3: Field Wrapper Classes

- **Description**: Create 80+ custom field wrapper classes
- **Pros**: Explicit types; clear responsibility
- **Cons**: 80+ classes is excessive; most fields are simple types that don't need custom classes
- **Why not chosen**: Property pattern achieves the same with less code

### Alternative 4: Pure Pydantic Validators

- **Description**: Use Pydantic validators on model fields
- **Pros**: Integrated validation; familiar pattern
- **Cons**: Conflicts with API's dynamic custom field structure where `custom_fields` is a list of dicts; would require complex `model_validator` logic to flatten/unflatten
- **Why not chosen**: Doesn't align with Asana's API structure

### Alternative 5: Custom Metaclass

- **Description**: Create `BusinessEntityMeta` that generates Fields during class creation
- **Pros**: Full control; single-phase
- **Cons**: Conflicts with Pydantic's `ModelMetaclass`; complex inheritance; fragile
- **Why not chosen**: Pydantic v2 already uses its own metaclass; combining is fragile

### Alternative 6: Standard Library datetime

- **Description**: Use stdlib `datetime` instead of Arrow
- **Pros**: No external dependency; standard library
- **Cons**: User explicitly requested Arrow; less intuitive API; no humanization; requires more boilerplate for common operations
- **Why not chosen**: User preference and superior API

## Consequences

### Positive

- **Type safety**: GID constants are typed strings; IDE catches typos
- **IDE support**: Autocomplete shows all available GIDs
- **Documentation**: Constants file documents field purposes
- **Simplicity**: No configuration infrastructure for MVP
- **Reliability**: No runtime discovery means no discovery failures
- **Performance**: Direct lookup by known GID, no extra API calls
- **IDE autocomplete**: For all business fields
- **Type hints**: Provide documentation and static analysis
- **Reuses existing**: CustomFieldAccessor change tracking
- **Property pattern**: Familiar Python idiom
- **Type conversion**: Handles API format differences
- **DRY**: Field names declared once in descriptors
- **Backward Compatible**: `Model.Fields.CONSTANT` continues to work
- **Extensible**: Manual Fields constants preserved via inheritance
- **Rich date API**: Arrow provides humanization, timezone handling, flexible parsing

### Negative

- **Code change required**: Adding or changing a GID requires code change and deploy
- **Environment coupling**: Same GIDs assumed across environments (can use constants per environment)
- **Limited extensibility**: New fields require code changes until post-MVP
- **Not customer-ready**: External customers cannot customize field mappings in MVP
- **Boilerplate**: For 80+ property definitions (18 Business + 21 Contact + 44 Unit)
- **Field name maintenance**: Constants must match Asana field names exactly
- **Property definitions**: Must be maintained as fields change
- **Implicit Generation**: Fields class created "magically" at class definition time (mitigated by documentation)
- **Module-level State**: Registry is module-level (cleaned up immediately after use)
- **External dependency**: Arrow library dependency (minimal cost)

### Neutral

- **Post-MVP migration**: Static constants can coexist with configuration; not a breaking change
- **Documentation burden**: Constants file must be kept in sync with Asana field names (comments)
- **Testing**: Unit tests must use consistent GID mocks
- **Runtime Cost**: Negligible - one-time at class definition
- **Inheritance**: Works correctly - each subclass gets its own Fields class
- **ISO format**: Arrow serializes to ISO date format for Asana API compatibility

## Compliance

### GID Management

1. **Code review checklist**: Custom field GIDs use constants from `custom_fields.py`; no hardcoded GID strings inline
2. **Linting rules**: Disallow inline GID strings in extractors
3. **Constants file structure**: Each constant has field name comment, field type comment, optional derivation notes
4. **Testing requirements**: Unit tests mock custom field extraction; test fixtures use consistent GID values

### Property Descriptors

1. **Code review checklist**: New custom field properties delegate to `get_custom_fields()`; type conversion in getters; field names defined in `Fields` inner class
2. **Unit tests**:
   ```python
   def test_property_uses_accessor():
       """Property changes tracked via accessor."""
       business = Business.model_validate(response)
       business.company_id = "NEW"
       assert business.get_custom_fields().has_changes()

   def test_type_conversion():
       """Property getter converts API types."""
       business = Business.model_validate(response_with_mrr)
       assert isinstance(business.mrr, Decimal)
   ```

### Fields Generation

1. **Code review checklist**: Descriptors without explicit `field_name` derive names correctly; abbreviations (MRR, VCA, URL, etc.) handled correctly; explicit `field_name` overrides used where needed
2. **Testing requirements**: Field name derivation unit tests; Fields class generation verified for each model; inheritance case tested
3. **Migration checklist**: Remove explicit `Fields` class (or keep if has additional constants); verify all `Model.Fields.CONSTANT` references still work

### Date Fields

1. **Import Arrow**: `import arrow` for date field handling
2. **Serialization**: Arrow dates serialize to ISO format "YYYY-MM-DD"
3. **Type hints**: Properties return `arrow.Arrow | None`
4. **Testing**: Test Arrow parsing, humanization, and serialization
