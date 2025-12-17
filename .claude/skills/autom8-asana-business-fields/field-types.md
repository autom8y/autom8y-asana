# Field Types

> Handling different custom field types from Asana API

---

## Text Fields

Simple string values:

```python
# API returns: "Hello World" or None

@property
def company_name(self) -> str | None:
    """Company name (text field)."""
    return self.get_custom_fields().get(self.Fields.COMPANY_NAME)

@company_name.setter
def company_name(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.COMPANY_NAME, value)
```

### Text with Validation

```python
import re

@property
def contact_email(self) -> str | None:
    return self.get_custom_fields().get(self.Fields.CONTACT_EMAIL)

@contact_email.setter
def contact_email(self, value: str | None) -> None:
    if value and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', value):
        raise ValueError(f"Invalid email: {value}")
    self.get_custom_fields().set(self.Fields.CONTACT_EMAIL, value)
```

---

## Number Fields

API returns float, convert as needed:

```python
# API returns: 5000.0 or None

@property
def mrr(self) -> Decimal | None:
    """MRR as Decimal for precision."""
    value = self.get_custom_fields().get(self.Fields.MRR)
    return Decimal(str(value)) if value is not None else None

@mrr.setter
def mrr(self, value: Decimal | int | float | None) -> None:
    # API expects float
    self.get_custom_fields().set(
        self.Fields.MRR,
        float(value) if value is not None else None
    )

@property
def aggression_level(self) -> int | None:
    """Aggression level as integer."""
    value = self.get_custom_fields().get(self.Fields.AGGRESSION_LEVEL)
    return int(value) if value is not None else None

@aggression_level.setter
def aggression_level(self, value: int | None) -> None:
    self.get_custom_fields().set(self.Fields.AGGRESSION_LEVEL, value)
```

---

## Enum Fields

API returns dict with gid and name:

```python
# API returns: {"gid": "123", "name": "Active", "enabled": true}

@property
def unit_status(self) -> str | None:
    """Unit status (enum field)."""
    value = self.get_custom_fields().get(self.Fields.UNIT_STATUS)
    if isinstance(value, dict):
        return value.get("name")
    return value

@unit_status.setter
def unit_status(self, value: str | None) -> None:
    # Set by name, accessor resolves to correct option
    self.get_custom_fields().set(self.Fields.UNIT_STATUS, value)
```

### Enum with Python Enum

```python
from enum import Enum

class UnitStatus(str, Enum):
    ACTIVE = "Active"
    PAUSED = "Paused"
    CANCELLED = "Cancelled"

@property
def unit_status(self) -> UnitStatus | None:
    """Unit status as enum."""
    value = self.get_custom_fields().get(self.Fields.UNIT_STATUS)
    if isinstance(value, dict):
        value = value.get("name")
    return UnitStatus(value) if value else None

@unit_status.setter
def unit_status(self, value: UnitStatus | str | None) -> None:
    if isinstance(value, UnitStatus):
        value = value.value
    self.get_custom_fields().set(self.Fields.UNIT_STATUS, value)
```

---

## Multi-Enum Fields

API returns list of dicts:

```python
# API returns: [
#   {"gid": "1", "name": "Google", "enabled": true},
#   {"gid": "2", "name": "Meta", "enabled": true}
# ]

@property
def products(self) -> list[str]:
    """Products (multi-enum field)."""
    value = self.get_custom_fields().get(self.Fields.PRODUCTS)
    if value is None:
        return []
    if isinstance(value, list):
        return [
            v.get("name") if isinstance(v, dict) else v
            for v in value
        ]
    return []

@products.setter
def products(self, value: list[str] | None) -> None:
    # Set as list of names
    self.get_custom_fields().set(
        self.Fields.PRODUCTS,
        value or []
    )
```

### Adding/Removing from Multi-Enum

```python
def add_product(self, product: str) -> None:
    """Add a product to the list."""
    current = self.products
    if product not in current:
        current.append(product)
        self.products = current

def remove_product(self, product: str) -> None:
    """Remove a product from the list."""
    current = self.products
    if product in current:
        current.remove(product)
        self.products = current
```

---

## Date Fields

API returns ISO string:

```python
from datetime import date

# API returns: "2024-12-31" or None

@property
def start_date(self) -> date | None:
    """Start date (date field)."""
    value = self.get_custom_fields().get(self.Fields.START_DATE)
    if value:
        return date.fromisoformat(value)
    return None

@start_date.setter
def start_date(self, value: date | str | None) -> None:
    if isinstance(value, date):
        value = value.isoformat()
    self.get_custom_fields().set(self.Fields.START_DATE, value)
```

---

## Datetime Fields

API returns ISO string with time:

```python
from datetime import datetime

# API returns: "2024-12-31T14:30:00.000Z"

@property
def last_contact(self) -> datetime | None:
    """Last contact timestamp."""
    value = self.get_custom_fields().get(self.Fields.LAST_CONTACT)
    if value:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    return None

@last_contact.setter
def last_contact(self, value: datetime | str | None) -> None:
    if isinstance(value, datetime):
        value = value.isoformat()
    self.get_custom_fields().set(self.Fields.LAST_CONTACT, value)
```

---

## People Fields

API returns list of user refs:

```python
# API returns: [{"gid": "123", "name": "John Doe"}]

@property
def assigned_to(self) -> list[str]:
    """Assigned users (people field)."""
    value = self.get_custom_fields().get(self.Fields.ASSIGNED_TO)
    if value is None:
        return []
    if isinstance(value, list):
        return [
            v.get("name") if isinstance(v, dict) else v
            for v in value
        ]
    return []

# People fields are typically read-only in custom fields
# Assignment is done via task.assignee
```

---

## Currency Fields

Number with currency context:

```python
from decimal import Decimal

@property
def budget(self) -> Decimal | None:
    """Budget amount."""
    value = self.get_custom_fields().get(self.Fields.BUDGET)
    return Decimal(str(value)) if value is not None else None

@property
def currency(self) -> str:
    """Currency code (with default USD)."""
    value = self.get_custom_fields().get(self.Fields.CURRENCY)
    if isinstance(value, dict):
        value = value.get("name")
    return value or "USD"

@property
def formatted_budget(self) -> str:
    """Budget formatted with currency."""
    amount = self.budget or Decimal("0")
    currency = self.currency
    return f"{currency} {amount:,.2f}"
```

---

## Percentage Fields

Number representing percentage:

```python
@property
def discount(self) -> Decimal | None:
    """Discount percentage (0-100)."""
    value = self.get_custom_fields().get(self.Fields.DISCOUNT)
    return Decimal(str(value)) if value is not None else None

@discount.setter
def discount(self, value: Decimal | float | None) -> None:
    if value is not None and not (0 <= value <= 100):
        raise ValueError("Discount must be 0-100")
    self.get_custom_fields().set(
        self.Fields.DISCOUNT,
        float(value) if value is not None else None
    )

@property
def discount_multiplier(self) -> Decimal:
    """Discount as multiplier (e.g., 0.9 for 10% off)."""
    discount = self.discount or Decimal("0")
    return 1 - (discount / 100)
```

---

## Related

- [field-accessor-pattern.md](field-accessor-pattern.md) - Property patterns
- [default-fallback-override.md](default-fallback-override.md) - Default handling
- [patterns-fields.md](patterns-fields.md) - Common patterns
