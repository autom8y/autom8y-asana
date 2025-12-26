# ADR-0069: Hydration API Design

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-HYDRATION, TDD-HYDRATION, ADR-0068, ADR-0052

## Context

The hydration feature needs a clean API for users to load complete business model hierarchies from any entry point. There are multiple design options for where this API should live and how it should be invoked.

**Questions from PRD (Q2, Q5)**:
- Should `hydrate_async()` be an instance method or factory function?
- Should the API be on entity methods, factory methods, or both?

### Use Cases

1. **From Business GID**: Load full hierarchy downward (most common)
2. **From Contact GID**: Navigate up to Business, then load full hierarchy
3. **From Offer GID**: Navigate up through Unit to Business, then load full hierarchy
4. **From any entity instance**: User already has an entity, wants to hydrate context

### Forces

1. **Discoverability**: Users should easily find hydration methods
2. **Type safety**: Return types should be strongly typed
3. **Consistency**: API should match existing SDK patterns
4. **Flexibility**: Support both GID-based and instance-based entry points
5. **Simplicity**: Don't over-engineer with too many entry points

## Decision

We will provide **both instance methods and factory methods** (Option B+C from Discovery).

### API Surface

#### 1. Factory Method on Business (Primary API)

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
            client: AsanaClient for API calls.
            gid: Business task GID.
            hydrate: If True, load full hierarchy. Default True.

        Returns:
            Fully hydrated Business (if hydrate=True) or Business-only.
        """
```

#### 2. Instance Methods on Leaf Entities (Navigation API)

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
            client: AsanaClient for API calls.
            hydrate_full: If True, hydrate full Business hierarchy after finding it.
                         If False, only populates the path traversed.

        Returns:
            Business instance (fully hydrated if hydrate_full=True).
        """

class Offer(BusinessEntity):
    async def to_business_async(
        self,
        client: AsanaClient,
        *,
        hydrate_full: bool = True,
    ) -> Business:
        """Navigate to containing Business through Unit -> UnitHolder -> Business."""

class Unit(BusinessEntity):
    async def to_business_async(
        self,
        client: AsanaClient,
        *,
        hydrate_full: bool = True,
    ) -> Business:
        """Navigate to containing Business through UnitHolder -> Business."""
```

#### 3. Generic Hydration Factory (Advanced API)

```python
# Located in: src/autom8_asana/models/business/hydration.py

async def hydrate_from_gid_async(
    client: AsanaClient,
    gid: str,
    *,
    hydrate_full: bool = True,
) -> HydrationResult:
    """Hydrate business hierarchy from any task GID.

    This is the universal entry point that:
    1. Fetches the task
    2. Detects its type (ADR-0068)
    3. Traverses upward to Business if needed
    4. Optionally hydrates full hierarchy downward

    Args:
        client: AsanaClient for API calls.
        gid: Any task GID in the business hierarchy.
        hydrate_full: If True, hydrate full hierarchy after finding Business.

    Returns:
        HydrationResult with business, entry_entity, and path information.
    """
```

### Return Type for Generic Hydration

```python
@dataclass
class HydrationResult:
    """Result of hydration operation.

    Attributes:
        business: The root Business entity (always populated).
        entry_entity: The entity at the entry GID (typed appropriately).
        entry_type: The detected type of the entry entity.
        path: List of entities traversed from entry to Business.
        api_calls: Number of API calls made during hydration.
        warnings: Any non-fatal issues encountered.
    """
    business: Business
    entry_entity: BusinessEntity
    entry_type: EntityType
    path: list[BusinessEntity]
    api_calls: int
    warnings: list[str]
```

### API Location Summary

| Entry Point | Method | Returns |
|-------------|--------|---------|
| Business GID | `Business.from_gid_async(client, gid)` | `Business` |
| Contact instance | `contact.to_business_async(client)` | `Business` |
| Offer instance | `offer.to_business_async(client)` | `Business` |
| Unit instance | `unit.to_business_async(client)` | `Business` |
| Any GID | `hydrate_from_gid_async(client, gid)` | `HydrationResult` |

## Rationale

**Why both instance and factory methods?**

- **Factory methods** are discoverable via class (`Business.from_gid_async`) and match existing SDK patterns
- **Instance methods** are ergonomic when user already has an entity (`contact.to_business_async`)
- Both patterns exist in the SDK already, users expect both

**Why `to_business_async` naming?**

- Clearly indicates direction (upward to Business)
- Distinguishes from `hydrate_async` which could be ambiguous
- Matches navigation semantics (`contact.to_business` vs `business.from_contact`)

**Why a generic `hydrate_from_gid_async`?**

- Webhook handlers receive GIDs of unknown type
- Avoids users needing to detect type themselves
- Returns rich metadata about the hydration operation

**Why return `HydrationResult` from generic entry?**

- User may need to know what type of entity they started with
- Path information useful for debugging
- API call count useful for performance monitoring
- Matches `SaveResult` pattern for consistency

## Alternatives Considered

### Option A: Factory Methods Only

- **Description**: Only `Business.from_gid_async()`, `Contact.from_gid_async()`, etc.
- **Pros**: Consistent entry points, clear type expectations
- **Cons**: Users must know entity type before calling; awkward for webhooks
- **Why not chosen**: Doesn't support "unknown GID" use case

### Option D: Single Unified Entry Point

- **Description**: Only `hydrate_from_gid_async()` for everything
- **Pros**: One API to learn, handles all cases
- **Cons**: Less discoverable, forces all users through generic path, return type always `HydrationResult`
- **Why not chosen**: Over-generalization; simple cases (Business GID) become verbose

### Option E: Extension Methods / Mixin

- **Description**: Add hydration capability via mixin class
- **Pros**: Separation of concerns
- **Cons**: Python doesn't have extension methods; mixins complicate inheritance
- **Why not chosen**: Doesn't fit Python idioms cleanly

## Consequences

### Positive

- **Multiple entry points**: Users can choose the API that fits their use case
- **Type safety**: Factory methods return typed entities, generic returns metadata
- **Discoverable**: Both `Business.from_gid_async` and `contact.to_business_async` are IDE-discoverable
- **Flexible**: `hydrate_full` parameter allows partial navigation when full hydration isn't needed

### Negative

- **Multiple APIs**: More documentation needed, potential confusion about which to use
- **Duplication**: Instance methods (`to_business_async`) share logic with factory

### Neutral

- API matches existing SDK patterns (`client.tasks.get_async`, `client.save_session`)
- Return types are explicit and strongly typed

## Compliance

- Factory methods MUST be implemented on `Business` class
- Instance methods MUST be implemented on `Contact`, `Offer`, `Unit` classes
- Generic hydration MUST be in dedicated module: `src/autom8_asana/models/business/hydration.py`
- All methods MUST accept `AsanaClient` as first positional argument
- All methods MUST be async (per SDK async-first pattern)
- `HydrationResult` MUST be exported from `autom8_asana.models.business`

## Implementation Notes

### Phase Mapping

| Phase | Session | Deliverable |
|-------|---------|-------------|
| P0 | 4 | `Business.from_gid_async()` with full downward hydration |
| P1 | 5 | `Contact.to_business_async()`, `Offer.to_business_async()` |
| P2 | 6 | `hydrate_from_gid_async()` generic entry point |

### Internal Implementation

All APIs delegate to shared implementation:

```python
# Internal module: src/autom8_asana/models/business/_hydration_impl.py

async def _hydrate_downward_async(business: Business, client: AsanaClient) -> None:
    """Populate all holders and their children recursively."""

async def _traverse_upward_async(
    entity: Task,
    client: AsanaClient,
) -> tuple[Business, list[BusinessEntity]]:
    """Walk parent chain to find Business, return Business and path."""
```
