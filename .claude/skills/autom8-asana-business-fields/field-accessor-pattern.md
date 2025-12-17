# Field Accessor Pattern

> How typed properties delegate to CustomFieldAccessor (ADR-0051)

---

## The Pattern

Every custom field property follows this pattern:

```python
class Business(Task):
    class Fields:
        COMPANY_ID = "Company ID"  # Constant for field name

    @property
    def company_id(self) -> str | None:
        """Company identifier (custom field)."""
        return self.get_custom_fields().get(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)
```

---

## Fields Inner Class

Use `Fields` class for discoverability:

```python
class Business(Task):
    """Business with typed field accessors."""

    class Fields:
        """Custom field name constants.

        Use these constants for IDE autocomplete and to avoid
        typos in field names.
        """
        # String fields
        COMPANY_ID = "Company ID"
        COMPANY_NAME = "Company Name"
        OFFICE_PHONE = "Office Phone"

        # Numeric fields
        MRR = "MRR"
        CREDIT_BALANCE = "Credit Balance"
        AGGRESSION_LEVEL = "Aggression Level"

        # Enum fields
        BOOKING_TYPE = "Booking Type"
        BILLING_SCHEDULE = "Billing Schedule"
        TIME_ZONE = "Time Zone"
```

Benefits:
- IDE autocomplete: `Business.Fields.` shows all options
- Typo prevention: Compile-time string references
- Documentation: Group fields by type or purpose
- Refactoring: Change name in one place

---

## CustomFieldAccessor Integration

The SDK's `CustomFieldAccessor` handles:

1. **Name-to-GID resolution**: "Company ID" -> "123456789"
2. **Value storage**: Tracks current and modified values
3. **Change detection**: `has_changes()` compares to original
4. **Serialization**: Includes changes in `model_dump()`

```python
# Get accessor from Task
accessor = task.get_custom_fields()

# Read value (resolves by name)
value = accessor.get("Company ID")

# Write value (marks as modified)
accessor.set("Company ID", "NEW-VALUE")

# Check for changes
if accessor.has_changes():
    print("Custom fields modified")

# Get all modifications
mods = accessor._modifications
# {"Company ID": "NEW-VALUE"}
```

---

## Property Implementation Patterns

### Simple String Field

```python
@property
def company_id(self) -> str | None:
    """Company identifier (custom field)."""
    return self.get_custom_fields().get(self.Fields.COMPANY_ID)

@company_id.setter
def company_id(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.COMPANY_ID, value)
```

### Number Field with Decimal

```python
@property
def mrr(self) -> Decimal | None:
    """Monthly recurring revenue (custom field)."""
    value = self.get_custom_fields().get(self.Fields.MRR)
    return Decimal(str(value)) if value is not None else None

@mrr.setter
def mrr(self, value: Decimal | int | float | None) -> None:
    # Convert to float for API
    self.get_custom_fields().set(
        self.Fields.MRR,
        float(value) if value is not None else None
    )
```

### Enum Field

```python
@property
def booking_type(self) -> str | None:
    """Booking type (enum custom field)."""
    value = self.get_custom_fields().get(self.Fields.BOOKING_TYPE)
    # API returns {"gid": "...", "name": "..."}
    if isinstance(value, dict):
        return value.get("name")
    return value

@booking_type.setter
def booking_type(self, value: str | None) -> None:
    # Set by enum option name
    self.get_custom_fields().set(self.Fields.BOOKING_TYPE, value)
```

### Read-Only Property

```python
@property
def created_by(self) -> str | None:
    """Who created this entity (read-only)."""
    value = self.get_custom_fields().get(self.Fields.CREATED_BY)
    if isinstance(value, dict):
        return value.get("name")
    return value
    # No setter - read-only
```

---

## Delete/Clear Pattern

To clear a field value:

```python
@property
def company_id(self) -> str | None:
    return self.get_custom_fields().get(self.Fields.COMPANY_ID)

@company_id.setter
def company_id(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

@company_id.deleter
def company_id(self) -> None:
    """Clear the company ID field."""
    self.get_custom_fields().set(self.Fields.COMPANY_ID, None)

# Usage
del business.company_id  # Clears the field
```

---

## Computed Properties

Some properties derive from multiple fields:

```python
@property
def display_name(self) -> str:
    """Display name (computed from company_name or name)."""
    return self.company_name or self.name or "Unnamed Business"

@property
def total_mrr(self) -> Decimal:
    """Total MRR across all units (computed)."""
    if not hasattr(self, '_unit_holder') or self._unit_holder is None:
        return Decimal("0")
    return sum(
        (u.mrr or Decimal("0")) for u in self._unit_holder.units
    )
```

---

## Type Conversion Summary

| Python Type | Getter Conversion | Setter Conversion |
|-------------|-------------------|-------------------|
| `str` | Direct return | Direct set |
| `int` | `int(value)` | `int(value)` |
| `float` | `float(value)` | `float(value)` |
| `Decimal` | `Decimal(str(value))` | `float(value)` |
| `date` | `date.fromisoformat(value)` | `value.isoformat()` |
| `datetime` | `datetime.fromisoformat(value)` | `value.isoformat()` |
| `list[str]` | Extract names from dicts | Pass as-is |

---

## Validation in Accessors

Add validation in setters:

```python
@property
def aggression_level(self) -> int | None:
    value = self.get_custom_fields().get(self.Fields.AGGRESSION_LEVEL)
    return int(value) if value is not None else None

@aggression_level.setter
def aggression_level(self, value: int | None) -> None:
    if value is not None and not (1 <= value <= 10):
        raise ValueError("Aggression level must be 1-10")
    self.get_custom_fields().set(self.Fields.AGGRESSION_LEVEL, value)
```

---

## Related

- [field-types.md](field-types.md) - Type-specific handling details
- [field-resolver.md](field-resolver.md) - How field names resolve
- [default-fallback-override.md](default-fallback-override.md) - Default value patterns
