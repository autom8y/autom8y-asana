# ADR-0012: Public API Surface Definition

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md) (FR-COMPAT-008), [TDD-0006](../design/TDD-0006-backward-compatibility.md)

## Context

The autom8_asana SDK needs to clearly distinguish between:

1. **Public API**: Stable, documented, semantic versioning applies
2. **Semi-public API**: Available for power users, changes documented in changelog
3. **Internal API**: Implementation details, may change without notice

FR-COMPAT-008 requires: "SDK shall not expose internal implementation details in public API."

Python doesn't enforce API visibility at runtime, so we need conventions that:
- Guide users toward stable APIs
- Allow internal refactoring without breaking changes
- Support static analysis tools (IDE autocomplete, type checkers)
- Follow Python community conventions

## Decision

**Use a three-tier API visibility model with explicit `__all__` exports and underscore prefixes for internal modules.**

### Tier 1: Public API (Exported from Root)

Everything in `autom8_asana/__init__.py`'s `__all__` is public and stable:

```python
# autom8_asana/__init__.py
__all__ = [
    # Main entry point
    "AsanaClient",

    # Configuration
    "AsanaConfig",
    "RateLimitConfig",
    "RetryConfig",
    "ConcurrencyConfig",
    "TimeoutConfig",
    "ConnectionPoolConfig",

    # Exceptions
    "AsanaError",
    "AuthenticationError",
    "ForbiddenError",
    "NotFoundError",
    "GoneError",
    "RateLimitError",
    "ServerError",
    "TimeoutError",
    "ConfigurationError",
    "SyncInAsyncContextError",

    # Protocols (for custom implementations)
    "AuthProvider",
    "CacheProvider",
    "LogProvider",
    "ItemLoader",

    # Batch API
    "BatchClient",
    "BatchRequest",
    "BatchResult",
    "BatchSummary",

    # Models
    "AsanaResource",
    "NameGid",
    "PageIterator",
    "Task",
    "Project",
    "Section",
    "User",
    "Workspace",
    "CustomField",
    # ... all models
]
```

**Guarantee**: These names will not be removed or have breaking signature changes without a major version bump.

### Tier 2: Semi-Public API (Submodule Exports)

Accessible via submodule imports but not re-exported from root:

| Module | Exports | Stability |
|--------|---------|-----------|
| `autom8_asana.clients` | Individual client classes | Stable signatures, new methods may be added |
| `autom8_asana.models` | Individual model classes | Stable, new fields may be added |
| `autom8_asana.protocols` | Protocol definitions | Stable |
| `autom8_asana.transport` | `AsyncHTTPClient`, `sync_wrapper` | Subject to change in minor versions |

**Example**:
```python
# Semi-public: works, but check changelog for changes
from autom8_asana.clients import TasksClient
from autom8_asana.transport import sync_wrapper
```

### Tier 3: Internal API (Underscore Prefix)

Modules prefixed with underscore are internal:

| Module | Contents | Why Internal |
|--------|----------|--------------|
| `autom8_asana._defaults/` | Default provider implementations | Implementation detail |
| `autom8_asana._internal/` | Concurrency utils, correlation IDs | Implementation detail |
| `autom8_asana._compat.py` | Deprecated import aliases | Migration-only, will be removed |

**Guarantee**: None. These may change or disappear in any release.

**Example**:
```python
# DO NOT DO THIS - internal modules may change
from autom8_asana._defaults import NullCacheProvider  # Bad!

# Instead, use defaults through AsanaClient construction
client = AsanaClient()  # Uses NullCacheProvider internally
```

### Enforcement Mechanisms

1. **`__all__` on all public modules**: Defines exactly what's exported
2. **Underscore prefix for internal modules**: `_defaults/`, `_internal/`, `_compat.py`
3. **IDE support via `TYPE_CHECKING` blocks**: Static analysis sees correct types
4. **Documentation**: Public API documented, internal API not
5. **Architecture tests**: CI verifies no internal imports in public modules

## Rationale

This approach balances discoverability with stability:

1. **Clear Public API**: Users import from root package, autocomplete shows only stable names

2. **Underscore Convention**: Python's standard way to indicate "private". Linters like ruff can warn on underscore imports.

3. **`__all__` Enforcement**: Controls `from module import *` and IDE autocomplete. Makes public surface explicit.

4. **Three Tiers**: Allows power users to access internals if needed while signaling stability expectations.

5. **Semantic Versioning Compatibility**: Public API changes require major version bump; semi-public changes require minor version mention in changelog.

## Alternatives Considered

### Single Public Module (Flat Export)

- **Description**: Export everything from root, no submodules
- **Pros**:
  - Simple imports (`from autom8_asana import everything`)
  - Single `__all__` to maintain
- **Cons**:
  - Large `__init__.py` with all imports (slow)
  - No organization for related functionality
  - Autocomplete becomes overwhelming
- **Why not chosen**: Too many names in root namespace; clients and models naturally group

### Private Package Prefix (`_autom8_asana_internal`)

- **Description**: Separate package for internal code
- **Pros**:
  - Completely separate namespace
  - Can have independent versioning
- **Cons**:
  - Awkward package structure
  - More complex build configuration
  - Users might still import it
- **Why not chosen**: Overkill; underscore prefix on modules is sufficient

### Runtime Import Guards

- **Description**: Raise `ImportError` when importing internal modules from outside package
- **Pros**:
  - Hard enforcement
  - Fails fast
- **Cons**:
  - Complex to implement correctly
  - Can break legitimate use cases (testing, debugging)
  - Python philosophy is "we're all adults here"
- **Why not chosen**: Python doesn't enforce visibility; convention is preferred

### No Internal Distinction

- **Description**: Everything is public, use semantic versioning for all changes
- **Pros**:
  - Simple
  - No "private" confusion
- **Cons**:
  - Can't refactor internals without version bump
  - All implementation details become API
  - Difficult to maintain
- **Why not chosen**: Unsustainable; need freedom to refactor internals

## Consequences

### Positive

- **Clear API contract**: Users know what's stable
- **Refactoring freedom**: Internals can change without breaking users
- **IDE support**: Autocomplete shows only public API from root import
- **Semantic versioning works**: Public API = semver surface
- **Documentation focus**: Only document public API

### Negative

- **Users may import internals anyway**: Python doesn't prevent it
- **Maintenance burden**: Must maintain `__all__` in all public modules
- **Semi-public ambiguity**: Users may not understand tier 2 stability

### Neutral

- **More `__init__.py` files**: Each public submodule needs explicit exports
- **Import depth varies**: `from autom8_asana import X` vs `from autom8_asana.clients import Y`

## Compliance

To ensure this decision is followed:

1. **`__all__` in every public module**: CI check for missing `__all__`

2. **Architecture tests**:
   ```python
   def test_no_internal_imports_in_public_modules():
       """Verify public modules don't expose internal imports."""
       import ast
       for module in PUBLIC_MODULES:
           tree = ast.parse(open(module).read())
           for node in ast.walk(tree):
               if isinstance(node, ast.Import):
                   for alias in node.names:
                       assert not alias.name.startswith("autom8_asana._")
   ```

3. **Ruff configuration**:
   ```toml
   [tool.ruff]
   # Warn on import of private modules
   select = ["PLC0415"]  # import-outside-toplevel for private access
   ```

4. **Documentation**: Public API has docstrings and user guide; internal has no external docs

5. **Code review**: New public exports require discussion; internal changes don't
