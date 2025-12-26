# ADR-0029: Foundation Architecture

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0001, ADR-0003, ADR-0004, ADR-0012
- **Related**: TDD-0001 (SDK Architecture), PRD-0001 (SDK Extraction)

## Context

The autom8_asana system requires a clean architectural foundation that separates SDK infrastructure from business domain logic while maintaining extensibility. Three fundamental questions drive this architecture:

1. **How do we integrate with external systems** (auth, caching, logging) without coupling to specific implementations?
2. **How do we integrate with the Asana SDK** to gain async-first performance while maintaining API compatibility?
3. **Where is the boundary** between reusable SDK components and business-specific domain logic?

These decisions form the foundation upon which all other architectural choices build.

## Decision

We establish a **three-layer foundation architecture** using protocol-based extensibility, custom transport integration, and explicit entity boundaries.

### 1. Protocol-Based Extensibility

**Use `typing.Protocol` for all extensibility points.**

The SDK defines structural interfaces without requiring inheritance:

```python
from typing import Protocol

class AuthProvider(Protocol):
    """Protocol for authentication/secret retrieval."""
    def get_secret(self, key: str) -> str: ...

class CacheProvider(Protocol):
    """Protocol for caching operations."""
    def get(self, key: str) -> dict | None: ...
    def set(self, key: str, value: dict, ttl: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...

class LogProvider(Protocol):
    """Protocol for logging, compatible with Python logging.Logger."""
    def debug(self, msg: str, *args, **kwargs) -> None: ...
    def info(self, msg: str, *args, **kwargs) -> None: ...
    def warning(self, msg: str, *args, **kwargs) -> None: ...
    def error(self, msg: str, *args, **kwargs) -> None: ...
```

**Consumer integration**:
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

**Rationale**: Structural subtyping provides zero coupling. Existing classes like `logging.Logger` automatically satisfy protocols. Enables static type checking while maintaining independence.

### 2. SDK Integration Layer

**Replace Asana SDK's HTTP layer with httpx-based transport; retain type definitions and error parsing.**

**What we replaced**:
- HTTP request handling → custom `AsyncHTTPClient` with httpx
- Authentication → `AuthProvider` protocol injection
- Pagination → custom `PageIterator`
- Sync/async handling → async-first with sync wrappers

**What we kept**:
- Type definitions from `asana` package for API compatibility reference
- Error response parsing patterns
- API endpoint signatures

**Architecture**:
```python
# Import types from asana SDK for reference/compatibility
from asana.models import Task as AsanaTask  # For type reference only

# Define Pydantic models that are API-compatible
from autom8_asana.models import Task  # Our Pydantic model

# Our transport layer handles all HTTP
class AsyncHTTPClient:
    async def request(self, method: str, path: str, **kwargs) -> dict:
        # Use httpx for HTTP
        # Apply our rate limiting (1500 req/min token bucket)
        # Apply our retry logic (exponential backoff with jitter)
        # Apply our concurrency control (semaphores)
        ...
```

**Rationale**: Full control over transport enables async-first design, custom rate limiting at 1500 req/min, exponential backoff with jitter, and configurable connection pooling. Official SDK remains as dependency for type reference and API change tracking.

### 3. Entity Model Boundary

**SDK provides minimal `AsanaResource` base class; full `Item` stays in autom8 monolith.**

**SDK layer** (`AsanaResource`):
```python
from pydantic import BaseModel, ConfigDict

class AsanaResource(BaseModel):
    """Base model for all Asana API resources.

    Provides common fields and serialization logic.
    Does NOT include: lazy loading, caching, business logic, or database integration.
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

**Monolith layer** (`Item extends AsanaResource`):
```python
# In autom8 (NOT in SDK)
from autom8_asana.models import AsanaResource

class Item(AsanaResource):
    """Full Asana resource with autom8 business logic.

    Extends SDK's AsanaResource with:
    - Lazy loading via TaskCache
    - Business model instantiation (Offer, Business, Unit)
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
        ...
```

**Rationale**: Clean separation enables SDK reuse across microservices while autom8 owns domain complexity. New services use `AsanaResource` directly without inheriting business logic. Zero coupling between layers.

### 4. API Surface Definition

**Use explicit `__all__` exports and underscore prefixes for three-tier visibility model.**

**Tier 1 - Public API** (exported from root):
```python
# autom8_asana/__init__.py
__all__ = [
    # Main entry point
    "AsanaClient",

    # Configuration
    "AsanaConfig", "RateLimitConfig", "RetryConfig",

    # Exceptions
    "AsanaError", "AuthenticationError", "RateLimitError",

    # Protocols (for custom implementations)
    "AuthProvider", "CacheProvider", "LogProvider",

    # Core models
    "AsanaResource", "Task", "Project", "User",
]
```

**Guarantee**: Semantic versioning applies. Breaking changes require major version bump.

**Tier 2 - Semi-Public API** (submodule exports):
- `autom8_asana.clients` - Individual client classes
- `autom8_asana.models` - Individual model classes
- `autom8_asana.protocols` - Protocol definitions
- `autom8_asana.transport` - Transport utilities

**Stable signatures, new methods may be added in minor versions.**

**Tier 3 - Internal API** (underscore prefix):
- `autom8_asana._defaults/` - Default provider implementations
- `autom8_asana._internal/` - Internal utilities
- `autom8_asana._compat.py` - Deprecated import aliases

**No guarantees. May change or disappear in any release.**

**Rationale**: Clear public surface enables refactoring internals without version bumps. IDE autocomplete shows only stable APIs. Follows Python community conventions while maintaining explicit contracts.

## Consequences

### Positive

**Protocol-Based Extensibility**:
- Zero coupling between SDK and consumers
- Type safety via static analysis
- stdlib compatibility (`logging.Logger` works as-is)
- Easy mock implementations for testing

**SDK Integration**:
- Full async support with httpx
- Custom rate limiting at exactly 1500 req/min
- Exponential backoff with jitter for retries
- Connection pooling for efficiency
- Type reference for API compatibility checking

**Entity Boundary**:
- Clean SDK free of business logic
- Flexible extension for autom8 needs
- Simple default for new consumers
- Zero knowledge of caching, SQL, or business domains

**API Surface**:
- Clear public API contract
- Freedom to refactor internals
- IDE autocomplete shows only stable APIs
- Semantic versioning enforcement

### Negative

**Protocol-Based Extensibility**:
- Runtime errors possible if incompatible object passed
- No default implementations in protocols (separate classes needed)
- Requires Python 3.8+ (not an issue given 3.10+ requirement)

**SDK Integration**:
- More code to maintain (transport layer)
- Potential drift between models and Asana SDK types
- Dependency not fully utilized (include `asana` but don't use most of it)
- Duplicate type definitions

**Entity Boundary**:
- Duplication between `AsanaResource` and `Item`
- Migration work for autom8 to maintain separate `Item`
- Two mental models for developers

**API Surface**:
- Users may import internals anyway (Python doesn't prevent it)
- Maintenance burden for `__all__` in all public modules
- Semi-public ambiguity (users may not understand tier 2 stability)

### Neutral

**Protocol-Based Extensibility**:
- Three separate protocol files for organization
- Default implementations shipped separately in `_defaults/`

**SDK Integration**:
- Two type systems (Asana SDK classes + Pydantic models)
- Error hierarchy references Asana patterns but defines own exceptions

**Entity Boundary**:
- Clear boundary (AsanaResource is the contract)
- Documentation must explain SDK/Item separation

**API Surface**:
- Import depth varies (`from autom8_asana import X` vs `from autom8_asana.clients import Y`)
- More `__init__.py` files with explicit exports

## Implementation Notes

### Protocol Compliance Checking

```python
# Code review checklist
- All extensibility points use Protocol, not ABC
- No ABC imports in protocols/ module

# CI enforcement
- mypy --strict catches protocol violations
- Architecture tests verify protocol-only patterns
```

### SDK Integration Validation

```python
# Import auditing in CI
- Verify asana imports are only for types/errors
- No asana.Client usage
- httpx is the only HTTP library making requests

# Model comparison
- Periodic script to compare models against Asana SDK types
```

### Entity Boundary Enforcement

```python
# SDK import audit
- Verify AsanaResource has no imports from business modules
- Block any business logic in SDK models
- SDK tests don't reference Item or business models
```

### API Surface Protection

```python
# Architecture tests
def test_no_internal_imports_in_public_modules():
    """Verify public modules don't expose internal imports."""
    import ast
    for module in PUBLIC_MODULES:
        tree = ast.parse(open(module).read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("autom8_asana._")

# Ruff configuration
[tool.ruff]
select = ["PLC0415"]  # Warn on import of private modules
```

## Related Decisions

**Patterns**: See ADR-SUMMARY-PATTERNS for protocol definitions, descriptor patterns, and factory patterns that build on this foundation.

**Cache**: See ADR-0030 for cache infrastructure that uses CacheProvider protocol.

**Registry**: See ADR-0031 for entity registry and detection that builds on AsanaResource boundary.

**Business Domain**: See ADR-0032 for business entity patterns that extend AsanaResource.

## References

**Original ADRs**:
- ADR-0001: Protocol-Based Extensibility (2025-12-08)
- ADR-0003: Asana SDK Integration (2025-12-08)
- ADR-0004: Item Class Boundary (2025-12-08)
- ADR-0012: Public API Surface (2025-12-08)

**Technical Design**:
- TDD-0001: SDK Architecture
- TDD-0006: Backward Compatibility

**Requirements**:
- PRD-0001: SDK Extraction
- FR-SDK-001: Async-first design
- FR-SDK-006: Rate limiting at 1500 req/min
- FR-COMPAT-007: Official SDK as dependency
- FR-COMPAT-008: No internal implementation details in public API
