# Field Resolver

> How field names resolve to Asana custom field GIDs

---

## The Problem

Asana custom fields are identified by GIDs, but developers use names:

```python
# Developer writes:
business.get_custom_fields().set("Company ID", "ACME-001")

# API needs:
# {"custom_fields": {"1234567890": "ACME-001"}}
```

---

## How CustomFieldAccessor Resolves

The SDK's `CustomFieldAccessor` handles name-to-GID mapping:

```python
class CustomFieldAccessor:
    """Accessor for task custom fields."""

    def __init__(self, custom_fields: list[dict]):
        # Build name -> field mapping
        self._fields: dict[str, dict] = {}
        for field in custom_fields:
            name = field.get("name", "")
            self._fields[name.lower()] = field  # Case-insensitive

    def get(self, name: str) -> Any:
        """Get field value by name."""
        field = self._fields.get(name.lower())
        if field is None:
            return None

        # Return appropriate value based on field type
        if "text_value" in field:
            return field["text_value"]
        if "number_value" in field:
            return field["number_value"]
        if "enum_value" in field:
            return field["enum_value"]  # {"gid": "...", "name": "..."}
        if "multi_enum_values" in field:
            return field["multi_enum_values"]

        return None

    def set(self, name: str, value: Any) -> None:
        """Set field value by name."""
        # Store modification (resolved at save time)
        self._modifications[name] = value
```

---

## Case-Insensitive Lookup

Field names are matched case-insensitively:

```python
# All of these work:
accessor.get("Company ID")
accessor.get("company id")
accessor.get("COMPANY ID")

# Implementation
def get(self, name: str) -> Any:
    field = self._fields.get(name.lower())
    ...
```

---

## Resolution at Save Time

Field names resolve to GIDs when building the API request:

```python
class CustomFieldAccessor:
    def get_modifications_for_api(self) -> dict[str, Any]:
        """Convert modifications to API format (GID keys)."""
        result = {}
        for name, value in self._modifications.items():
            field = self._fields.get(name.lower())
            if field is None:
                raise ValueError(f"Unknown custom field: {name}")

            gid = field["gid"]
            result[gid] = self._convert_value_for_api(field, value)

        return result

    def _convert_value_for_api(self, field: dict, value: Any) -> Any:
        """Convert value to API format."""
        field_type = field.get("type")

        if field_type == "enum":
            # Find enum option GID by name
            return self._resolve_enum_gid(field, value)
        if field_type == "multi_enum":
            # Find multiple enum option GIDs
            return [self._resolve_enum_gid(field, v) for v in value]

        return value
```

---

## Enum Option Resolution

Enum values resolve names to option GIDs:

```python
def _resolve_enum_gid(self, field: dict, value: str | None) -> str | None:
    """Resolve enum option name to GID."""
    if value is None:
        return None

    enum_options = field.get("enum_options", [])
    for option in enum_options:
        if option.get("name", "").lower() == value.lower():
            return option["gid"]

    raise ValueError(f"Unknown enum option '{value}' for field '{field['name']}'")
```

---

## Caching Resolver Results

Avoid re-resolving on each access:

```python
class CustomFieldAccessor:
    def __init__(self, custom_fields: list[dict]):
        self._fields: dict[str, dict] = {}
        self._gid_cache: dict[str, str] = {}  # name -> gid

        for field in custom_fields:
            name = field.get("name", "")
            lower_name = name.lower()
            self._fields[lower_name] = field
            self._gid_cache[lower_name] = field["gid"]

    def get_gid(self, name: str) -> str | None:
        """Get field GID by name (cached)."""
        return self._gid_cache.get(name.lower())
```

---

## Handling Unknown Fields

What happens when a field name doesn't exist:

```python
# On get: returns None
value = accessor.get("Nonexistent Field")  # None

# On set: stored in modifications, error at save time
accessor.set("Nonexistent Field", "value")  # No error yet
# ... later at save:
# ValueError: Unknown custom field: Nonexistent Field
```

### Strict Mode

Optional strict validation:

```python
def set(self, name: str, value: Any, strict: bool = False) -> None:
    """Set field value.

    Args:
        name: Field name
        value: New value
        strict: If True, raise error for unknown fields
    """
    if strict and name.lower() not in self._fields:
        raise ValueError(f"Unknown custom field: {name}")

    self._modifications[name] = value
```

---

## Field Metadata Access

Get information about a field:

```python
def get_field_info(self, name: str) -> dict | None:
    """Get field metadata by name."""
    return self._fields.get(name.lower())

# Usage
info = accessor.get_field_info("Unit Status")
# {
#     "gid": "123",
#     "name": "Unit Status",
#     "type": "enum",
#     "enum_options": [
#         {"gid": "1", "name": "Active"},
#         {"gid": "2", "name": "Paused"},
#     ]
# }
```

---

## Available Fields

List all available field names:

```python
def get_available_fields(self) -> list[str]:
    """Get list of available field names."""
    return [
        field["name"]
        for field in self._fields.values()
    ]

# Usage
fields = accessor.get_available_fields()
# ["Company ID", "MRR", "Booking Type", ...]
```

---

## Related

- [field-accessor-pattern.md](field-accessor-pattern.md) - Property pattern
- [field-types.md](field-types.md) - Type-specific handling
- [patterns-fields.md](patterns-fields.md) - Common patterns
