# ADR-0051: Custom Field Type Safety

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-11
- **Deciders**: Architect
- **Related**: [TDD-0015](../architecture/business-model-tdd.md), [ADR-0030](ADR-0030-custom-field-typing.md)

## Context

The SDK needs typed access to business-specific custom fields like `company_id`, `booking_type`, `mrr`. The existing `CustomFieldAccessor` provides string-based access:

```python
accessor = task.get_custom_fields()
accessor.set("Priority", "High")  # Untyped - accepts any value
value = accessor.get("MRR")       # Returns Any
```

For 80+ business fields across Business, Contact, and Unit models, we need type safety with validation.

### Forces at Play

| Force | Pull Toward |
|-------|-------------|
| Type safety | Wrapper classes (explicit types) |
| IDE autocomplete | Properties (discoverable API) |
| Validation | Pydantic or wrapper classes |
| Change tracking | CustomFieldAccessor (existing) |
| Code volume | Pydantic validators (less boilerplate) |
| Flexibility | CustomFieldAccessor (runtime resolution) |

### Options Considered

| Option | Approach | Type Safe | Change Tracking | Boilerplate |
|--------|----------|-----------|-----------------|-------------|
| A: Field wrapper classes | `OfficePhone`, `CompanyId` classes | Yes | New system | High (80+ classes) |
| B: Pydantic validators | Field definitions on model | Partial | Conflicts with API | Medium |
| C: Hybrid | Properties + CustomFieldAccessor | Yes | Reuses existing | Medium |

## Decision

**Use hybrid approach: typed property accessors that delegate to CustomFieldAccessor for storage and change tracking.**

### Implementation

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

    @property
    def booking_type(self) -> BookingType | None:
        """Booking type enum (custom field)."""
        raw = self.get_custom_fields().get(self.Fields.BOOKING_TYPE)
        if raw is None:
            return None
        # Handle enum_value dict from API
        if isinstance(raw, dict):
            raw = raw.get("name")
        return BookingType(raw) if raw else None

    @booking_type.setter
    def booking_type(self, value: BookingType | None) -> None:
        self.get_custom_fields().set(
            self.Fields.BOOKING_TYPE,
            value.value if value else None
        )
```

## Rationale

### Why Hybrid (Option C)?

1. **Leverages existing CustomFieldAccessor**: The SDK already has `CustomFieldAccessor` with:
   - Name-to-GID resolution (case-insensitive)
   - Change tracking via `_modifications` dict
   - Integration with `model_dump()` for SaveSession

   Building on it rather than replacing avoids duplication and ensures consistency.

2. **Properties provide ergonomics**:
   ```python
   # With properties (IDE autocomplete works)
   business.company_id = "ABC123"
   business.mrr = Decimal("5000.00")

   # Without properties (stringly-typed)
   business.get_custom_fields().set("Company ID", "ABC123")
   ```

3. **Type conversion centralized**: Property getters/setters handle type coercion:
   - `mrr` getter: API returns float/int, property returns `Decimal`
   - `booking_type` getter: API returns `{"gid": "...", "name": "..."}`, property returns `BookingType` enum

4. **Change tracking preserved**: All modifications flow through `CustomFieldAccessor`:
   ```python
   business.company_id = "NEW"  # Calls accessor.set()
   business.get_custom_fields().has_changes()  # True
   business.model_dump()  # Includes custom_fields changes
   ```

### Why Not Option A (Wrapper Classes)?

80+ custom field wrapper classes is excessive:
```python
# Would need 80+ of these
class CompanyIdField:
    def __init__(self, accessor: CustomFieldAccessor):
        self._accessor = accessor

    def get(self) -> str | None:
        return self._accessor.get("Company ID")

    def set(self, value: str | None) -> None:
        self._accessor.set("Company ID", value)
```

Most fields are simple types (str, int, Decimal) that don't need custom classes. The property pattern achieves the same with less code.

### Why Not Option B (Pure Pydantic)?

Pydantic validators on model fields would require:
```python
class Business(Task):
    company_id: str | None = Field(default=None, alias="Company ID")

    @field_validator("company_id", mode="before")
    def extract_company_id(cls, v, values):
        # Parse from custom_fields list
        ...
```

This conflicts with the API's dynamic custom field structure where `custom_fields` is a list of dicts, not flat fields. It would require complex `model_validator` logic to flatten/unflatten.

## Consequences

### Positive
- IDE autocomplete for all business fields
- Type hints provide documentation and static analysis
- Reuses existing CustomFieldAccessor change tracking
- Property pattern is familiar Python idiom
- Type conversion handles API format differences

### Negative
- Boilerplate for 80+ property definitions (18 Business + 21 Contact + 44 Unit)
- Field name constants must match Asana field names exactly
- Property definitions must be maintained as fields change

### Mitigation
- Generate property definitions from field metadata using code generation
- Add validation that field names match known Asana fields at test time
- Document field name update process

## Compliance

### How This Decision Is Enforced

1. **Code review checklist**:
   - [ ] New custom field properties delegate to `get_custom_fields()`
   - [ ] Type conversion in getters, not scattered
   - [ ] Field names defined in `Fields` inner class

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

3. **Field name validation**:
   ```python
   def test_field_names_match_asana():
       """Field constants match Asana custom field names."""
       for name in Business.Fields.__dict__.values():
           if isinstance(name, str):
               # Verify field exists in Asana
               ...
   ```
