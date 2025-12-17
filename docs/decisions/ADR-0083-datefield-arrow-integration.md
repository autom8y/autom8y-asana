# ADR-0083: DateField Arrow Integration

## Metadata
- **Status**: Accepted
- **Author**: Architect (Amended by Orchestrator)
- **Date**: 2025-12-16
- **Amended**: 2025-12-16 (User decision: Arrow required)
- **Deciders**: User, Architect, Principal Engineer
- **Related**: PRD-PATTERNS-A (FR-DATE-001 through FR-DATE-007), TDD-PATTERNS-A, ADR-0081

## Context

The SDK has 8 date-like custom fields across business models, currently stored and returned as text strings:

| Model | Field | Current Type |
|-------|-------|--------------|
| Process | process_due_date | str | None |
| Process | started_at | str | None |
| Process | process_completed_at | str | None |
| Offer | (potential future) | str | None |

These fields store ISO 8601 date strings (e.g., "2025-12-16") in Asana's text custom fields. The current implementation returns raw strings:

```python
@property
def process_due_date(self) -> str | None:
    return self._get_text_field(self.Fields.DUE_DATE)
```

PRD-PATTERNS-A requirement FR-DATE-001 specifies that DateField should return a parsed date type for type-safe date manipulation.

### Forces at Play

1. **Type Safety**: Returning raw strings requires manual parsing at call sites
2. **API Consistency**: Asana stores dates as ISO strings; we transform other types (enum -> str)
3. **User Requirement**: User explicitly requested Arrow library for date handling
4. **Rich API**: Arrow provides timezone handling, humanize, ranges, and parsing flexibility
5. **Asana Date Format**: ISO 8601 dates (`YYYY-MM-DD`) and datetimes (`YYYY-MM-DDTHH:MM:SSZ`)

## Decision

Use Arrow library for DateField, returning `Arrow | None`.

### Implementation

```python
import arrow
from arrow import Arrow

class DateField(CustomFieldDescriptor[Arrow | None]):
    """Descriptor for date custom fields.

    Per ADR-0083: Uses Arrow library for rich date handling.
    Parses ISO 8601 date strings. Converts Arrow to ISO string on write.

    Arrow provides:
    - Timezone-aware datetime handling
    - Human-readable formatting ("2 hours ago")
    - Flexible parsing of various date formats
    - Rich comparison and arithmetic operations
    """

    def _get_value(self, obj: Any) -> Arrow | None:
        value = obj.get_custom_fields().get(self.field_name)
        if value is None or value == "":
            return None
        if isinstance(value, Arrow):
            return value
        if isinstance(value, str):
            try:
                # Arrow handles ISO 8601 dates and datetimes
                return arrow.get(value)
            except (ValueError, arrow.parser.ParserError):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Invalid date value for field %s: %r",
                    self.field_name, value
                )
                return None
        return None

    def _set_value(self, obj: Any, value: Arrow | None) -> None:
        if value is None:
            api_value = None
        else:
            # Serialize to ISO 8601 date format for Asana
            api_value = value.format("YYYY-MM-DD")
        obj.get_custom_fields().set(self.field_name, api_value)
```

### Usage

```python
import arrow

# DateField declaration
process_due_date = DateField()

# Reading (returns Arrow | None)
due = process.process_due_date
if due:
    print(f"Due: {due.format('MMMM D, YYYY')}")  # "December 16, 2025"
    print(f"Humanized: {due.humanize()}")         # "in 2 days"
    print(f"Year: {due.year}, Month: {due.month}")
    print(f"Weekday: {due.format('dddd')}")       # "Tuesday"

    # Timezone conversion
    print(f"UTC: {due.to('UTC')}")
    print(f"Local: {due.to('local')}")

# Writing (accepts Arrow | None)
process.process_due_date = arrow.now().shift(days=7)

# Writing from various formats
process.process_due_date = arrow.get("2025-12-25")
process.process_due_date = arrow.get(2025, 12, 25)
```

## Rationale

### Why Arrow?

| Factor | Arrow | stdlib datetime.date |
|--------|-------|---------------------|
| **User Request** | Explicitly requested | Not requested |
| **Timezone Support** | Full timezone handling | Date-only, no timezone |
| **Humanize** | Built-in ("2 hours ago") | Manual implementation |
| **Parsing** | Flexible, many formats | Strict ISO only |
| **API Richness** | shift(), span(), range() | Basic operations |
| **Learning Curve** | Small (intuitive API) | Already known |

Arrow is the right choice because:
- **User explicitly requested it** - primary deciding factor
- **Rich functionality** - timezone, humanize, flexible parsing
- **Modern API** - more intuitive than stdlib datetime
- **Battle-tested** - widely used, well-maintained

### Why Not stdlib?

While stdlib `datetime.date` would work for basic date handling:
- User explicitly requested Arrow
- Loses timezone information from datetime strings
- No humanize functionality
- Less flexible parsing
- More verbose date arithmetic

### Dependency Management

Arrow is a well-maintained, stable library with minimal transitive dependencies:
- `python-dateutil` (already common in Python projects)
- No compiled extensions (pure Python)

Add to `pyproject.toml`:
```toml
dependencies = [
    "arrow>=1.3.0",
    # ... existing dependencies
]
```

## Alternatives Considered

### Alternative 1: stdlib datetime.date (Architect's Original Recommendation)

- **Description**: Use Python's standard library datetime.date
- **Pros**: Zero dependencies, familiar API
- **Cons**: User explicitly requested Arrow, less powerful
- **Why not chosen**: User decision overrides; Arrow provides better UX

### Alternative 2: Keep String Returns

- **Description**: Return raw ISO strings, let consumers parse
- **Pros**: No transformation, simple
- **Cons**: Violates type safety goal (FR-DATE-001), manual parsing everywhere
- **Why not chosen**: Defeats purpose of typed field descriptors

### Alternative 3: Pendulum Library

- **Description**: Use Pendulum (another date library)
- **Pros**: Similar to Arrow, good timezone support
- **Cons**: User specifically requested Arrow
- **Why not chosen**: User preference for Arrow

## Consequences

### Positive

1. **User Satisfaction**: Implements exactly what was requested
2. **Rich API**: Timezone, humanize, flexible parsing out of the box
3. **Type Safety**: `Arrow | None` return type enables IDE/mypy checking
4. **Developer Experience**: Arrow's API is intuitive and well-documented
5. **Future-Proof**: Full datetime capabilities available if needed

### Negative

1. **New Dependency**: Arrow must be added to project dependencies
   - *Mitigation*: Arrow is stable, well-maintained, minimal sub-dependencies
2. **Learning Curve**: Developers unfamiliar with Arrow need to learn API
   - *Mitigation*: Arrow API is intuitive; stdlib datetime methods also available
3. **Serialization Overhead**: Arrow objects need conversion for JSON/API
   - *Mitigation*: `_set_value` handles conversion automatically

### Neutral

1. **Parse Errors**: Invalid strings return `None` with warning log
2. **ISO Format**: Output uses ISO 8601 date format for Asana compatibility
3. **Setter Accepts Arrow Only**: Not datetime or date (consistent typing)

## Compliance

### Code Review Checklist

- [ ] DateField returns `Arrow | None`, not `str | None` or `date | None`
- [ ] Arrow dependency added to pyproject.toml
- [ ] Invalid date strings return `None` with warning logged
- [ ] Setter accepts `Arrow | None`, converts to ISO string
- [ ] Both date-only and datetime strings parsed correctly

### Testing Requirements

- [ ] Parse ISO date: "2025-12-16" -> Arrow
- [ ] Parse ISO datetime: "2025-12-16T10:30:00Z" -> Arrow (timezone preserved)
- [ ] Parse invalid string: "not-a-date" -> None (with warning)
- [ ] Parse empty string: "" -> None
- [ ] Parse None: None -> None
- [ ] Serialize Arrow: arrow.get("2025-12-16") -> "2025-12-16"
- [ ] Serialize None: None -> None
- [ ] Timezone handling: UTC dates parsed correctly
- [ ] Humanize: Arrow.humanize() works on returned values

### Dependency Requirements

- [ ] `arrow>=1.3.0` added to pyproject.toml dependencies
- [ ] Import works: `from arrow import Arrow`
- [ ] Type hints work: `Arrow | None` recognized by mypy

## Amendment History

| Date | Author | Change |
|------|--------|--------|
| 2025-12-16 | Architect | Initial draft recommending stdlib datetime.date |
| 2025-12-16 | Orchestrator | Amended per user decision to require Arrow library |
