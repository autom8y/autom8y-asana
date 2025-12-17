# Field Patterns

> Common patterns for custom field implementation

---

## Pattern: Full Property Set

Complete property with getter, setter, deleter:

```python
class Business(Task):
    class Fields:
        COMPANY_ID = "Company ID"

    @property
    def company_id(self) -> str | None:
        """Company identifier (custom field)."""
        return self.get_custom_fields().get(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

    @company_id.deleter
    def company_id(self) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, None)

# Usage
business.company_id = "ACME-001"  # Set
print(business.company_id)        # Get
del business.company_id           # Clear
```

---

## Pattern: Validated Property

Property with validation in setter:

```python
@property
def contact_email(self) -> str | None:
    return self.get_custom_fields().get(self.Fields.CONTACT_EMAIL)

@contact_email.setter
def contact_email(self, value: str | None) -> None:
    if value is not None:
        # Basic email validation
        if "@" not in value or "." not in value:
            raise ValueError(f"Invalid email format: {value}")
    self.get_custom_fields().set(self.Fields.CONTACT_EMAIL, value)
```

---

## Pattern: Normalized Property

Property that normalizes values:

```python
@property
def contact_phone(self) -> str | None:
    return self.get_custom_fields().get(self.Fields.CONTACT_PHONE)

@contact_phone.setter
def contact_phone(self, value: str | None) -> None:
    if value:
        # Normalize phone: remove non-digits, format
        digits = ''.join(c for c in value if c.isdigit())
        if len(digits) == 10:
            value = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            value = f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    self.get_custom_fields().set(self.Fields.CONTACT_PHONE, value)
```

---

## Pattern: Derived Property

Property computed from other fields:

```python
@property
def full_address(self) -> str:
    """Full address (derived from address fields)."""
    parts = []
    if self.line_1:
        parts.append(self.line_1)
    if self.line_2:
        parts.append(self.line_2)

    city_line = ", ".join(filter(None, [
        self.city, self.state, self.postal_code
    ]))
    if city_line:
        parts.append(city_line)

    if self.country:
        parts.append(self.country)

    return "\n".join(parts) if parts else ""
```

---

## Pattern: Aggregated Property

Property that aggregates from children:

```python
@property
def total_mrr(self) -> Decimal:
    """Total MRR across all units."""
    if not self._unit_holder:
        return Decimal("0")
    return sum(
        (u.mrr or Decimal("0"))
        for u in self._unit_holder.units
    )

@property
def active_unit_count(self) -> int:
    """Count of active units."""
    if not self._unit_holder:
        return 0
    return sum(
        1 for u in self._unit_holder.units
        if u.unit_status == "Active"
    )
```

---

## Pattern: Enum with Validation

Enum property that validates against known options:

```python
VALID_STATUSES = {"Active", "Paused", "Cancelled"}

@property
def unit_status(self) -> str | None:
    value = self.get_custom_fields().get(self.Fields.UNIT_STATUS)
    if isinstance(value, dict):
        return value.get("name")
    return value

@unit_status.setter
def unit_status(self, value: str | None) -> None:
    if value is not None and value not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{value}'. "
            f"Must be one of: {', '.join(VALID_STATUSES)}"
        )
    self.get_custom_fields().set(self.Fields.UNIT_STATUS, value)
```

---

## Pattern: List Field Methods

Helpers for multi-value fields:

```python
@property
def products(self) -> list[str]:
    value = self.get_custom_fields().get(self.Fields.PRODUCTS)
    if value is None:
        return []
    return [v.get("name") if isinstance(v, dict) else v for v in value]

@products.setter
def products(self, value: list[str] | None) -> None:
    self.get_custom_fields().set(self.Fields.PRODUCTS, value or [])

def add_product(self, product: str) -> None:
    """Add product if not already present."""
    current = self.products
    if product not in current:
        self.products = current + [product]

def remove_product(self, product: str) -> None:
    """Remove product if present."""
    current = self.products
    if product in current:
        self.products = [p for p in current if p != product]

def has_product(self, product: str) -> bool:
    """Check if product is in list."""
    return product in self.products
```

---

## Pattern: Change Detection

Check if specific field changed:

```python
def is_field_modified(self, field_name: str) -> bool:
    """Check if a specific field has been modified."""
    mods = self.get_custom_fields()._modifications
    return field_name in mods

def get_original_value(self, field_name: str) -> Any:
    """Get original value before modifications."""
    accessor = self.get_custom_fields()
    if field_name in accessor._modifications:
        # Return original from field data
        return accessor._get_original(field_name)
    return accessor.get(field_name)

# Usage
business.company_id = "NEW-ID"
if business.is_field_modified("Company ID"):
    old = business.get_original_value("Company ID")
    print(f"Changed from {old} to {business.company_id}")
```

---

## Pattern: Bulk Field Updates

Update multiple fields at once:

```python
def update_fields(self, **fields) -> None:
    """Update multiple custom fields.

    Args:
        **fields: Field name -> value pairs
    """
    for name, value in fields.items():
        # Convert snake_case to Title Case
        field_name = name.replace("_", " ").title()
        self.get_custom_fields().set(field_name, value)

# Usage
business.update_fields(
    company_id="ACME-001",
    mrr=5000,
    booking_type="Direct"
)
```

---

## Pattern: Field Groups

Group related fields:

```python
class Business(Task):
    class AddressFields:
        """Address-related fields."""
        LINE_1 = "Line 1"
        LINE_2 = "Line 2"
        CITY = "City"
        STATE = "State"
        POSTAL_CODE = "Postal Code"

    class FinancialFields:
        """Financial fields."""
        MRR = "MRR"
        CREDIT_BALANCE = "Credit Balance"
        BILLING_SCHEDULE = "Billing Schedule"

    def get_address_dict(self) -> dict[str, str | None]:
        """Get all address fields as dict."""
        return {
            "line_1": self.line_1,
            "line_2": self.line_2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
        }
```

---

## Anti-Pattern: Direct Accessor Mutation

Don't bypass properties:

```python
# BAD: Bypasses validation
self.get_custom_fields()._modifications["Email"] = "invalid"

# GOOD: Use property setter
self.contact_email = "invalid"  # Raises ValidationError
```

---

## Pattern: Cascading Field Property

Property for fields that cascade from root to descendants (ADR-0054):

```python
class Business(Task):
    class CascadingFields:
        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            targets=["Unit", "Offer", "Process"],
        )

    @property
    def office_phone(self) -> str | None:
        """Office phone (cascading field - single source of truth)."""
        return self.get_custom_fields().get(self.Fields.OFFICE_PHONE)

    @office_phone.setter
    def office_phone(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.OFFICE_PHONE, value)
        # Note: call session.cascade_field(business, "Office Phone") to propagate
```

---

## Pattern: Inherited Field Property

Property for fields that inherit from parent chain (ADR-0054):

```python
class Offer(Task):
    @property
    def vertical(self) -> str | None:
        """Vertical (inherited from Unit unless overridden)."""
        if self._is_field_overridden("Vertical"):
            return self.get_custom_fields().get("Vertical")
        if self._unit:
            return self._unit.vertical
        return None

    @vertical.setter
    def vertical(self, value: str | None) -> None:
        """Set vertical locally, marking as overridden."""
        self.get_custom_fields().set("Vertical", value)
        self.get_custom_fields().set("Vertical Override", "Yes")

    def inherit_vertical(self) -> None:
        """Clear override, inherit from parent."""
        self.get_custom_fields().remove("Vertical")
        self.get_custom_fields().remove("Vertical Override")
```

---

## Related

- [field-accessor-pattern.md](field-accessor-pattern.md) - Basic pattern
- [field-types.md](field-types.md) - Type-specific handling
- [default-fallback-override.md](default-fallback-override.md) - Default values
- [cascading-inherited-fields.md](cascading-inherited-fields.md) - Cascading and inherited field patterns (ADR-0054)
