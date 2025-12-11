# ADR-0032: Cache Granularity

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team
- **Related**: [PRD-0003](../requirements/PRD-0003-structured-dataframe-layer.md) (FR-CACHE-001), [TDD-0008](../design/TDD-0008-intelligent-caching.md), [TDD-0009](../design/TDD-0009-structured-dataframe-layer.md), [ADR-0021](ADR-0021-dataframe-caching-strategy.md)

## Context

The Structured Dataframe Layer extracts task data into typed rows. These extracted rows can be cached to avoid re-extraction on subsequent requests. The question is: at what granularity should this cache operate?

### Cache Granularity Options

| Granularity | Key Structure | Cached Unit |
|-------------|---------------|-------------|
| Per-project | `asana:struc:project:{project_gid}` | Entire DataFrame |
| Per-section | `asana:struc:section:{section_gid}` | Section DataFrame |
| Per-task (no context) | `asana:struc:task:{task_gid}` | Single row |
| Per-task (with project) | `asana:struc:{task_gid}:{project_gid}` | Single row with context |

### Why Project Context Matters

A task's extracted row may vary by project context:

1. **Section membership**: A task belongs to a section within a specific project. Multi-homed tasks appear in different sections in different projects.

2. **Project-specific custom fields**: Custom fields may be project-specific. The same task in different projects may have different custom fields visible.

3. **Derived fields**: Fields like `max_pipeline_stage` may be computed relative to the project context.

```python
# Same task, different projects, different section
task_gid = "123456789"

# In Project A:
row_a = {"section": "Active", "project_gid": "A", ...}

# In Project B (multi-homed):
row_b = {"section": "Pipeline", "project_gid": "B", ...}
```

### TDD-0008 Integration

TDD-0008 defines the STRUC entry type with key format:

```
asana:struc:{task_gid}:{project_gid} -> JSON (computed structural data)
```

This decision documents why this granularity was chosen.

### Forces at Play

| Force | Pull Toward |
|-------|-------------|
| Cache hit rate | Fine-grained (per-task) |
| Invalidation precision | Fine-grained (per-task) |
| Storage efficiency | Coarse-grained (per-project) |
| Project context sensitivity | Per-task with project |
| Cross-project reuse | Per-task without context |
| Simplicity | Per-project (one entry) |
| Legacy pattern alignment | Per-task with project |

## Decision

**Cache extracted rows at per-task granularity with project context: `{task_gid}:{project_gid}`.**

### Key Structure

```
asana:struc:{task_gid}:{project_gid}

Examples:
asana:struc:1234567890:9876543210  -> {"gid": "1234567890", "section": "Active", ...}
asana:struc:1234567890:5555555555  -> {"gid": "1234567890", "section": "Pipeline", ...}
```

### Cache Entry Structure

```python
CacheEntry(
    key="1234567890:9876543210",
    data={
        "gid": "1234567890",
        "name": "Task Name",
        "section": "Active",
        "type": "Unit",
        "mrr": "5000.00",
        # ... all extracted fields
    },
    entry_type=EntryType.STRUC,
    version=datetime(2025, 1, 15, 10, 30, 0),  # task.modified_at
    cached_at=datetime.utcnow(),
    ttl=300,  # 5 minutes default
    metadata={
        "schema_version": "1.0.0",
        "project_gid": "9876543210",
    }
)
```

### Implementation

```python
class DataFrameCacheIntegration:
    def __init__(self, cache_provider: CacheProvider, schema_version: str):
        self._cache = cache_provider
        self._schema_version = schema_version

    def get_cached_row(
        self,
        task_gid: str,
        project_gid: str,
    ) -> TaskRow | None:
        """Retrieve cached row for task in project context."""
        key = f"{task_gid}:{project_gid}"
        entry = self._cache.get_versioned(key, EntryType.STRUC)

        if entry is None:
            return None

        # Validate schema compatibility
        if entry.metadata.get("schema_version") != self._schema_version:
            return None  # Schema mismatch; re-extract

        return self._deserialize_row(entry.data)

    def cache_row(
        self,
        task_gid: str,
        project_gid: str,
        row: TaskRow,
        version: datetime,
    ) -> None:
        """Cache extracted row with project context."""
        key = f"{task_gid}:{project_gid}"
        entry = CacheEntry(
            data=row.to_dict(),
            entry_type=EntryType.STRUC,
            version=version,
            cached_at=datetime.utcnow(),
            metadata={
                "schema_version": self._schema_version,
                "project_gid": project_gid,
            },
        )
        self._cache.set_versioned(key, entry)

    def get_batch(
        self,
        task_gids: list[str],
        project_gid: str,
    ) -> dict[str, TaskRow | None]:
        """Batch retrieve cached rows for efficiency."""
        keys = [f"{gid}:{project_gid}" for gid in task_gids]
        entries = self._cache.get_batch(keys, EntryType.STRUC)

        return {
            gid: self._deserialize_row(e.data) if e else None
            for gid, e in zip(task_gids, entries.values())
        }
```

## Rationale

### Why Per-Task Granularity?

**1. Precise invalidation**: When a task is modified, only that task's cache entry is invalidated. Project-level caching would invalidate all tasks on any task change.

```python
# Per-task: Surgical invalidation
cache.invalidate(f"{modified_task_gid}:{project_gid}")

# Per-project: Overkill invalidation
cache.invalidate(f"project:{project_gid}")  # All 1000 tasks re-extracted
```

**2. Higher hit rate**: Individual tasks change less frequently than entire projects. Per-task caching maximizes the probability of a cache hit.

| Scenario | Per-Project | Per-Task |
|----------|-------------|----------|
| 1000 tasks, 1 modified | 0% hit | 99.9% hit |
| 1000 tasks, 10 modified | 0% hit | 99% hit |
| 1000 tasks, 0 modified | 100% hit | 100% hit |

**3. Memory efficiency**: Only active tasks are cached. Per-project caching would cache entire DataFrames even if only a subset is accessed.

**4. Reuse across requests**: A cached task row can serve multiple DataFrame requests that include that task.

### Why Include Project Context?

**1. Section membership varies by project**: A multi-homed task has different section membership in each project. The `section` field in the extracted row depends on project context.

```python
# Task 123 in Project A (section: "Active")
row_a = extract(task_123, project_a)
assert row_a.section == "Active"

# Task 123 in Project B (section: "Pipeline")
row_b = extract(task_123, project_b)
assert row_b.section == "Pipeline"
```

**2. Custom field visibility**: Projects can have different custom field settings. A custom field visible in Project A may not be visible in Project B.

**3. Derived fields**: Some fields are computed relative to project context. For example, `max_pipeline_stage` might be computed from the project's pipeline configuration.

**4. Matches legacy pattern**: The legacy `struc()` method caches with project context (S3 key includes project).

### Why Not Pure Task (No Project Context)?

Without project context, the cache would return incorrect data for multi-homed tasks:

```python
# WRONG: Pure task caching
cache.set("task:123", {"section": "Active", ...})  # From Project A

# Later, in Project B:
row = cache.get("task:123")  # Returns "Active" section
# WRONG! Task is in "Pipeline" section in Project B
```

This would produce silent data corruption.

## Alternatives Considered

### Alternative 1: Per-Project Caching

- **Description**: Cache entire DataFrame per project.
- **Pros**:
  - Fewer cache entries (1 per project vs N per task)
  - Simpler key structure
  - Single read retrieves all data
- **Cons**:
  - Any task change invalidates entire project cache
  - Poor hit rate when tasks frequently change
  - Memory waste if only subset of tasks accessed
  - Large cache values (entire DataFrame serialized)
- **Why not chosen**: Hit rate and invalidation precision are unacceptable for projects with frequent task updates.

### Alternative 2: Per-Section Caching

- **Description**: Cache DataFrame per section within project.
- **Pros**:
  - Smaller invalidation scope than per-project
  - Fewer entries than per-task
  - Natural grouping for section-based access
- **Cons**:
  - Task moves between sections invalidate both
  - Still coarse-grained for task modifications
  - Doesn't solve multi-homed task problem
  - Section GIDs less stable than task GIDs
- **Why not chosen**: Task-level changes still cause section-level invalidation. Not a significant improvement over per-project.

### Alternative 3: Per-Task Without Project Context

- **Description**: Cache row per task without project GID in key.
- **Pros**:
  - Maximum reuse (same task serves all projects)
  - Simplest key structure
  - Fewest cache entries
- **Cons**:
  - Section field would be incorrect for multi-homed tasks
  - Project-specific custom fields not handled
  - Derived fields computed without context
  - Silent data corruption for multi-homed tasks
- **Why not chosen**: Data correctness requires project context. Silent corruption is unacceptable.

### Alternative 4: Composite Key with Field Hashing

- **Description**: Include hash of context-sensitive fields in key.
- **Pros**:
  - Maximum cache sharing where context is identical
  - Correct data when contexts differ
- **Cons**:
  - Complex key generation
  - Must identify which fields are context-sensitive
  - Hash collision risk
  - Hard to explain and debug
- **Why not chosen**: Complexity not justified. Per-task with project is simple and correct.

### Alternative 5: No Caching (Extract Every Time)

- **Description**: Don't cache extracted rows; always re-extract from task data.
- **Pros**:
  - Always fresh data
  - No cache invalidation logic
  - No storage costs
- **Cons**:
  - Performance penalty for repeated extractions
  - Doesn't meet PRD-0003 performance requirements
  - Wastes CPU on redundant work
- **Why not chosen**: PRD-0003 requires cache integration for performance (FR-CACHE-001 through FR-CACHE-010).

## Consequences

### Positive

- **High hit rate**: Per-task granularity maximizes cache hits
- **Precise invalidation**: Only modified tasks are re-extracted
- **Correct for multi-homed tasks**: Project context ensures correct section/custom fields
- **Efficient batch access**: `get_batch()` retrieves multiple tasks in one call
- **Matches TDD-0008**: Aligns with existing STRUC entry type design
- **Schema versioning**: Metadata includes schema version for compatibility checks

### Negative

- **More cache entries**: N entries per project (N = task count) instead of 1
- **Larger key space**: `{task_gid}:{project_gid}` is more verbose
- **Duplication for non-multi-homed tasks**: Single-project tasks have redundant project context
- **Batch retrieval complexity**: Must construct keys with project GID for each task

### Neutral

- **Storage cost**: Redis handles many small keys efficiently; not a significant concern
- **TTL applies per-task**: Each task entry has its own expiration
- **Migration from legacy**: Same granularity as legacy S3 caching; compatible

## Compliance

### How This Decision Is Enforced

1. **Code review checklist**:
   - [ ] STRUC cache keys include both `task_gid` and `project_gid`
   - [ ] No STRUC cache access without project context
   - [ ] `get_batch()` uses project GID for all keys

2. **Key format validation**:
   ```python
   def _validate_struc_key(key: str) -> None:
       """Enforce key format: {task_gid}:{project_gid}"""
       parts = key.split(":")
       if len(parts) != 2:
           raise ValueError(f"Invalid STRUC key format: {key}")
       task_gid, project_gid = parts
       if not task_gid.isdigit() or not project_gid.isdigit():
           raise ValueError(f"Invalid GID in STRUC key: {key}")
   ```

3. **Unit tests**:
   ```python
   def test_cache_key_includes_project_context():
       """STRUC keys include project GID."""
       cache.cache_row(task_gid="123", project_gid="456", row=row)
       assert cache.get_cached_row("123", "456") == row
       assert cache.get_cached_row("123", "789") is None  # Different project

   def test_multi_homed_task_different_sections():
       """Same task in different projects has different sections."""
       cache.cache_row("123", "A", UnitRow(section="Active", ...))
       cache.cache_row("123", "B", UnitRow(section="Pipeline", ...))

       assert cache.get_cached_row("123", "A").section == "Active"
       assert cache.get_cached_row("123", "B").section == "Pipeline"
   ```

4. **Logging**:
   ```python
   logger.debug(
       "struc_cache_access",
       task_gid=task_gid,
       project_gid=project_gid,
       cache_key=f"{task_gid}:{project_gid}",
       hit=entry is not None,
   )
   ```

5. **Documentation**:
   - [ ] API docs explain project context requirement
   - [ ] Cache key format documented
   - [ ] Multi-homed task behavior explained
