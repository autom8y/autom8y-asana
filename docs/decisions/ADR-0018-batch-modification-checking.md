# ADR-0018: Batch Modification Checking

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team
- **Related**: [PRD-0002](../requirements/PRD-0002-intelligent-caching.md), [TDD-0008](../design/TDD-0008-intelligent-caching.md)

## Context

When processing multiple tasks (e.g., building a dataframe for a project with 1,000 tasks), the SDK needs to determine which cached entries are stale before fetching fresh data. Without optimization, this would require:

- 1,000 individual API calls to check `modified_at`, OR
- Fetching all 1,000 tasks regardless of cache status

Neither approach is acceptable:
- Individual checks: 1,000 API calls at ~200ms each = 200 seconds
- Full fetch: Ignores cache entirely, wastes API quota

**Legacy autom8 pattern**: The legacy TaskCache uses a batch modification checking pattern:
1. Batch API call fetches `modified_at` for up to 100 tasks in one request
2. Results cached in-memory for 25 seconds to prevent check spam
3. Only tasks with newer `modified_at` are re-fetched

This pattern reduces API calls by >90% when processing recently-cached data.

**Constraint**: Asana API `/batch` endpoint supports up to 100 sub-requests per call.

## Decision

**Implement batch modification checking with 25-second in-memory TTL, isolated per process.**

### Implementation

```python
from dataclasses import dataclass
from datetime import datetime
from threading import Lock


@dataclass
class StalenessResult:
    """Result of batch staleness check."""
    stale_gids: list[str]
    fresh_gids: list[str]
    check_count: int
    api_calls_made: int


class BatchModificationChecker:
    """Batch staleness checking with in-memory TTL.

    Prevents API spam by caching check results for 25 seconds.
    Results are per-process (not shared across ECS tasks/Lambda).
    """

    def __init__(
        self,
        http_client: AsyncHTTPClient,
        ttl: int = 25,  # seconds
    ) -> None:
        self._http = http_client
        self._ttl = ttl
        self._check_cache: dict[str, tuple[datetime, bool]] = {}
        self._lock = Lock()

    async def check_batch_staleness(
        self,
        gids: list[str],
        cached_versions: dict[str, datetime],
    ) -> StalenessResult:
        """Check staleness for multiple GIDs.

        Args:
            gids: Task GIDs to check
            cached_versions: Map of GID to cached modified_at

        Returns:
            StalenessResult with stale/fresh GID lists
        """
        # 1. Filter out recently-checked GIDs
        gids_to_check = [
            gid for gid in gids
            if not self._is_recently_checked(gid)
        ]

        if not gids_to_check:
            # All GIDs were checked recently
            return self._build_result_from_cache(gids, cached_versions)

        # 2. Chunk into batches of 100 (API limit)
        chunks = [
            gids_to_check[i:i + 100]
            for i in range(0, len(gids_to_check), 100)
        ]

        # 3. Execute batch API calls
        api_calls_made = 0
        current_versions: dict[str, datetime] = {}

        for chunk in chunks:
            versions = await self._fetch_modified_at_batch(chunk)
            current_versions.update(versions)
            api_calls_made += 1

        # 4. Compare versions and record results
        stale_gids = []
        fresh_gids = []

        for gid in gids:
            if gid in current_versions:
                current = current_versions[gid]
                cached = cached_versions.get(gid)
                is_fresh = cached is not None and cached >= current
                self._record_check(gid, is_fresh)
                if is_fresh:
                    fresh_gids.append(gid)
                else:
                    stale_gids.append(gid)
            elif gid in cached_versions:
                # Was in cache but not checked (recently checked)
                if self._get_cached_freshness(gid):
                    fresh_gids.append(gid)
                else:
                    stale_gids.append(gid)

        return StalenessResult(
            stale_gids=stale_gids,
            fresh_gids=fresh_gids,
            check_count=len(gids),
            api_calls_made=api_calls_made,
        )

    def _is_recently_checked(self, gid: str) -> bool:
        """Check if GID was checked within TTL window."""
        with self._lock:
            if gid not in self._check_cache:
                return False
            checked_at, _ = self._check_cache[gid]
            elapsed = (datetime.utcnow() - checked_at).total_seconds()
            if elapsed > self._ttl:
                del self._check_cache[gid]
                return False
            return True

    def _record_check(self, gid: str, is_fresh: bool) -> None:
        """Record check result in in-memory cache."""
        with self._lock:
            self._check_cache[gid] = (datetime.utcnow(), is_fresh)

    async def _fetch_modified_at_batch(
        self,
        gids: list[str],
    ) -> dict[str, datetime]:
        """Fetch modified_at for multiple tasks via batch API."""
        # Uses Asana batch API to get only modified_at field
        ...
```

### Key Design Points

1. **25-second TTL**: Matches legacy autom8 behavior. Sufficient to prevent spam during typical dataframe builds while remaining fresh enough for real-time scenarios.

2. **Per-process isolation**: The in-memory cache is not shared across processes (ECS tasks, Lambda invocations). This is intentional:
   - Avoids complexity of distributed cache for check results
   - Each process has its own "freshness window"
   - Redis is not used for check caching (adds network latency for very short-lived data)

3. **Thread-safe**: Uses `Lock` for concurrent access within a process.

4. **Chunking**: Automatically splits requests exceeding 100 GIDs into multiple API calls.

## Rationale

**Why 25 seconds?**

The 25-second TTL balances two concerns:
- **Too short (<10s)**: Re-checks happen too frequently during dataframe builds
- **Too long (>60s)**: Stale data served in real-time scenarios

25 seconds is the sweet spot based on legacy autom8 production data:
- Typical dataframe build for 500 tasks: ~20 seconds
- TTL covers the build, preventing re-checks
- Short enough that subsequent operations see fresh data

**Why in-memory vs. Redis?**

| Factor | In-Memory | Redis |
|--------|-----------|-------|
| Latency | ~0ms | ~2ms |
| Shared | No | Yes |
| Survives restart | No | Yes |
| Complexity | Low | Medium |

For check results that expire in 25 seconds:
- The data is too short-lived to benefit from Redis persistence
- The network latency of Redis (~2ms) is significant compared to in-memory (~0ms)
- Each process performing its own checks is acceptable; check results don't need sharing

**Why per-process isolation?**

ECS tasks and Lambda invocations have different request patterns:
- ECS task A processing project X shouldn't affect task B processing project Y
- Lambda invocations are ephemeral; shared check cache would require Redis
- Process isolation simplifies reasoning about cache behavior

## Alternatives Considered

### Alternative 1: Redis-Based Check Cache

- **Description**: Store check results in Redis with TTL, share across processes.
- **Pros**:
  - Shared efficiency: Process B benefits from Process A's checks
  - Survives process restarts
  - Consistent behavior across fleet
- **Cons**:
  - Adds Redis round-trip for every check lookup
  - Complex cache key management
  - Overkill for 25-second TTL data
  - Race conditions between check and cache write
- **Why not chosen**: Network latency overhead outweighs sharing benefits for such short-lived data.

### Alternative 2: No Caching of Check Results

- **Description**: Every batch operation performs fresh modification checks.
- **Pros**:
  - Always up-to-date staleness information
  - No cache management complexity
  - Simple implementation
- **Cons**:
  - Dataframe build with 1,000 tasks: 10 API calls per build
  - Multiple builds in quick succession: 10 calls each
  - Wastes API quota on repeated checks
- **Why not chosen**: Fails to optimize for the common case of repeated operations on same data.

### Alternative 3: Longer TTL (5 Minutes)

- **Description**: Cache check results for 5 minutes instead of 25 seconds.
- **Pros**:
  - Even fewer API calls
  - Better for long-running batch operations
- **Cons**:
  - Real-time scenarios see stale data
  - User expects ~30 second freshness for interactive use
  - Legacy pattern proven at 25 seconds
- **Why not chosen**: Too aggressive for expected use cases. 25 seconds is the proven sweet spot.

### Alternative 4: Check on Every Cache Read

- **Description**: Every `get_versioned()` with `freshness=STRICT` performs individual staleness check.
- **Pros**:
  - Guaranteed freshness
  - Simple mental model
- **Cons**:
  - 1,000 tasks = 1,000 API calls (no batching)
  - ~200 seconds for staleness checking alone
  - Completely defeats caching benefits
- **Why not chosen**: Performance is unacceptable. Batch checking is essential.

### Alternative 5: ETag-Based Validation

- **Description**: Use HTTP ETags for cache validation.
- **Pros**:
  - Standard HTTP caching pattern
  - Efficient conditional requests
- **Cons**:
  - Asana API doesn't consistently use ETags
  - ETags don't work across resource types
  - Still requires one request per resource
- **Why not chosen**: Asana API doesn't support ETag-based validation for all resources.

## Consequences

### Positive

- **Dramatic API reduction**: 1,000 tasks need ~10 API calls instead of 1,000
- **Fast dataframe builds**: Staleness check adds ~500ms instead of 200 seconds
- **Proven pattern**: Matches legacy autom8 behavior
- **Simple implementation**: No distributed state management
- **Configurable TTL**: Can tune via `CacheSettings.batch_check_ttl`

### Negative

- **Per-process isolation**: Different processes may have different freshness views
- **Memory usage**: Stores GID -> (timestamp, bool) per process
- **Lambda cold starts**: New invocations start with empty check cache
- **No persistence**: Checks lost on process restart

### Neutral

- **25-second default**: Configurable but matches legacy
- **Thread-safe locks**: Minor contention in highly concurrent scenarios
- **Chunking handled automatically**: Transparent to consumers

## Compliance

To ensure this decision is followed:

1. **Code review checklist**:
   - Batch operations use `BatchModificationChecker`
   - Individual staleness checks are avoided for batch scenarios
   - TTL is configurable via settings

2. **Testing requirements**:
   - Unit tests verify TTL expiration behavior
   - Unit tests verify chunking for >100 GIDs
   - Integration tests verify API call reduction

3. **Metrics**:
   - Track `batch_check_cache_hits` and `batch_check_cache_misses`
   - Track `api_calls_made` per staleness check
   - Alert if API calls per operation exceed expected threshold
