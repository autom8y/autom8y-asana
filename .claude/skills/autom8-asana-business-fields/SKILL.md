# Business Model Fields

> Custom field type mapping, accessors, resolvers, and validation

---

## Activation Triggers

**Use this skill when**:
- Implementing typed custom field properties on business entities
- Working with CustomFieldAccessor patterns
- Understanding field type conversions (enum, multi-enum, number, etc.)
- Implementing default/fallback/override resolution for fields
- Designing field resolver patterns

**Keywords**: custom field, CustomFieldAccessor, field getter, field setter, @property, field.get(), field.set(), typed accessor, field resolver, enum field, multi-enum, default value, fallback, cascading field, inherited field, cascade_field, CascadingFieldDef, InheritedFieldDef, allow_override, multi-level cascade, target_types, should_update_descendant, override opt-in, no override

**File patterns**: `**/models/*field*.py`, `**/fields/*.py`, `**/models/business/*.py`

---

## Architecture Decision: Hybrid Approach (ADR-0051)

**Decision**: Use typed property accessors that delegate to CustomFieldAccessor for storage and change tracking.

Benefits:
- IDE autocomplete for all business fields
- Type hints provide documentation and static analysis
- Reuses existing CustomFieldAccessor change tracking
- Property pattern is familiar Python idiom
- Type conversion handles API format differences

```python
@property
def company_id(self) -> str | None:
    return self.get_custom_fields().get(self.Fields.COMPANY_ID)

@company_id.setter
def company_id(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.COMPANY_ID, value)
```

---

## Quick Reference

| I need to... | See |
|--------------|-----|
| Understand field accessor pattern | [field-accessor-pattern.md](field-accessor-pattern.md) |
| Implement default/fallback logic | [default-fallback-override.md](default-fallback-override.md) |
| Handle specific field types | [field-types.md](field-types.md) |
| Understand field name resolution | [field-resolver.md](field-resolver.md) |
| See common field patterns | [patterns-fields.md](patterns-fields.md) |
| Implement cascading/inherited fields | [cascading-inherited-fields.md](cascading-inherited-fields.md) |

---

## Core Pattern

```python
class Business(Task):
    """Business with typed custom field accessors."""

    class Fields:
        """Field name constants for IDE discoverability."""
        COMPANY_ID = "Company ID"
        MRR = "MRR"
        BOOKING_TYPE = "Booking Type"

    # Simple string field
    @property
    def company_id(self) -> str | None:
        return self.get_custom_fields().get(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

    # Number field with Decimal conversion
    @property
    def mrr(self) -> Decimal | None:
        value = self.get_custom_fields().get(self.Fields.MRR)
        return Decimal(str(value)) if value is not None else None

    # Enum field with dict extraction
    @property
    def booking_type(self) -> str | None:
        value = self.get_custom_fields().get(self.Fields.BOOKING_TYPE)
        if isinstance(value, dict):
            return value.get("name")
        return value
```

---

## Field Types Summary

| Type | API Returns | Property Returns | Setter Accepts |
|------|-------------|------------------|----------------|
| Text | `str` | `str \| None` | `str \| None` |
| Number | `float` | `Decimal \| None` | `Decimal \| int \| float` |
| Enum | `{"gid": "...", "name": "..."}` | `str \| None` | `str \| None` |
| Multi-enum | `[{"gid": "...", "name": "..."}]` | `list[str]` | `list[str]` |
| Date | `"YYYY-MM-DD"` | `date \| None` | `date \| str` |
| People | `[{"gid": "...", "name": "..."}]` | `list[str]` | `list[str]` |

---

## Change Tracking Integration

All modifications flow through CustomFieldAccessor:

```python
# Setting a value
business.company_id = "NEW-ID"
# Internally: self.get_custom_fields().set("Company ID", "NEW-ID")

# Check for changes
business.get_custom_fields().has_changes()  # True

# Get modifications
business.get_custom_fields()._modifications
# {"Company ID": "NEW-ID"}

# SaveSession detects changes via model_dump()
```

---

## Progressive References

| Document | Lines | Content |
|----------|-------|---------|
| [field-accessor-pattern.md](field-accessor-pattern.md) | ~160 | Property delegation, Fields class, accessor integration |
| [default-fallback-override.md](default-fallback-override.md) | ~140 | Default values, fallback sources, override priority |
| [field-types.md](field-types.md) | ~180 | Enum, multi-enum, number, date, list handling |
| [field-resolver.md](field-resolver.md) | ~100 | Name-to-GID resolution, caching, case handling |
| [patterns-fields.md](patterns-fields.md) | ~100 | Common patterns, validation, change tracking |
| [cascading-inherited-fields.md](cascading-inherited-fields.md) | ~150 | Cascading and inherited field patterns (ADR-0054) |

---

## When to Use Other Skills

| Need | Use Instead |
|------|-------------|
| Field name glossary by entity | [autom8-asana-business-schemas](../autom8-asana-business-schemas/) |
| Navigation between entities | [autom8-asana-business-relationships](../autom8-asana-business-relationships/) |
| SaveSession commit workflows | [autom8-asana-business-workflows](../autom8-asana-business-workflows/) |
| Core SDK CustomFieldAccessor | [autom8-asana-domain](../autom8-asana-domain/) |
