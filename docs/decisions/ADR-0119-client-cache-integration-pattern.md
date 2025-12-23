# ADR-0119: Client Cache Integration Pattern

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: Architect, Principal Engineer
- **Related**: TDD-CACHE-UTILIZATION, TDD-CACHE-INTEGRATION, ADR-0127 (Graceful Degradation)

---

## Context

The autom8_asana SDK has mature caching infrastructure (`CacheProvider`, `CacheEntry`, `EntryType`, `CacheMetrics`) and a working implementation in TasksClient. We need to extend cache support to ProjectsClient, SectionsClient, UsersClient, and CustomFieldsClient.

**Forces at play**:
- TasksClient has a working pattern that must be replicated consistently
- Different entity types have different versioning capabilities (`modified_at` availability varies)
- TTL requirements differ by entity volatility
- Code duplication risk if pattern is not well-defined
- Graceful degradation is already implemented in BaseClient helpers

**Key variation**: Asana's API returns `modified_at` for Tasks and Projects, but NOT for Sections, Users, or CustomFields. The pattern must handle both cases.

---

## Decision

We will use a **standardized cache integration pattern** for all SDK clients that:

1. **Validates GID** at method entry using `validate_gid()`
2. **Checks cache first** using `self._cache_get(gid, EntryType.X)`
3. **Returns cached data** on hit (respecting `raw` parameter)
4. **Fetches from API** on miss
5. **Stores in cache** using `self._cache_set(gid, data, EntryType.X, ttl=Y)`
6. **Returns response** (model or raw dict)

**Versioning strategy**:
- For entities with `modified_at` (Task, Project): Extract from API response
- For entities without `modified_at` (Section, User, CustomField): Use `datetime.now()`
- This is handled automatically by `_cache_set()` in BaseClient

**TTL configuration** (fixed per entity type):

| EntryType | TTL (seconds) | Rationale |
|-----------|---------------|-----------|
| TASK | Entity-type detected | Business/Contact/etc. have different TTLs |
| PROJECT | 900 (15 min) | Has `modified_at`; metadata changes infrequently |
| SECTION | 1800 (30 min) | No `modified_at`; sections rarely change |
| USER | 3600 (1 hour) | No timestamps; profiles extremely stable |
| CUSTOM_FIELD | 1800 (30 min) | Schema changes require admin action |

---

## Rationale

### Consistent Pattern Over Custom Logic

Each client could implement custom caching logic, but this would lead to:
- Inconsistent behavior across clients
- Harder testing (each client needs unique test coverage)
- Bug risk from subtle implementation differences

A standardized pattern ensures:
- Predictable behavior for SDK users
- Single test template for all clients
- Easier code review (deviation from pattern is a red flag)

### Versioning Falls Back Gracefully

BaseClient's `_cache_set()` already handles missing `modified_at`:

```python
# From BaseClient._cache_set()
modified_at = data.get("modified_at")
if modified_at:
    version = self._parse_modified_at(modified_at)
else:
    version = datetime.now(timezone.utc)
```

This means clients don't need special handling for versioning - they just call `_cache_set()` and the right thing happens.

### Fixed TTL vs. Configurable TTL

We chose **fixed TTL per entity type** rather than user-configurable for:
- Simplicity: No new configuration surface
- Consistency: All SDK users get the same behavior
- Appropriate defaults: TTLs are based on entity volatility analysis

Users who need different TTLs can:
1. Implement a custom CacheProvider with different behavior
2. Use cache invalidation APIs directly
3. Request configuration option in future release

---

## Alternatives Considered

### Alternative 1: Client-Specific Caching Logic

- **Description**: Each client implements its own caching strategy
- **Pros**: Maximum flexibility per entity type
- **Cons**:
  - Code duplication
  - Inconsistent behavior
  - Higher test burden
- **Why not chosen**: Pattern consistency outweighs flexibility benefits

### Alternative 2: Generic Caching Decorator

- **Description**: Create `@cached(entry_type=...)` decorator for get methods
- **Pros**: Zero duplication; single implementation
- **Cons**:
  - Decorator complexity with async methods
  - Hard to handle `raw` parameter variations
  - Obscures logic in method body
- **Why not chosen**: Explicit pattern is clearer than decorator magic

### Alternative 3: Configurable TTLs in CacheConfig

- **Description**: Add `entity_ttls: dict[EntryType, int]` to CacheConfig
- **Pros**: User control over TTLs
- **Cons**:
  - Configuration surface expansion
  - Users must understand entity volatility
  - Defaults are appropriate for 95% of cases
- **Why not chosen**: Deferred to future release if demand exists

### Alternative 4: Always Use Current Timestamp

- **Description**: Don't use `modified_at` even when available
- **Pros**: Simpler; uniform versioning
- **Cons**:
  - Loses staleness detection capability
  - Cache may return stale data when version comparison would detect it
- **Why not chosen**: `modified_at` provides better freshness guarantees when available

---

## Consequences

### Positive

- **Consistency**: All clients behave identically
- **Maintainability**: Single pattern to understand and test
- **Reliability**: Leverages proven BaseClient helpers
- **Simplicity**: No new abstractions or configuration

### Negative

- **Fixed TTLs**: Users cannot customize without custom provider
- **No skip-cache option**: Must call API directly to bypass cache
- **Code similarity**: Pattern repetition across clients (acceptable for clarity)

### Neutral

- **Test coverage**: Each client needs tests, but test structure is templated
- **Documentation**: Pattern must be documented for contributor onboarding

---

## Compliance

To ensure this decision is followed:

1. **Code review checklist**: Verify cache integration follows the 6-step pattern
2. **Test template**: All client cache tests should verify hit path, miss path, and TTL
3. **EntryType requirement**: New cacheable entities must add EntryType enum value
4. **TTL documentation**: Default TTLs must be documented in docstrings

**Pattern template for new clients**:

```python
@error_handler
async def get_async(
    self,
    {entity}_gid: str,
    *,
    raw: bool = False,
    opt_fields: list[str] | None = None,
) -> {Model} | dict[str, Any]:
    """Get a {entity} by GID with cache support."""
    from autom8_asana.cache.entry import EntryType
    from autom8_asana.persistence.validation import validate_gid

    validate_gid({entity}_gid, "{entity}_gid")

    cached_entry = self._cache_get({entity}_gid, EntryType.{ENTRY_TYPE})
    if cached_entry is not None:
        data = cached_entry.data
        if raw:
            return data
        return {Model}.model_validate(data)

    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/{entities}/{{{entity}_gid}}", params=params)

    self._cache_set({entity}_gid, data, EntryType.{ENTRY_TYPE}, ttl={TTL})

    if raw:
        return data
    return {Model}.model_validate(data)
```
