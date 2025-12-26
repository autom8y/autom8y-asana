# ADR-0005: Pydantic v2 with `extra="ignore"` for Forward Compatibility

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md), [TDD-0001](../design/TDD-0001-sdk-architecture.md), FR-SDK-039

## Context

The PRD requires Pydantic v2 for all models (FR-SDK-039). We need to configure Pydantic's behavior for handling Asana API responses, specifically:

1. **Extra fields**: Asana may add new fields to API responses. How should we handle unknown fields?
2. **Field validation**: How strict should validation be?
3. **Serialization**: How do we serialize models back to API format?

Pydantic v2 offers three `extra` configurations:
- `extra="forbid"`: Raise error on unknown fields
- `extra="ignore"`: Silently discard unknown fields
- `extra="allow"`: Store unknown fields in `__pydantic_extra__`

The Asana API:
- Regularly adds new fields to responses
- May return fields not documented in the API spec
- Uses `opt_fields` parameter to request specific fields
- Returns different fields based on permissions

## Decision

**Use Pydantic v2 with `extra="ignore"` as the default configuration for all models.**

```python
from pydantic import BaseModel, ConfigDict

class AsanaResource(BaseModel):
    """Base model for all Asana API resources."""

    model_config = ConfigDict(
        extra="ignore",           # Silently ignore unknown fields
        populate_by_name=True,    # Allow field aliases
        str_strip_whitespace=True, # Clean up string inputs
    )

    gid: str
    resource_type: str
```

### Configuration Details

| Setting | Value | Rationale |
|---------|-------|-----------|
| `extra` | `"ignore"` | Forward compatibility - new API fields don't break existing code |
| `populate_by_name` | `True` | Support both Python names and API names (e.g., `due_on` vs `dueOn`) |
| `str_strip_whitespace` | `True` | Normalize string inputs |
| `validate_assignment` | `False` (default) | Allow mutation without re-validation for performance |
| `frozen` | `False` (default) | Models are mutable (matches existing autom8 patterns) |

### Example Model

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class Task(AsanaResource):
    """Asana Task model."""

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    resource_type: str = "task"
    name: str
    notes: Optional[str] = None
    completed: bool = False
    due_on: Optional[str] = Field(None, alias="due_on")  # YYYY-MM-DD
    due_at: Optional[datetime] = None
    # ... known fields

    # Unknown fields from API (e.g., new fields Asana adds) are silently ignored
```

### API Interaction

```python
# Asana returns response with known and unknown fields
api_response = {
    "gid": "123",
    "resource_type": "task",
    "name": "My Task",
    "completed": False,
    "new_experimental_field": "some value",  # Unknown to our model
    "another_future_field": {"nested": "data"},  # Also unknown
}

# Model creation succeeds, unknown fields are ignored
task = Task.model_validate(api_response)

# task.new_experimental_field would raise AttributeError
# But model creation didn't fail
```

## Rationale

`extra="ignore"` provides the best balance for an API client library:

1. **Forward compatibility**: When Asana adds new fields, our SDK continues working. Users don't need to upgrade immediately.

2. **Graceful degradation**: Missing model fields just mean that feature isn't supported yet, not that the SDK is broken.

3. **Clean models**: We only expose fields we've explicitly modeled and tested. No surprise attributes.

4. **Upgrade path**: When we add new fields to models, existing code continues working.

5. **Production safety**: A minor API change from Asana won't cause production outages.

## Alternatives Considered

### `extra="forbid"` (Strict Mode)

- **Description**: Raise `ValidationError` if response contains unknown fields.
- **Pros**:
  - Immediately aware of API changes
  - Forces model updates to stay current
  - No silent data loss
- **Cons**:
  - **Breaking**: SDK breaks when Asana adds any new field
  - Users must upgrade SDK immediately after any API change
  - Production outages from benign API additions
  - Can't use SDK with newer API versions
- **Why not chosen**: Too fragile for a client library. API additions shouldn't break consumers.

### `extra="allow"` (Permissive Mode)

- **Description**: Store unknown fields in `__pydantic_extra__` dict.
- **Pros**:
  - No data loss
  - Can access unknown fields via `model.__pydantic_extra__["field"]`
  - Visibility into new API fields
- **Cons**:
  - Inconsistent access patterns (known vs unknown fields)
  - Extra memory for storing unknown data
  - Serialization becomes complex (do we include extras?)
  - Type safety lost for extra fields
  - May encourage using unofficial API fields
- **Why not chosen**: Mixed access patterns are confusing. If we need a field, we should model it explicitly.

### Field-Level `extra` Configuration

- **Description**: Use `extra="forbid"` on some models, `extra="ignore"` on others.
- **Pros**:
  - Fine-grained control
  - Strict where it matters
- **Cons**:
  - Inconsistent behavior across models
  - Harder to reason about
  - More configuration to maintain
- **Why not chosen**: Consistency is more valuable than fine-grained control here.

### Runtime Configuration

- **Description**: Let users configure `extra` behavior at runtime.
- **Pros**:
  - Maximum flexibility
  - Users can choose strict mode if desired
- **Cons**:
  - Complicates configuration
  - Different behavior in different contexts
  - Harder to test
  - Documentation complexity
- **Why not chosen**: Simplicity trumps flexibility. One well-chosen default is better than configuration.

## Consequences

### Positive
- **Resilient**: SDK survives API additions without code changes
- **Simple**: One behavior to understand and document
- **Safe**: Production systems don't break from new fields
- **Clean**: Models only expose explicitly defined fields

### Negative
- **Silent data loss**: Unknown fields are discarded (but we don't need them)
- **Delayed awareness**: May not notice new useful API fields immediately
- **Incomplete representation**: Model doesn't capture full API response

### Neutral
- **Explicit modeling**: Must add new fields to models to use them
- **Version awareness**: Should periodically review API changes and update models

## Compliance

To ensure this decision is followed:

1. **Base class enforcement**: All models inherit from `AsanaResource` which sets `extra="ignore"`
2. **Code review**: Check that models don't override to `extra="forbid"`
3. **Test coverage**: Tests verify models handle unknown fields gracefully
4. **API drift detection**: Periodic script compares our models to API responses, logs unknown fields
5. **Documentation**: Docstrings note that unknown fields are ignored
