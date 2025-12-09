# ADR-0019: Staleness Detection Algorithm

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team
- **Related**: [PRD-0002](../requirements/PRD-0002-intelligent-caching.md), [TDD-0008](../design/TDD-0008-intelligent-caching.md), [ADR-0018](ADR-0018-batch-modification-checking.md)

## Context

The intelligent caching layer must determine when cached data is stale (outdated) so it can be refreshed from the Asana API. Different use cases have different freshness requirements:

**Strict freshness scenarios**:
- Interactive task editing where user expects to see latest data
- Webhook handlers processing updates
- Critical business logic depending on current state

**Eventual freshness scenarios**:
- Dataframe generation for reporting (acceptable to be seconds behind)
- Bulk read operations where performance matters more than absolute freshness
- Background processing where slight staleness is acceptable

**Asana API provides**:
- `modified_at` field on tasks indicating last modification timestamp
- No ETag support for conditional requests
- No change notifications beyond webhooks

**Requirements**:
- FR-CACHE-005: Freshness parameter (`strict` vs `eventual`)
- FR-CACHE-010: `check_freshness()` method
- NFR-REL-004: Cache consistency (no stale reads in strict mode)

## Decision

**Use Arrow datetime comparison with a `Freshness` parameter to control staleness behavior.**

### Freshness Enum

```python
from enum import Enum


class Freshness(Enum):
    """Cache freshness modes."""
    STRICT = "strict"
    EVENTUAL = "eventual"
```

### Staleness Detection Algorithm

```python
from datetime import datetime
import arrow


def is_stale(
    cached_version: datetime,
    current_version: datetime,
) -> bool:
    """Compare cached version against current version.

    Uses Arrow for robust datetime comparison handling
    timezone-aware and naive datetimes.

    Args:
        cached_version: The modified_at stored in cache
        current_version: The modified_at from API

    Returns:
        True if cached version is older than current version
    """
    cached = arrow.get(cached_version)
    current = arrow.get(current_version)
    return current > cached


async def get_versioned(
    self,
    key: str,
    entry_type: EntryType,
    freshness: Freshness = Freshness.EVENTUAL,
) -> CacheEntry | None:
    """Retrieve versioned cache entry with freshness control.

    EVENTUAL mode:
    - Returns cached entry if exists and not TTL-expired
    - Does not validate against current API version
    - Fast: single cache read

    STRICT mode:
    - If cached entry exists, fetches current modified_at from API
    - Compares versions; returns cache only if versions match
    - Invalidates cache if stale
    - Slower: cache read + API call
    """
    entry = await self._get_from_redis(key, entry_type)

    if entry is None:
        return None

    if entry.is_expired():
        await self._delete_from_redis(key, entry_type)
        return None

    if freshness == Freshness.EVENTUAL:
        # Trust cache, don't validate
        return entry

    # STRICT mode: validate against API
    current_version = await self._fetch_modified_at(key)

    if current_version is None:
        # Task may have been deleted
        await self._delete_from_redis(key, entry_type)
        return None

    if is_stale(entry.version, current_version):
        # Cache is stale, invalidate and return None
        await self._delete_from_redis(key, entry_type)
        return None

    # Cache is fresh
    return entry
```

### Version Sources by Entry Type

| Entry Type | Version Source | Comparison Strategy |
|------------|----------------|---------------------|
| TASK | Task `modified_at` | Direct comparison |
| SUBTASKS | Parent task `modified_at` | Parent change invalidates |
| DEPENDENCIES | Task `modified_at` | Task change invalidates |
| DEPENDENTS | Task `modified_at` | Task change invalidates |
| STORIES | `last_story_at` (newest story) | New stories detected |
| ATTACHMENTS | Task `modified_at` | Task change invalidates |
| STRUC | Task `modified_at` | Task change invalidates |

### Arrow for Datetime Handling

Using [Arrow](https://arrow.readthedocs.io/) for datetime comparison because:
- Handles timezone-aware and naive datetimes correctly
- Parses ISO 8601 strings reliably
- Provides consistent comparison semantics
- Lightweight library with no large dependencies

```python
import arrow

# Handles various input formats
arrow.get("2025-12-09T10:30:00Z")
arrow.get("2025-12-09T10:30:00.000+00:00")
arrow.get(datetime.utcnow())

# Comparison works regardless of timezone representation
cached = arrow.get("2025-12-09T10:30:00Z")
current = arrow.get("2025-12-09T10:30:01+00:00")
assert current > cached  # Works correctly
```

## Rationale

**Why `modified_at` comparison?**

`modified_at` is the canonical indicator of task state in Asana:
- Updated on any task field change
- Available on all task responses
- Lightweight to fetch (single field via `opt_fields=modified_at`)
- Reliable across all Asana API endpoints

**Why Arrow over stdlib datetime?**

Python's `datetime` comparison has edge cases:
- Comparing naive vs. aware datetimes raises `TypeError`
- Timezone handling is error-prone
- ISO 8601 parsing requires `datetime.fromisoformat()` (Python 3.7+) with limitations

Arrow abstracts these issues:
- Auto-converts to comparable format
- Parses all ISO 8601 variants
- Minimal performance overhead

**Why two freshness modes?**

Different operations have different tolerance for staleness:

| Mode | Use Case | Latency | Accuracy |
|------|----------|---------|----------|
| EVENTUAL | Dataframes, bulk reads | Low (~2ms) | May be seconds stale |
| STRICT | Edits, critical paths | Higher (~50ms) | Always current |

A single mode would either waste API calls (always strict) or risk stale reads (always eventual).

## Alternatives Considered

### Alternative 1: TTL-Only Expiration

- **Description**: Rely solely on TTL for cache invalidation, no version comparison.
- **Pros**:
  - Simple implementation
  - No API calls for staleness check
  - Predictable cache behavior
- **Cons**:
  - No guarantee of freshness during TTL window
  - Long TTL = potentially stale data
  - Short TTL = frequent cache misses
  - Cannot support STRICT mode
- **Why not chosen**: Cannot meet NFR-REL-004 (no stale reads in strict mode).

### Alternative 2: ETag-Based Validation

- **Description**: Use HTTP ETags for cache validation with conditional requests.
- **Pros**:
  - Standard HTTP caching pattern
  - Server-side validation
  - Efficient 304 Not Modified responses
- **Cons**:
  - Asana API doesn't consistently support ETags
  - ETags vary by endpoint
  - Requires If-None-Match header handling
  - Not available for all resource types
- **Why not chosen**: Asana API doesn't provide reliable ETag support across all endpoints.

### Alternative 3: Polling-Based Background Refresh

- **Description**: Background worker periodically polls API and updates cache.
- **Pros**:
  - Cache always warm
  - Reads always fast (no inline checks)
  - Predictable refresh intervals
- **Cons**:
  - Wastes API quota on unchanged tasks
  - Complexity of background worker
  - Staleness during poll interval
  - Must know which tasks to poll
- **Why not chosen**: Too complex for SDK scope. Polling scheduler is consumer responsibility.

### Alternative 4: Webhook-Driven Invalidation

- **Description**: Use Asana webhooks to invalidate cache on changes.
- **Pros**:
  - Real-time invalidation
  - No polling overhead
  - Minimal API calls
- **Cons**:
  - Requires webhook infrastructure
  - Not all consumers have webhooks configured
  - Webhook delivery not guaranteed
  - SDK becomes dependent on webhook setup
- **Why not chosen**: Webhooks are optional consumer infrastructure. SDK cannot rely on them.

### Alternative 5: Content Hashing

- **Description**: Hash cache content and compare with hash of API response.
- **Pros**:
  - Detects any change, not just timestamp
  - Works even if `modified_at` is unreliable
- **Cons**:
  - Must fetch full content to compute hash
  - Defeats purpose of staleness check (still fetching everything)
  - Computationally expensive for large payloads
- **Why not chosen**: Requires fetching full data anyway, eliminating benefit of staleness check.

## Consequences

### Positive

- **Flexible freshness control**: Consumers choose strictness level per operation
- **Proven pattern**: Matches legacy autom8 behavior
- **Lightweight strict checks**: Only fetches `modified_at` field, not full payload
- **Robust datetime handling**: Arrow prevents timezone comparison bugs
- **Clear semantics**: EVENTUAL = fast, STRICT = accurate

### Negative

- **Arrow dependency**: Adds external library (minimal, ~2MB)
- **STRICT mode latency**: Adds ~50ms API call per cache read
- **Version source complexity**: Different entry types use different version fields
- **Eventual mode risk**: Consumers may get stale data if not aware

### Neutral

- **Default is EVENTUAL**: Consumers must opt into STRICT for guaranteed freshness
- **Batch checking uses same algorithm**: Consistent staleness detection
- **Stories use `last_story_at`**: Different version source, same comparison logic

## Compliance

To ensure this decision is followed:

1. **Code review checklist**:
   - Freshness parameter used appropriately per operation type
   - STRICT mode used for user-facing edits
   - Arrow used for all datetime comparisons

2. **Testing requirements**:
   - Unit tests for is_stale() with various datetime formats
   - Unit tests for timezone-aware vs. naive comparisons
   - Integration tests verifying STRICT mode API calls

3. **Documentation**:
   - README explains freshness modes with use case examples
   - Docstrings clarify which mode to use when
   - Warnings about eventual mode staleness potential
