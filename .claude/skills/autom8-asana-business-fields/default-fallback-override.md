# Default, Fallback, Override

> Resolution order for custom field values

---

## Resolution Priority

When reading a field value, check in this order:

1. **Asana value**: Current value from API
2. **Default**: Computed from other fields
3. **Fallback**: External source (future: SQL, API)
4. **None**: No value available

```python
@property
def full_name(self) -> str | None:
    # 1. Try Asana value first
    value = self.get_custom_fields().get(self.Fields.FULL_NAME)
    if value:
        return value

    # 2. Try default (computed)
    default = self._compute_full_name_default()
    if default:
        return default

    # 3. Fallback (future: external source)
    # fallback = self._get_full_name_fallback()

    # 4. None
    return None
```

---

## Default Values

Defaults are computed from other available data:

### From Other Fields

```python
@property
def full_name(self) -> str | None:
    """Full name with default from first + last."""
    value = self.get_custom_fields().get(self.Fields.FULL_NAME)
    if value:
        return value

    # Default: combine first and last
    first = self.first_name
    last = self.last_name
    if first and last:
        return f"{first} {last}"
    return first or last

@property
def display_name(self) -> str:
    """Display name with default from task name."""
    return self.company_name or self.name or "Unnamed"
```

### From Related Entities

```python
@property
def office_phone(self) -> str | None:
    """Office phone with default from business."""
    value = self.get_custom_fields().get(self.Fields.OFFICE_PHONE)
    if value:
        return value

    # Default from parent business
    business = self.business
    if business:
        return business.office_phone
    return None

@property
def time_zone(self) -> str | None:
    """Time zone with default from address."""
    value = self.get_custom_fields().get(self.Fields.TIME_ZONE)
    if value:
        return value

    # Default from business address (sibling of hours)
    business = self.business
    if business and business.address:
        return business.address.time_zone
    return None
```

---

## Computed Defaults

Complex defaults with logic:

```python
@property
def name_display(self) -> str:
    """Task name with intelligent default."""
    # Use task name if set
    if self.name and self.name != "New Task":
        return self.name

    # For contacts: use full name
    if isinstance(self, Contact):
        return self.full_name or "New Contact"

    # For units: use vertical + MRR pattern
    if isinstance(self, Unit):
        vertical = self.vertical or "Unknown"
        mrr = self.mrr or Decimal("0")
        return f"{vertical} - ${mrr:,.0f}"

    return "New Task"
```

---

## Override Pattern

Force default even when Asana has a value:

```python
@property
def calculated_mrr(self) -> Decimal:
    """MRR always calculated from units (override pattern)."""
    # Always compute, ignore stored value
    if self._unit_holder is None:
        return Decimal("0")
    return sum(
        (u.mrr or Decimal("0"))
        for u in self._unit_holder.units
    )

# Usage
business.mrr           # Stored value from Asana
business.calculated_mrr  # Always computed
```

### Optional Override Flag

```python
def get_mrr(self, override: bool = False) -> Decimal | None:
    """Get MRR with optional override.

    Args:
        override: If True, always compute from units.
                 If False (default), use stored value.
    """
    if override:
        return self._compute_total_mrr()

    value = self.get_custom_fields().get(self.Fields.MRR)
    if value is not None:
        return Decimal(str(value))

    # Fall back to computed
    return self._compute_total_mrr()
```

---

## Fallback Sources (Future)

Placeholders for external data sources:

```python
class FieldFallbackMixin:
    """Mixin for field fallback support."""

    _fallback_provider: FallbackProvider | None = None

    def set_fallback_provider(self, provider: FallbackProvider) -> None:
        """Set external fallback source."""
        self._fallback_provider = provider

    def _get_fallback(self, field_name: str) -> Any:
        """Get value from fallback provider."""
        if self._fallback_provider is None:
            return None
        return self._fallback_provider.get(self.gid, field_name)

# Future implementation
class SQLFallbackProvider:
    """Fallback to SQL database."""

    def get(self, entity_gid: str, field_name: str) -> Any:
        # Query SQL for field value
        ...

# Usage
business.set_fallback_provider(SQLFallbackProvider(db))
```

---

## Default on Write

Set default when writing if no value provided:

```python
@property
def created_date(self) -> date | None:
    value = self.get_custom_fields().get(self.Fields.CREATED_DATE)
    if value:
        return date.fromisoformat(value)
    return None

@created_date.setter
def created_date(self, value: date | None) -> None:
    if value is None:
        # Default to today if clearing
        value = date.today()
    self.get_custom_fields().set(
        self.Fields.CREATED_DATE,
        value.isoformat()
    )
```

---

## Cascading Defaults

Defaults that cascade through hierarchy:

```python
@property
def billing_schedule(self) -> str | None:
    """Billing schedule with cascading default."""
    # Unit's own value
    value = self.get_custom_fields().get(self.Fields.BILLING_SCHEDULE)
    if value:
        return value

    # Default from business
    business = self.business
    if business:
        return business.billing_schedule

    # System default
    return "Monthly"
```

---

## Validation with Defaults

Ensure valid values with fallback:

```python
VALID_VERTICALS = {"Legal", "Medical", "Home Services", "Other"}

@property
def vertical(self) -> str:
    """Vertical with validation and default."""
    value = self.get_custom_fields().get(self.Fields.VERTICAL)

    # Extract name from enum dict
    if isinstance(value, dict):
        value = value.get("name")

    # Validate
    if value in VALID_VERTICALS:
        return value

    # Default for invalid/missing
    return "Other"
```

---

## Related

- [field-accessor-pattern.md](field-accessor-pattern.md) - Basic accessor pattern
- [field-types.md](field-types.md) - Type-specific handling
- [patterns-fields.md](patterns-fields.md) - Common patterns
