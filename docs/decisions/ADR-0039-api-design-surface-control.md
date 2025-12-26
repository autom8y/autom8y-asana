# ADR-0039: API Design & Surface Control

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: ADR-0012 (Public API Surface), ADR-0069 (Hydration API), ADR-0073 (Batch Resolution API), ADR-0128 (Field Normalization)
- **Related**: reference/API-INTEGRATION.md

## Context

The SDK needs clear boundaries between stable public APIs, power-user features, and internal implementation details. API design decisions affect:

1. **Discoverability**: Users should easily find the right methods
2. **Stability**: Public APIs need semantic versioning guarantees
3. **Flexibility**: Power users need access to advanced features
4. **Maintainability**: Internals must be refactorable without breaking users
5. **Type Safety**: Return types should be strongly typed and predictable

Python doesn't enforce API visibility at runtime, requiring conventions that guide users toward stable APIs while allowing refactoring freedom.

## Decision

### Three-Tier API Visibility Model

**Use explicit `__all__` exports and underscore prefixes to define API stability levels.**

#### Tier 1: Public API (Exported from Root)

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
    "CircuitBreakerConfig",

    # Exceptions
    "AsanaError",
    "RateLimitError",
    "ServerError",
    "SaveOrchestrationError",
    "GidValidationError",
    "PartialSaveError",

    # Protocols (for custom implementations)
    "AuthProvider",
    "CacheProvider",
    "LogProvider",

    # Models
    "Task",
    "Project",
    "User",
    "Business",
    "SaveSession",
    "SaveResult",
]
```

**Guarantee**: Semantic versioning applies. Breaking changes require major version bump.

#### Tier 2: Semi-Public API (Submodule Exports)

Accessible via submodule imports but not re-exported from root:

| Module | Exports | Stability |
|--------|---------|-----------|
| `autom8_asana.clients` | Individual client classes | Stable signatures, new methods may be added |
| `autom8_asana.models` | Individual model classes | Stable, new fields may be added |
| `autom8_asana.protocols` | Protocol definitions | Stable |
| `autom8_asana.transport` | `AsyncHTTPClient`, `sync_wrapper` | Subject to change in minor versions |
| `autom8_asana.models.business.resolution` | `resolve_units_async`, `resolve_offers_async` | Stable signatures |
| `autom8_asana.models.business.hydration` | `hydrate_from_gid_async` | Stable signatures |

**Example**:
```python
# Semi-public: works, but check changelog for changes
from autom8_asana.clients import TasksClient
from autom8_asana.models.business.resolution import resolve_units_async
```

#### Tier 3: Internal API (Underscore Prefix)

Modules prefixed with underscore are internal:

| Module | Contents | Why Internal |
|--------|----------|--------------|
| `autom8_asana._defaults/` | Default provider implementations | Implementation detail |
| `autom8_asana._internal/` | Concurrency utils, correlation IDs | Implementation detail |
| `autom8_asana._compat.py` | Deprecated import aliases | Migration-only |
| `autom8_asana.models.business._hydration_impl.py` | Hydration internals | Implementation detail |

**Guarantee**: None. May change or disappear in any release.

### Hydration API Design

**Provide multiple entry points: factory methods, instance methods, and generic function.**

#### Factory Method on Business (Primary API)

```python
class Business(BusinessEntity):
    @classmethod
    async def from_gid_async(
        cls,
        client: AsanaClient,
        gid: str,
        *,
        hydrate: bool = True,
    ) -> Business:
        """Load Business from GID with optional full hierarchy hydration.

        Args:
            client: AsanaClient for API calls
            gid: Business task GID
            hydrate: If True, load full hierarchy (default True)

        Returns:
            Fully hydrated Business (if hydrate=True) or Business-only
        """
```

#### Instance Methods on Leaf Entities (Navigation API)

```python
class Contact(BusinessEntity):
    async def to_business_async(
        self,
        client: AsanaClient,
        *,
        hydrate_full: bool = True,
    ) -> Business:
        """Navigate to containing Business and optionally hydrate full hierarchy.

        Args:
            client: AsanaClient for API calls
            hydrate_full: If True, hydrate full hierarchy after finding it

        Returns:
            Business instance (fully hydrated if hydrate_full=True)
        """

class Offer(BusinessEntity):
    async def to_business_async(self, client: AsanaClient, *, hydrate_full: bool = True) -> Business:
        """Navigate through Unit -> UnitHolder -> Business."""

class Unit(BusinessEntity):
    async def to_business_async(self, client: AsanaClient, *, hydrate_full: bool = True) -> Business:
        """Navigate through UnitHolder -> Business."""
```

#### Generic Hydration Function (Advanced API)

```python
# Located in: autom8_asana.models.business.hydration

async def hydrate_from_gid_async(
    client: AsanaClient,
    gid: str,
    *,
    hydrate_full: bool = True,
) -> HydrationResult:
    """Hydrate business hierarchy from any task GID.

    Universal entry point that:
    1. Fetches the task
    2. Detects its type
    3. Traverses upward to Business if needed
    4. Optionally hydrates full hierarchy downward

    Args:
        client: AsanaClient for API calls
        gid: Any task GID in business hierarchy
        hydrate_full: If True, hydrate full hierarchy after finding Business

    Returns:
        HydrationResult with business, entry_entity, and path information
    """
```

**API Location Summary**:

| Entry Point | Method | Returns | Use Case |
|-------------|--------|---------|----------|
| Business GID | `Business.from_gid_async(client, gid)` | `Business` | Known Business GID |
| Contact instance | `contact.to_business_async(client)` | `Business` | Navigate from Contact |
| Offer instance | `offer.to_business_async(client)` | `Business` | Navigate from Offer |
| Unit instance | `unit.to_business_async(client)` | `Business` | Navigate from Unit |
| Any GID | `hydrate_from_gid_async(client, gid)` | `HydrationResult` | Webhook with unknown type |

### Batch Resolution API Design

**Implement as module-level functions (not class methods or client methods).**

```python
# Module: autom8_asana.models.business.resolution

async def resolve_units_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Unit]]:
    """Batch resolve multiple AssetEdits to Units.

    Args:
        asset_edits: AssetEdits to resolve
        client: AsanaClient for API calls
        strategy: Resolution strategy (default AUTO)

    Returns:
        Dict mapping asset_edit.gid to ResolutionResult
    """

async def resolve_offers_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Offer]]:
    """Batch resolve multiple AssetEdits to Offers."""
```

**Usage**:
```python
from autom8_asana.models.business.resolution import resolve_units_async

results = await resolve_units_async(asset_edits, client)

for asset_edit in asset_edits:
    result = results[asset_edit.gid]
    if result.success:
        print(f"{asset_edit.name} -> {result.entity.name}")
```

**Return Type**: Dictionary mapping `asset_edit.gid` to `ResolutionResult`
- Every input AssetEdit has entry (even on failure)
- GID key enables O(1) lookup
- Matches patterns like `asyncio.gather()` results

### Field Normalization

**Single source of truth for field sets to prevent drift.**

```python
# Located in: autom8_asana.models.business.fields

STANDARD_TASK_OPT_FIELDS = [
    "name",
    "notes",
    "html_notes",
    "memberships",
    "memberships.section",
    "custom_fields",
    "custom_fields.enum_value",
    "dependencies",
    "dependents",
]

# All detection paths use this constant
# No duplication, no drift
```

**Benefits**:
- Single constant for all task fetches
- Eliminates class of bugs from field set drift
- Easy to update in one place
- Consistent across detection, hydration, and client operations

## Rationale

### Why Three-Tier Visibility?

**Tier 1 (Public)**: Exported from root
- Semantic versioning applies
- IDE autocomplete shows only these
- Documented in user guide

**Tier 2 (Semi-public)**: Submodule imports
- Stable signatures for power users
- Changes noted in changelog
- Advanced features without polluting root namespace

**Tier 3 (Internal)**: Underscore prefix
- Refactoring freedom
- No stability guarantees
- Python convention for "private"

### Why Multiple Hydration Entry Points?

Different use cases require different entry points:

1. **Known Business GID**: `Business.from_gid_async` - type-safe, simple
2. **Webhook with unknown GID**: `hydrate_from_gid_async` - generic, returns metadata
3. **Navigation from entity**: `contact.to_business_async` - ergonomic when entity exists

All delegate to shared implementation but provide appropriate return types and discoverability.

### Why Module Functions for Batch Resolution?

**No natural class home**: Batch resolution operates on collection, not single entity.

**Cleaner signature**: `resolve_units_async(asset_edits, client)` clearer than `AssetEdit.resolve_units_batch_async(asset_edits, client)`.

**Parallel to utilities**: Similar to `asyncio.gather()` being module function.

**Not a client method**: Entity-specific business logic, not general transport operation.

### Why Dict Return Type for Batch Operations?

1. **O(1) lookup**: Find result for specific AssetEdit without iteration
2. **Completeness**: Every input has entry (even failures)
3. **Composability**: Easy to merge, filter, iterate

### Why Single Field Constant?

**Problem**: Field sets duplicated across codebase led to drift and bugs.

**Solution**: Single `STANDARD_TASK_OPT_FIELDS` constant.

**Benefits**:
- Update in one place
- Consistent across all code paths
- Eliminates drift bugs
- Easy to verify completeness

## Alternatives Considered

### API Visibility Alternatives

#### Single Public Module (Flat Export)

- **Pros**: Simple imports, single `__all__`
- **Cons**: Large `__init__.py`, slow imports, overwhelming autocomplete
- **Why not chosen**: Too many names in root namespace

#### Runtime Import Guards

- **Pros**: Hard enforcement, fails fast
- **Cons**: Complex to implement, breaks legitimate use cases, not Pythonic
- **Why not chosen**: Python doesn't enforce visibility; convention preferred

### Hydration API Alternatives

#### Factory Methods Only

- **Pros**: Consistent entry points, clear type expectations
- **Cons**: Must know entity type before calling, awkward for webhooks
- **Why not chosen**: Doesn't support "unknown GID" use case

#### Single Unified Entry Point

- **Pros**: One API to learn, handles all cases
- **Cons**: Less discoverable, forces all through generic path, always returns `HydrationResult`
- **Why not chosen**: Over-generalization; simple cases become verbose

### Batch Resolution Alternatives

#### Class Method on AssetEdit

- **Pros**: Discoverable via class
- **Cons**: Awkward to call on class with instances as input, conflates instance and collection
- **Why not chosen**: Module function more natural for collections

#### Method on AssetEditHolder

- **Pros**: Natural home for holder's children
- **Cons**: Limits input to single holder's children, inflexible
- **Why not chosen**: Users may have cross-holder collections

#### Client Method

- **Pros**: Matches client pattern
- **Cons**: Requires new client attribute, mixes business model with transport
- **Why not chosen**: Resolution is business model logic

## Consequences

### Positive

**API Visibility**:
- Clear API contract for users
- Refactoring freedom for internals
- IDE autocomplete shows only public API from root
- Semantic versioning works correctly
- Documentation focuses on public API

**Hydration API**:
- Multiple entry points for different use cases
- Type-safe returns for common cases
- Metadata available for advanced scenarios
- Discoverable via class methods and instance methods

**Batch Resolution**:
- Clear module function API with explicit inputs
- Efficient shared lookups, concurrent fetches
- Flexible (works with any AssetEdit collection)
- Testable pure functions

**Field Normalization**:
- Single source of truth prevents drift
- Easy to update field sets
- Eliminates entire class of bugs

### Negative

**API Visibility**:
- Users may import internals anyway (Python doesn't prevent)
- Maintenance burden for `__all__` in all public modules
- Semi-public ambiguity (users may not understand tier 2)

**Hydration API**:
- Multiple APIs require more documentation
- Potential confusion about which to use

**Batch Resolution**:
- Import required from resolution module
- Less discoverable than entity or client methods
- New pattern (module functions for batch operations)

### Neutral

**API Visibility**:
- More `__init__.py` files needed
- Import depth varies by tier

**Hydration API**:
- Matches existing SDK patterns
- Return types explicit and strongly typed

**Batch Resolution**:
- Sync wrappers follow same pattern
- Documentation provides examples

## Compliance

### Enforcement

1. **API Visibility**:
   - [ ] `__all__` in every public module
   - [ ] CI check for missing `__all__`
   - [ ] Architecture tests verify no internal imports in public modules
   - [ ] Ruff configuration warns on private module imports

2. **Hydration API**:
   - [ ] Factory methods on `Business` class
   - [ ] Instance methods on `Contact`, `Offer`, `Unit`
   - [ ] Generic function in `hydration.py`
   - [ ] All methods async, accept `AsanaClient` as parameter
   - [ ] `HydrationResult` exported from `models.business`

3. **Batch Resolution**:
   - [ ] Module-level functions in `resolution.py`
   - [ ] Return type `dict[str, ResolutionResult[T]]`
   - [ ] Every input has entry in result dict
   - [ ] Optimize shared lookups
   - [ ] Exported from `models.business` package

4. **Field Normalization**:
   - [ ] Single `STANDARD_TASK_OPT_FIELDS` constant
   - [ ] All task fetches use constant (no duplication)
   - [ ] Constant in `models/business/fields.py`

### Testing

- Public API imported from root works
- Semi-public API imported from submodules works
- Internal modules have underscore prefix
- Hydration entry points return correct types
- Batch resolution optimizes API calls
- Field constant used consistently across codebase
