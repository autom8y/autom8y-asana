# ADR-0050: Entity-Aware TTL Management

## Metadata
- **Status**: Accepted
- **Author**: Tech Writer (consolidation)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: ADR-0126
- **Related**: reference/CACHE.md, ADR-0046 (Cache Protocol Extension), ADR-0048 (Staleness Detection)

## Context

Different entity types in the Asana-as-database pattern have vastly different update frequencies. Using a single TTL for all entities forces a suboptimal tradeoff:

| Entity Type | Update Frequency | Single TTL Impact |
|-------------|------------------|-------------------|
| Business | Weekly | 5min TTL: Evicted unnecessarily, cache hit rate drops |
| Contact | Daily | 5min TTL: Acceptable but could be longer |
| Unit | Daily | 5min TTL: Acceptable but could be longer |
| Offer | Hourly | 5min TTL: Acceptable |
| Process | Minutes | 5min TTL: Stale data during state transitions |
| Generic Task | Variable | 5min TTL: One-size-fits-none |

**The Problem**:
- Long TTL (1 hour): Process entities serve stale data during critical state machine transitions
- Short TTL (1 minute): Business entities evicted every minute despite changing weekly

Entity type detection already implemented (`detect_entity_type_from_dict`). Can we use semantic type to optimize TTL?

## Decision

**Use config-driven TTL with sensible defaults, resolving TTL in priority order: project-specific > entity-type > entry-type > default.**

### Priority Resolution Chain

```
Priority 1: Project-specific TTL (project_gid -> TTL)
    ↓ (if not configured)
Priority 2: Entity-type TTL (business/contact/etc -> TTL)
    ↓ (if entity type unknown or not configured)
Priority 3: Entry-type TTL (TASK/SUBTASKS/etc -> TTL)
    ↓ (if not configured)
Priority 4: Default TTL (300 seconds)
```

### Implementation

```python
@dataclass
class TTLSettings:
    """TTL configuration with entity-type defaults."""

    default_ttl: int = 300  # 5 minutes

    # Priority 1: Project-specific overrides
    project_ttls: dict[str, int] = field(default_factory=dict)

    # Priority 2: Entity type (Business, Contact, etc.)
    entity_type_ttls: dict[str, int] = field(default_factory=lambda: {
        "business": 3600,   # 1 hour - root entity, metadata only
        "contact": 900,     # 15 min - low update frequency
        "unit": 900,        # 15 min - low update frequency
        "offer": 180,       # 3 min - pipeline movement
        "process": 60,      # 1 min - state machine transitions
    })

    # Priority 3: Entry type (TASK, SUBTASKS)
    entry_type_ttls: dict[str, int] = field(default_factory=dict)

    def get_ttl(
        self,
        project_gid: str | None = None,
        entry_type: str | EntryType | None = None,
        entity_type: str | None = None,
    ) -> int:
        """Resolve TTL with priority chain."""
        # Priority 1: Project-specific
        if project_gid and project_gid in self.project_ttls:
            return self.project_ttls[project_gid]

        # Priority 2: Entity type
        if entity_type:
            entity_key = entity_type.lower()
            if entity_key in self.entity_type_ttls:
                return self.entity_type_ttls[entity_key]

        # Priority 3: Entry type
        if entry_type:
            type_key = entry_type.value if isinstance(entry_type, EntryType) else entry_type
            if type_key in self.entry_type_ttls:
                return self.entry_type_ttls[type_key]

        # Priority 4: Default
        return self.default_ttl
```

### Entity Type Detection at Cache Time

Detection happens when storing, not retrieving:

```python
class TasksClient(BaseClient):
    async def get_async(self, task_gid: str, ...) -> Task | dict[str, Any]:
        # Check cache first
        cached_entry = self._cache_get(task_gid, EntryType.TASK)
        if cached_entry is not None:
            return cached_entry.data

        # Cache miss: fetch from API
        data = await self._http.get(f"/tasks/{task_gid}", ...)

        # Detect entity type and resolve TTL
        ttl = self._resolve_entity_ttl(data)

        # Store with entity-appropriate TTL
        self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl)

        return data

    def _resolve_entity_ttl(self, data: dict[str, Any]) -> int:
        """Resolve TTL based on detected entity type."""
        entity_type = self._detect_entity_type(data)
        return self._config.cache.ttl.get_ttl(entity_type=entity_type)

    def _detect_entity_type(self, data: dict[str, Any]) -> str | None:
        """Detect entity type from task data."""
        try:
            from autom8_asana.models.business.detection import detect_entity_type_from_dict
            return detect_entity_type_from_dict(data)
        except (ImportError, Exception):
            return None  # Fall back to default TTL
```

## Rationale

### Why Config-Driven Over Hardcoded?

Config-driven allows users to:
- Override defaults for specific patterns
- Set per-project TTLs for high-velocity projects
- Disable entity-type TTLs if unwanted
- Adapt to changing business patterns without code changes

### Why These Default Values?

| Entity | TTL | Rationale |
|--------|-----|-----------|
| Business | 3600s (1h) | Root entity, only metadata changes. Once set up, rarely modified. Long TTL maximizes hits. |
| Contact | 900s (15m) | Contact info changes infrequently but should be reasonably fresh for communication. |
| Unit | 900s (15m) | Associated addresses/details change occasionally but not frequently. |
| Offer | 180s (3m) | Offers move through pipeline stages hourly. Short TTL prevents stale stage data. |
| Process | 60s (1m) | State machines with frequent transitions. Very short TTL ensures current state. |
| Default | 300s (5m) | Industry standard API cache TTL. Balances freshness with performance. |

Default values based on observed update patterns in production Asana-as-database deployments.

### Why Priority Order: Project > Entity > Entry > Default?

**Priority 1 (Project-specific)**: A high-velocity project may need 30s TTL regardless of entity type. Project context trumps semantic type.

**Priority 2 (Entity type)**: Business model entities have known update patterns. Most semantic level for general caching.

**Priority 3 (Entry type)**: Different cache entry types (TASK vs SUBTASKS vs STRUC) may have different volatility.

**Priority 4 (Default)**: Fallback when nothing else matches.

### Why Detect at Cache Store Time?

Detection runs once per cache miss:
- TTL stored with entry, no re-detection on hit
- Detection cost amortized over cache lifetime (300s-3600s)
- ~0.1ms detection overhead acceptable for cache miss path

Alternative (detect at retrieval): Would run detection on every cache hit, adding overhead to fast path.

### Why Graceful Fallback on Detection Failure?

```python
def _detect_entity_type(self, data: dict[str, Any]) -> str | None:
    try:
        return detect_entity_type_from_dict(data)
    except Exception:
        return None  # Use default TTL
```

Detection failures should not:
- Crash the application
- Prevent caching
- Log errors (too noisy)

Returning `None` means default TTL (300s) used, which is acceptable.

### Why Include Project-Level TTL?

Some projects have special patterns:
- Archive projects: 24-hour TTL (data rarely changes)
- Active pipeline: 30-second TTL (constant updates)
- Template projects: 1-week TTL (never changes)

```python
config = CacheConfig(
    ttl=TTLSettings(
        project_ttls={
            "1234567890": 86400,  # Archive project: 24 hours
            "9876543210": 30,     # Active pipeline: 30 seconds
        }
    )
)
```

## Alternatives Considered

### Alternative 1: Hardcoded Entity Constants
**Rejected**: Users cannot customize. Models should not depend on cache infrastructure. Circular dependency risk.

### Alternative 2: Single Global TTL
**Rejected**: Suboptimal for all entity types. Process stale for 5 minutes (bad). Business evicted every 5 minutes (wasteful).

### Alternative 3: Detection via Custom Fields
**Rejected**: Fragile (field names may change). Incomplete (not all entities have unique fields). Duplicates detection logic.

### Alternative 4: User-Provided TTL Callback
**Rejected**: Over-engineering. Complex API for common case. Error handling burden on user. Config-driven covers 95% of cases.

### Alternative 5: Modified-At Based TTL
**Rejected**: Doesn't account for entity semantics. A Business modified today still changes rarely. A Process not modified in a week may change soon.

## Consequences

### Positive
- Optimized cache hit rates per entity update patterns
- Fresh data where needed (Process: 1 min)
- Reduced evictions for stable data (Business: 1 hour)
- Configurable for project-specific patterns
- Sensible defaults work out-of-box
- Graceful degradation on detection failure

### Negative
- Detection overhead: ~0.1ms per cache miss
- Configuration complexity: Multiple TTL levels may confuse users
- Entity coupling: Cache behavior tied to detection infrastructure
- Documentation requirement: TTL resolution rules must be explained

### Neutral
- New configuration field: `entity_type_ttls` added to TTLSettings
- Test coverage: More combinations to test (4 priority levels)
- Monitoring: New metric dimensions for entity-type TTL distribution

## Impact

Production metrics with entity-aware TTLs:
- Business entity cache hit rate: 95% → 99%+ (longer TTL reduces evictions)
- Process entity staleness: 5min max → 1min max (fresher state machine data)
- Average TTL utilization: 300s → varies 60s-3600s (optimized per entity)

Combined with progressive TTL (ADR-0048), stable Business entities can reach 24h ceiling while Process entities stay fresh at 1min.

## Compliance

**Enforcement mechanisms**:
1. Code review: Verify TTL defaults approved by product team
2. Testing: Unit tests for each entity type detection, priority resolution
3. Documentation: TTL configuration documented in user guide
4. Monitoring: Metrics on TTL distribution by entity type

**Configuration**:
```python
@dataclass
class TTLSettings:
    default_ttl: int = 300

    # Entity-type defaults
    entity_type_ttls: dict[str, int] = field(default_factory=lambda: {
        "business": 3600,
        "contact": 900,
        "unit": 900,
        "offer": 180,
        "process": 60,
    })

    # Project-specific overrides
    project_ttls: dict[str, int] = field(default_factory=dict)

    # Entry-type overrides
    entry_type_ttls: dict[str, int] = field(default_factory=dict)
```
