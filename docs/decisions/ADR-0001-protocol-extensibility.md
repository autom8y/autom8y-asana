# ADR-0001: Protocol-Based Extensibility for Dependency Injection

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md), [TDD-0001](../design/TDD-0001-sdk-architecture.md)

## Context

The autom8_asana SDK must integrate with external systems (authentication, caching, logging) without coupling to specific implementations. The autom8 monolith uses:
- `ENV.SecretManager` for secrets/tokens
- `TaskCache` (S3-backed) for caching
- `LOG` for structured logging

New consumers (microservices, scripts) need different implementations:
- Environment variables for secrets
- In-memory or no caching
- Standard Python logging

We need a mechanism that:
1. Allows autom8 to inject its implementations
2. Provides sensible defaults for standalone use
3. Doesn't require inheritance or registration
4. Supports static type checking
5. Keeps the SDK decoupled from any specific implementation

Python offers several approaches for dependency injection:
- Abstract Base Classes (ABC)
- `typing.Protocol` (structural subtyping)
- Duck typing (no formal contracts)
- Dependency injection frameworks (e.g., `dependency-injector`)

## Decision

**Use `typing.Protocol` for all extensibility points.**

The SDK defines protocols for:
- `AuthProvider`: Secret/token retrieval
- `CacheProvider`: Get/set/delete caching operations
- `LogProvider`: Python logging-compatible interface

Any class that implements the protocol's methods is automatically compatible without explicit inheritance.

```python
from typing import Protocol

class AuthProvider(Protocol):
    """Protocol for authentication/secret retrieval."""

    def get_secret(self, key: str) -> str:
        """Retrieve a secret value by key.

        Args:
            key: Secret identifier (e.g., "ASANA_PAT")

        Returns:
            Secret value as string

        Raises:
            AuthenticationError: If secret not found
        """
        ...


class CacheProvider(Protocol):
    """Protocol for caching operations."""

    def get(self, key: str) -> dict | None:
        """Retrieve value from cache."""
        ...

    def set(self, key: str, value: dict, ttl: int | None = None) -> None:
        """Store value in cache."""
        ...

    def delete(self, key: str) -> None:
        """Remove value from cache."""
        ...


class LogProvider(Protocol):
    """Protocol for logging, compatible with Python logging.Logger."""

    def debug(self, msg: str, *args, **kwargs) -> None: ...
    def info(self, msg: str, *args, **kwargs) -> None: ...
    def warning(self, msg: str, *args, **kwargs) -> None: ...
    def error(self, msg: str, *args, **kwargs) -> None: ...
    def exception(self, msg: str, *args, **kwargs) -> None: ...
```

Usage in consuming code:

```python
# autom8 can inject without inheriting from Protocol
class Autom8AuthProvider:
    def get_secret(self, key: str) -> str:
        return ENV.SecretManager.get(key)

# SDK accepts it because it matches the Protocol structure
client = AsanaClient(auth_provider=Autom8AuthProvider())

# Python's logging.Logger already matches LogProvider
import logging
client = AsanaClient(log_provider=logging.getLogger("myapp"))
```

## Rationale

`typing.Protocol` provides structural subtyping (like Go interfaces or TypeScript interfaces), which:

1. **No inheritance required**: Existing classes (like `logging.Logger`) automatically satisfy protocols if they have matching methods. autom8's wrappers don't need to import SDK types.

2. **Static type checking**: mypy and other type checkers validate protocol compliance at check time, not runtime.

3. **Minimal coupling**: Consumers only need to implement the methods. They don't import or inherit from SDK classes.

4. **Explicit contracts**: Protocols document the expected interface clearly, unlike pure duck typing.

5. **Standard library**: `typing.Protocol` is in Python's standard library (3.8+), no external dependencies.

## Alternatives Considered

### Abstract Base Classes (ABC)

- **Description**: Define abstract classes with `@abstractmethod` decorators. Consumers inherit from them.
- **Pros**:
  - Built into Python
  - Runtime enforcement via `isinstance()` checks
  - Can include default method implementations
- **Cons**:
  - Requires explicit inheritance
  - autom8's classes would need to import and inherit from SDK types, creating coupling
  - `logging.Logger` couldn't be used directly
- **Why not chosen**: Inheritance creates coupling. Existing classes can't satisfy ABCs without modification.

### Duck Typing (No Formal Contract)

- **Description**: Accept any object and assume it has the right methods. Document expected interface in docstrings.
- **Pros**:
  - Maximum flexibility
  - No imports or inheritance needed
  - Pythonic
- **Cons**:
  - No static type checking
  - Errors only caught at runtime
  - Interface documentation easily drifts from reality
  - IDE autocomplete doesn't work
- **Why not chosen**: We want type safety and explicit contracts. Duck typing provides neither.

### Dependency Injection Framework (e.g., `dependency-injector`)

- **Description**: Use a DI framework to manage object creation and injection.
- **Pros**:
  - Powerful lifecycle management
  - Supports scopes, singletons, factories
  - Good for large applications
- **Cons**:
  - Additional dependency
  - Learning curve
  - Overkill for our three simple extension points
  - Consumers must adopt the framework
- **Why not chosen**: Too heavy for our simple needs. Three protocols don't justify a framework.

### Callback Functions

- **Description**: Accept functions instead of objects for simple operations.
- **Pros**:
  - Very simple
  - No classes needed
- **Cons**:
  - Doesn't work well for stateful operations (cache needs get/set/delete)
  - Less discoverable than protocol methods
  - Awkward for logging (multiple functions)
- **Why not chosen**: CacheProvider and LogProvider have multiple related methods that belong together.

## Consequences

### Positive
- **Zero coupling**: autom8 implements protocols without importing SDK types
- **Type safety**: mypy validates protocol compliance
- **stdlib compatibility**: `logging.Logger` works as-is for `LogProvider`
- **Testability**: Easy to create mock implementations for testing
- **Documentation**: Protocols serve as living interface documentation

### Negative
- **Runtime errors possible**: If someone passes an incompatible object, error occurs at call time, not instantiation
- **No default implementations in protocols**: We need separate default classes (but we want those anyway)
- **Requires Python 3.8+**: Not an issue given Python 3.10+ requirement

### Neutral
- **Three separate files**: We organize protocols into `protocols/auth.py`, `protocols/cache.py`, `protocols/log.py` for clarity
- **Default implementations shipped separately**: `_defaults/` package contains standalone implementations

## Compliance

To ensure this decision is followed:

1. **Code review checklist**: All extensibility points must use Protocol, not ABC
2. **Type checking in CI**: `mypy --strict` catches protocol violations
3. **Documentation**: README shows protocol usage pattern
4. **Architecture tests**: Verify no ABC imports in `protocols/` module
