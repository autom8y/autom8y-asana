# Code Conventions

> This document defines how we write code in this project. These are project-specific conventions layered on top of language standards.

## File Organization

```
/src
├── /api              # HTTP layer: routes, request/response models
├── /domain           # Business logic: entities, services, rules
├── /infrastructure   # External concerns: database, cache, external APIs
├── /shared           # Cross-cutting: types, utilities, constants
└── /tests
    ├── /unit         # Pure logic tests, no I/O
    ├── /integration  # Tests with real dependencies
    └── /fixtures     # Shared test data factories
```

## Naming Conventions

### Files
- Snake_case for Python: `user_service.py`
- Suffix by type: `_service.py`, `_repository.py`, `_model.py`, `_router.py`
- Test files mirror source: `user_service.py` -> `test_user_service.py`

### Code
| Element | Convention | Example |
|---------|------------|---------|
| Classes | PascalCase | `UserService` |
| Functions | snake_case | `get_user_by_id` |
| Constants | SCREAMING_SNAKE | `MAX_RETRY_COUNT` |
| Type aliases | PascalCase | `UserId = NewType("UserId", int)` |
| Private | Leading underscore | `_internal_helper` |

### Domain Terms
Use domain vocabulary consistently. For project-specific terminology, create a glossary only when you have terms Claude wouldn't know (business domain entities, product-specific concepts).

## Patterns We Use

### Dependency Injection
Dependencies are passed explicitly, never imported globally within functions.

```python
# Yes
class UserService:
    def __init__(self, repo: UserRepository, cache: CacheClient):
        self._repo = repo
        self._cache = cache

# No
class UserService:
    def get_user(self, id: int):
        from infrastructure.database import get_repo  # Hidden dependency
```

### Result Types for Fallible Operations
Use explicit result types instead of exceptions for expected failure modes.

```python
# Yes
async def get_user(id: UserId) -> User | NotFoundError:
    ...

# No (for expected cases)
async def get_user(id: UserId) -> User:
    raise UserNotFoundError(...)  # Exception for expected case
```

Exceptions are reserved for unexpected failures (bugs, infrastructure failures).

### Repository Pattern (When Used)
Repositories return domain entities, never ORM models.

```python
# Yes
class UserRepository(Protocol):
    async def get_by_id(self, id: UserId) -> User | None: ...

# No
class UserRepository:
    async def get_by_id(self, id: int) -> UserModel: ...  # ORM leak
```

### Configuration
All configuration via environment variables through a typed settings class.

```python
class Settings(BaseSettings):
    database_url: str
    redis_url: str
    debug: bool = False

    model_config = SettingsConfigDict(env_prefix="APP_")
```

## Patterns We Avoid

### Avoid
- Global mutable state
- Import-time side effects
- Circular imports (indicates poor module boundaries)
- `Any` type (escape hatch, not a pattern)
- Bare `except:` clauses
- String manipulation for structured data

### Prefer
- Explicit over implicit
- Composition over inheritance
- Small, focused functions
- Early returns over deep nesting
- Immutable data structures where practical

## Error Handling

### Hierarchy
```
ApplicationError (base)
├── ValidationError      # Bad input from client
├── NotFoundError        # Requested resource doesn't exist
├── ConflictError        # State conflict (duplicate, version mismatch)
├── AuthorizationError   # Permission denied
└── IntegrationError     # External service failure
```

### HTTP Mapping
| Error Type | HTTP Status |
|------------|-------------|
| ValidationError | 400 |
| AuthorizationError | 403 |
| NotFoundError | 404 |
| ConflictError | 409 |
| IntegrationError | 502 |
| Unhandled | 500 |

### Logging
- Log at boundaries (API entry, external calls)
- Include correlation ID in all logs
- Structured JSON format
- Don't log sensitive data (PII, secrets)

## Testing Conventions

### Naming
```python
def test_{function_name}_{scenario}_{expected_outcome}():
    # test_get_user_when_not_found_returns_none
```

### Structure (Arrange-Act-Assert)
```python
def test_create_user_with_valid_data_succeeds():
    # Arrange
    user_data = UserFactory.build()

    # Act
    result = service.create_user(user_data)

    # Assert
    assert result.id is not None
    assert result.email == user_data.email
```

### Factories Over Fixtures
Use factory functions for test data, not static fixtures.

```python
# Yes
user = UserFactory.build(email="test@example.com")

# No
user = FIXTURES["default_user"]  # Static, inflexible
```

## Import Order

```python
# 1. Standard library
import asyncio
from datetime import datetime

# 2. Third-party
from fastapi import APIRouter
from pydantic import BaseModel

# 3. Local - absolute imports
from src.domain.user import User
from src.infrastructure.database import Database
```

## Comments and Documentation

### Docstrings
Google style for all public functions:

```python
async def create_user(data: CreateUserRequest) -> User:
    """Create a new user account.

    Args:
        data: Validated user creation request.

    Returns:
        The created user with assigned ID.

    Raises:
        ConflictError: If email already exists.
    """
```

### Inline Comments
- Explain "why", not "what"
- If you need to explain "what", the code isn't clear enough
- Link to ADRs for non-obvious decisions: `# Per ADR-0042: ...`

## Terminology Guidance

### Anti-Glossary: Terms to Avoid

| Avoid Using | Use Instead | Reason |
|-------------|-------------|--------|
| "object" | Resource, DTO, Record, Model | Too vague |
| "data" | payload, record, metric, event | Too generic |
| "handler" (in SDK) | client or method | Handler reserved for entrypoints |
| "project" (ambiguous) | codebase project vs domain project | Clarify context |
| "update" | patch, sync, mutate, refresh | More accurate |
| "id" | uuid, external_id, resource_id | Remove ambiguity |
| "model" (generic) | domain model, ORM model, SDK resource | Disambiguate |
| "thing" | Entity, Resource, Record | Too ambiguous |
| "stuff" | items, records, resources | Too informal |
| "just" (as in "just run X") | Run X, Execute X | Minimizes complexity |
| "simply" (similar) | Perform Y | Patronizing tone |
| "obviously" | [omit] | Assumes shared context |
| "easily" / "trivially" | [omit or specify steps] | Subjective difficulty |

When writing documentation, prefer **specific, unambiguous terms** over vague placeholders.

### Field & Naming Conventions

| Concept | Convention | Notes |
|---------|------------|-------|
| Identifiers | `snake_case` with `_id` suffix | e.g., `business_id`, `external_id` |
| Enums | PascalCase or SCREAMING_SNAKE_CASE | e.g., `Vertical.Chiropractic` |
| Timestamps | UTC ISO-8601 | `2025-01-01T00:00:00Z` |
| Booleans | `is_`, `has_`, `should_` prefix | Improves clarity |
| Monetary fields | `_amount`, `_cents`, `_usd` | Avoid currency ambiguity |
| Lists | plural names | `offers`, `events`, `records` |
