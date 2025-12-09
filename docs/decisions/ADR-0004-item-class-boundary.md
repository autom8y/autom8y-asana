# ADR-0004: Minimal AsanaResource in SDK, Full Item Stays in Monolith

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md), [TDD-0001](../design/TDD-0001-sdk-architecture.md), FR-SDK-037, FR-SDK-038

## Context

The autom8 monolith has an `Item` class that serves as the base for all Asana resources. This class has evolved to include:

1. **Core Asana fields**: `gid`, `resource_type`, `name` (pure API data)
2. **Lazy loading**: Fetches additional data on attribute access
3. **Caching integration**: Uses `TaskCache` (S3-backed) for persistence
4. **Business model instantiation**: Creates domain objects (Offer, Business, Unit, etc.)
5. **Domain validation**: Validates data against business rules
6. **SQL integration**: Syncs with database tables

The PRD states:
- FR-SDK-037: SDK provides base model class for all Asana resources
- FR-SDK-038: SDK provides core Item class with lazy loading hooks only, no business logic
- Out of scope: Business-coupled parts of Item class stay in autom8

We must decide what "Item class with lazy loading hooks" means in practice.

## Decision

**The SDK provides a minimal `AsanaResource` base class. The full `Item` class with business logic remains in autom8.**

### SDK Provides: `AsanaResource`

```python
from pydantic import BaseModel, ConfigDict

class AsanaResource(BaseModel):
    """Base model for all Asana API resources.

    Provides common fields and serialization logic.
    Does NOT include:
    - Lazy loading implementation
    - Caching
    - Business domain logic
    - Database integration
    """
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    gid: str
    resource_type: str

    def to_api_dict(self) -> dict:
        """Serialize to Asana API format."""
        return self.model_dump(exclude_none=True, by_alias=True)

    @classmethod
    def from_api_response(cls, data: dict) -> "AsanaResource":
        """Create instance from Asana API response."""
        return cls.model_validate(data)
```

### SDK Provides: Lazy Loading Protocol (Optional Hook)

```python
from typing import Protocol, Any

class LazyLoader(Protocol):
    """Protocol for lazy loading additional resource data.

    Consumers can implement this to provide lazy loading behavior.
    The SDK does NOT provide an implementation.
    """

    def load_field(self, resource: AsanaResource, field_name: str) -> Any:
        """Load a field that wasn't included in the initial response.

        Args:
            resource: The resource needing additional data
            field_name: The field to load

        Returns:
            The loaded field value
        """
        ...
```

### autom8 Keeps: Full `Item` Class

```python
# In autom8 (NOT in SDK)
from autom8_asana.models import AsanaResource
from autom8_asana.protocols import LazyLoader

class Item(AsanaResource):
    """Full Asana resource with autom8 business logic.

    Extends SDK's AsanaResource with:
    - Lazy loading via TaskCache
    - Business model instantiation
    - Domain validation
    - SQL synchronization
    """

    _cache: TaskCache  # S3-backed cache
    _lazy_loader: LazyLoader

    def __getattr__(self, name: str):
        # Lazy load from cache or API
        if name in self._lazy_fields:
            return self._lazy_loader.load_field(self, name)
        raise AttributeError(name)

    def to_business_model(self):
        # Create domain object (Offer, Business, Unit, etc.)
        # This is pure business logic, stays in autom8
        ...
```

## Rationale

Clean separation is essential for the SDK to be reusable:

1. **SDK stays pure**: `AsanaResource` is just a Pydantic model with no dependencies on caching, SQL, or business logic.

2. **autom8 owns complexity**: The rich `Item` behavior is business-specific. Other consumers don't want or need it.

3. **Optional lazy loading**: The SDK provides a protocol for lazy loading, but no implementation. Consumers who want lazy loading implement it themselves.

4. **Inheritance works**: autom8's `Item` can inherit from SDK's `AsanaResource` and add its features.

5. **Zero coupling**: New microservices use `AsanaResource` directly without inheriting business logic.

## Alternatives Considered

### Move Full Item to SDK with Feature Flags

- **Description**: SDK includes the full `Item` class but with flags to enable/disable features (caching, business logic, etc.).
- **Pros**:
  - Single class definition
  - autom8 doesn't need to maintain Item
- **Cons**:
  - SDK would need CacheProvider for lazy loading (coupling)
  - Feature flags add complexity
  - Business model instantiation can't be generalized
  - SQL integration definitely can't be in SDK
  - Violates "zero imports from sql/, contente_api/, aws_api/"
- **Why not chosen**: Feature flags can't cleanly separate business logic. SDK would be polluted with autom8-specific code.

### SDK Provides Lazy Loading Implementation

- **Description**: SDK includes a generic lazy loading implementation using CacheProvider.
- **Pros**:
  - Reusable lazy loading for all consumers
  - autom8's TaskCache could plug in via CacheProvider
- **Cons**:
  - Lazy loading behavior is tightly coupled to autom8's caching strategy
  - Other consumers likely don't want the same lazy loading semantics
  - Adds complexity for simple use cases
  - What fields to lazy load is business-specific
- **Why not chosen**: Lazy loading strategy is application-specific. The SDK shouldn't prescribe it.

### No Base Class in SDK

- **Description**: SDK provides only specific models (Task, Project, etc.), no shared base.
- **Pros**:
  - Simpler SDK
  - Each model is self-contained
- **Cons**:
  - Duplicated code across models
  - No common serialization logic
  - autom8 can't easily extend a base class
  - Harder to add common functionality later
- **Why not chosen**: A base class provides valuable code reuse and extension point.

### Abstract Item Class with Required Implementation

- **Description**: SDK defines abstract `Item` that consumers must subclass to provide business logic.
- **Pros**:
  - Forces consumers to think about their Item implementation
  - Clear extension points
- **Cons**:
  - Over-engineering for simple use cases
  - New microservices just want to call API, not define Items
  - ABC creates inheritance coupling
- **Why not chosen**: Most consumers don't need Item semantics at all. They just want API results.

## Consequences

### Positive
- **Clean SDK**: `AsanaResource` is a simple Pydantic model
- **No coupling**: SDK has zero knowledge of caching, SQL, or business domains
- **Flexible extension**: autom8 extends `AsanaResource` however it wants
- **Simple default**: New consumers use `Task`, `Project` models directly
- **Protocol for hooks**: LazyLoader protocol allows optional integration

### Negative
- **Duplication**: autom8's `Item` duplicates some AsanaResource behavior
- **Migration work**: autom8 must maintain `Item` as a separate class extending AsanaResource
- **Two mental models**: Developers must understand both AsanaResource and Item

### Neutral
- **Clear boundary**: SDK boundary is explicit (AsanaResource is the contract)
- **Documentation**: Must explain that Item stays in autom8

## Compliance

To ensure this decision is followed:

1. **SDK import audit**: Verify `AsanaResource` has no imports from business modules
2. **Code review**: Block any business logic in SDK models
3. **Architecture diagram**: Show Item extending AsanaResource in autom8
4. **Test isolation**: SDK tests don't reference Item or business models
5. **Documentation**: README explains the SDK/Item boundary
