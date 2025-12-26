# ADR-0126: Entity-Type TTL Resolution Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-22
- **Deciders**: SDK Team
- **Related**: [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md), [TDD-CACHE-INTEGRATION](../design/TDD-CACHE-INTEGRATION.md), ADR-0021, ADR-0068

## Context

Different entity types in the Asana-as-database pattern have vastly different update frequencies:

| Entity Type | Update Frequency | Current TTL | Appropriate TTL |
|-------------|-----------------|-------------|-----------------|
| Business | Weekly | N/A (no cache) | 3600s (1 hour) |
| Contact | Daily | N/A | 900s (15 min) |
| Unit | Daily | N/A | 900s (15 min) |
| Offer | Hourly | N/A | 180s (3 min) |
| Process | Minutes | N/A | 60s (1 min) |
| Generic Task | Variable | 300s (default) | 300s (5 min) |

Using a single TTL for all entities means either:
- Long TTL (1 hour): Process entities serve stale data during state machine transitions
- Short TTL (1 minute): Business entities evicted unnecessarily, cache hit rate drops

**The key question**: How should we determine TTL when caching a task?

Forces at play:
- Entity type detection is already implemented (`detect_entity_type_from_dict`)
- TTL should be configurable (users may have different patterns)
- Default values should be sensible without configuration
- Detection failures should fall back gracefully
- Performance impact of detection must be minimal

## Decision

We will use **config-driven TTL with sensible defaults**, resolving TTL in this priority order:

```
Priority 1: Project-specific TTL (project_gid -> TTL)
    |
    v (if not configured)
Priority 2: Entity-type TTL (business/contact/etc -> TTL)
    |
    v (if entity type unknown or not configured)
Priority 3: Entry-type TTL (TASK/SUBTASKS/etc -> TTL)
    |
    v (if not configured)
Priority 4: Default TTL (300 seconds)
```

Implementation in `TTLSettings`:

```python
@dataclass
class TTLSettings:
    """TTL configuration with entity-type defaults."""

    default_ttl: int = 300  # 5 minutes
    project_ttls: dict[str, int] = field(default_factory=dict)
    entry_type_ttls: dict[str, int] = field(default_factory=dict)
    entity_type_ttls: dict[str, int] = field(default_factory=lambda: {
        "business": 3600,   # 1 hour - rarely changes
        "contact": 900,     # 15 min - low update frequency
        "unit": 900,        # 15 min - low update frequency
        "offer": 180,       # 3 min - pipeline movement
        "process": 60,      # 1 min - state machine transitions
    })

    def get_ttl(
        self,
        project_gid: str | None = None,
        entry_type: str | EntryType | None = None,
        entity_type: str | None = None,
    ) -> int:
        """Resolve TTL with priority: project > entity_type > entry_type > default."""
        # Priority 1: Project-specific
        if project_gid and project_gid in self.project_ttls:
            return self.project_ttls[project_gid]

        # Priority 2: Entity type (Business, Contact, etc.)
        if entity_type:
            entity_key = entity_type.lower()
            if entity_key in self.entity_type_ttls:
                return self.entity_type_ttls[entity_key]

        # Priority 3: Entry type (TASK, SUBTASKS)
        if entry_type:
            type_key = entry_type.value if isinstance(entry_type, EntryType) else entry_type
            if type_key in self.entry_type_ttls:
                return self.entry_type_ttls[type_key]

        # Priority 4: Default
        return self.default_ttl
```

Entity type detection at cache time:

```python
class TasksClient(BaseClient):
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

| Approach | Pros | Cons |
|----------|------|------|
| Hardcoded | Simple, no config needed | Users can't customize |
| **Config-driven** | Flexible, customizable | Slightly more complex |
| Entity class constants | Type-safe | Requires model changes |

**Config-driven** allows users to:
- Override defaults for their specific patterns
- Set per-project TTLs for high-velocity projects
- Disable entity-type TTLs if unwanted

### Why These Default Values?

| Entity | TTL | Rationale |
|--------|-----|-----------|
| Business | 3600s | Root entity, only metadata changes. Once a business is set up, it rarely changes. Longer TTL maximizes cache hits. |
| Contact | 900s | Contact information changes infrequently but should be reasonably fresh for communication purposes. |
| Unit | 900s | Similar to Contact - associated addresses and details change occasionally but not frequently. |
| Offer | 180s | Offers move through pipeline stages frequently (hourly). Short TTL prevents stale stage data. |
| Process | 60s | Process tasks are state machines with frequent transitions. Very short TTL ensures current state. |
| Default | 300s | Industry standard for API cache TTL. Balances freshness with performance. |

### Why Priority Order: Project > Entity > Entry > Default?

1. **Project-specific highest**: A high-velocity project may need 30s TTL regardless of entity type. Project context trumps type.

2. **Entity type second**: Business model entities have known update patterns. This is the most semantic level.

3. **Entry type third**: Different cache entry types (TASK vs SUBTASKS) may have different patterns.

4. **Default last**: Fallback when nothing else matches.

### Why Detect Entity Type at Cache Time?

Detection happens when storing, not when retrieving:

```python
# At cache store time
ttl = self._resolve_entity_ttl(data)  # Detect here
self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl)
```

Benefits:
- Detection runs once per cache miss
- TTL is stored with entry, no re-detection on hit
- Detection cost amortized over cache lifetime

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

Returning `None` means default TTL (300s) is used, which is acceptable.

### Why Include Project-Level TTL?

Some projects have special patterns:
- Archive projects: 24-hour TTL (data rarely changes)
- Active pipeline: 30-second TTL (constant updates)
- Template projects: 1-week TTL (never changes)

```python
config = CacheConfig(
    ttl=TTLSettings(
        project_ttls={
            "archive_project_gid": 86400,  # 24 hours
            "active_pipeline_gid": 30,      # 30 seconds
        }
    )
)
```

## Alternatives Considered

### Alternative 1: Hardcoded Entity Constants

- **Description**: Define TTL as class constant on entity models:
  ```python
  class Business(BaseBusinessEntity):
      CACHE_TTL = 3600

  class Process(BaseBusinessEntity):
      CACHE_TTL = 60
  ```
- **Pros**:
  - Type-safe, co-located with entity
  - Discoverable via IDE
  - No configuration needed
- **Cons**:
  - Requires model changes
  - Users cannot customize
  - Detection still needed to choose model
  - Circular dependency risk (models importing cache)
- **Why not chosen**: Users need ability to customize TTLs. Models should not depend on cache infrastructure.

### Alternative 2: Single Global TTL

- **Description**: Use same TTL for all cached entities:
  ```python
  DEFAULT_TTL = 300  # 5 minutes for everything
  ```
- **Pros**:
  - Simplest implementation
  - Predictable behavior
  - No detection needed
- **Cons**:
  - Suboptimal for all entity types
  - Process stale for 5 minutes (bad)
  - Business evicted every 5 minutes (wasteful)
- **Why not chosen**: Does not optimize cache for entity update patterns. Defeats purpose of entity-aware caching.

### Alternative 3: Detection via Custom Fields

- **Description**: Use presence of specific custom fields to determine entity type:
  ```python
  if "Pipeline Stage" in custom_fields:
      return "offer"  # 180s TTL
  ```
- **Pros**:
  - No detection module dependency
  - Works on raw dict data
- **Cons**:
  - Fragile (field names may change)
  - Incomplete (not all entities have unique fields)
  - Duplicates detection logic
- **Why not chosen**: Detection infrastructure already exists (`detect_entity_type_from_dict`). No need to duplicate.

### Alternative 4: User-Provided TTL Callback

- **Description**: Let users provide a function to determine TTL:
  ```python
  def my_ttl_resolver(data: dict) -> int:
      if data.get("name", "").startswith("BUS-"):
          return 3600
      return 300

  client = AsanaClient(cache_config=CacheConfig(ttl_resolver=my_ttl_resolver))
  ```
- **Pros**:
  - Maximum flexibility
  - User controls logic entirely
- **Cons**:
  - Complex API for common case
  - User must understand data structure
  - Error handling burden on user
- **Why not chosen**: Over-engineering. Config-driven with defaults covers 95% of cases. Power users can extend.

### Alternative 5: Modified-At Based TTL

- **Description**: Set TTL based on how recently the entity was modified:
  ```python
  age = now - modified_at
  if age > timedelta(days=7):
      ttl = 3600  # Old entity, long TTL
  else:
      ttl = 60    # Recently modified, short TTL
  ```
- **Pros**:
  - Adaptive to actual change patterns
  - No entity type detection needed
- **Cons**:
  - Doesn't account for entity semantics
  - A Business modified today still changes rarely
  - A Process not modified in a week may change soon
- **Why not chosen**: Entity type is a better predictor of future changes than recent modification time.

## Consequences

### Positive

- **Optimized cache hit rates**: Entity-appropriate TTLs reduce unnecessary evictions
- **Fresh data where needed**: Process entities update quickly
- **Configurable**: Users can customize for their patterns
- **Sensible defaults**: Works out-of-box for Asana-as-database pattern
- **Graceful degradation**: Detection failures use safe default

### Negative

- **Detection overhead**: ~0.1ms per cache miss for entity detection
- **Configuration complexity**: Multiple TTL levels may confuse users
- **Entity coupling**: Cache behavior tied to detection infrastructure

### Neutral

- **New configuration field**: `entity_type_ttls` added to TTLSettings
- **Documentation required**: TTL resolution rules must be documented
- **Test coverage**: More combinations to test

## Compliance

How do we ensure this decision is followed?

1. **Default values reviewed**: TTL defaults approved by product team
2. **Detection tested**: Unit tests for each entity type detection
3. **Priority order tested**: Tests verify resolution priority
4. **Documentation**: TTL configuration documented in user guide

## Implementation Checklist

- [ ] Add `entity_type_ttls` field to TTLSettings
- [ ] Update `get_ttl()` method with entity_type parameter
- [ ] Add `_resolve_entity_ttl` method to TasksClient
- [ ] Add `_detect_entity_type` helper method
- [ ] Unit tests for TTL resolution priority
- [ ] Integration test with entity type detection
- [ ] Document TTL configuration in README
