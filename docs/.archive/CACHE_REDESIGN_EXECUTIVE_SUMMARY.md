# EXECUTIVE SUMMARY: Intelligent Caching Layer for autom8_asana SDK

**Date**: 2025-12-09
**Status**: Ready for Requirements Analysis Phase
**Scope**: Phase 2 of autom8_asana SDK Development

---

## Current State

### SDK Completion (PRD-0001)
The autom8_asana SDK extraction is **complete and validated**:
- **13 resource clients** (Tasks, Projects, Sections, CustomFields, Webhooks, Users, Teams, Attachments, Tags, Goals, Portfolios, Workspaces, Stories) + BatchClient
- **927 tests passing** with **89% coverage**
- **10 working example scripts** demonstrating real-world usage
- **Environment variable configuration** system for auth/logging/caching
- **Protocol-based extensibility** via `AuthProvider`, `CacheProvider`, `LogProvider`

### Existing Cache Foundation
The SDK includes a **minimal caching protocol** but **no intelligent caching implementation**:

**Protocol Definition** (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py`):
```python
class CacheProvider(Protocol):
    def get(self, key: str) -> dict[str, Any] | None: ...
    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...
```

**Default Implementations** (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/_defaults/cache.py`):
- `NullCacheProvider`: No-op (current default)
- `InMemoryCacheProvider`: Thread-safe in-memory cache with TTL and LRU eviction (max 10k entries)

**Critical Gap**: No intelligent cache invalidation, no relationship caching, no timestamp-based freshness checks, no hierarchical data structures.

---

## Legacy Analysis

### What We Analyzed
**Primary Legacy Codebase**: `~/Code/autom8/apis/asana_api/objects/`
- **Task object**: 1,785 lines (`task/main/main.py`)
- **S3 Cache implementation**: 528 lines (`aws_api/services/s3/models/asana_cache/tasks/main.py`)
- **Section/Project hierarchy**: Dataframe generation via `struc` method
- **Collection loading**: Smart relationship loading with staleness detection

### Core Legacy Principles (PRESERVE THESE)

#### 1. "Lowest-Load" Timestamp-Based Cache Invalidation
**Principle**: Only fetch data if it has changed since last cache.

**Implementation**:
- `modified_at` timestamp from Asana API is the version key
- `_fetch_task_modifications(gids)` batch-fetches **only** `modified_at` for 1+ tasks (25-second TTL in-memory)
- Compare cached `modified_at` vs. current `modified_at` → only fetch if stale
- **Savings**: Avoids expensive full-data fetches for unchanged tasks

**Code Pattern** (from `collection.py`):
```python
# Batch fetch current modification times (lightweight)
modifications = _fetch_task_modifications(gids, load_current=True)

for gid in gids:
    current_version = modifications[gid]
    cached_version = cache.get_version(gid)

    if current_version > cached_version:
        # Task changed → fetch full data
        fresh_data = fetch_full_task(gid)
        cache.set(gid, fresh_data, version=current_version)
    else:
        # Task unchanged → use cache
        task_data = cache.get(gid)
```

**Key Insight**: The `modified_at` field is **Asana's source of truth** for change detection. This is more reliable than TTL-based expiration.

#### 2. Per-Entry-Type Versioning
**Principle**: Cache different aspects of a task independently with separate versions.

**Entry Types** (from `EntryType` enum):
- `TASK`: Core task data (name, notes, assignee, due dates, custom fields, memberships)
- `SUBTASKS`: List of subtask GIDs + metadata
- `DEPENDENCIES`: List of dependency GIDs + metadata
- `DEPENDENTS`: List of dependent GIDs + metadata
- `STORIES`: Comments and activity history
- `ATTACHMENTS`: File attachments
- `STRUC`: Computed dataframe structure (project-specific insights)

**Storage Pattern** (S3):
```
tasks/{task_gid}/
  ├── task.json              # Core task data
  ├── subtasks.json          # Subtasks
  ├── dependencies.json      # Dependencies
  ├── dependents.json        # Dependents
  ├── stories.json           # Stories/comments
  ├── attachments.json       # Attachments
  ├── struc.json             # Computed structure
  └── modified_at.json       # Version map for all entry types
```

**`modified_at.json` Format**:
```json
{
  "task": "2025-12-08T10:30:00.000Z",
  "subtasks": "2025-12-08T10:30:00.000Z",
  "dependencies": "2025-12-07T14:22:00.000Z",
  "stories": "2025-12-08T09:15:00.000Z",
  "struc": "2025-12-08T10:30:00.000Z"
}
```

**Key Insight**: Not all attributes change at the same time. Subtasks might be stale while stories are fresh. This fine-grained versioning minimizes unnecessary API calls.

#### 3. Hierarchical Data Structure: Task → Section → Project
**Principle**: Business logic builds dataframes by aggregating tasks within sections, then sections within projects.

**Hierarchy**:
1. **Tasks**: Individual work items with relationships (subtasks, dependencies, memberships)
2. **Sections**: Collections of tasks within a project (e.g., "ACTIVE", "IMPLEMENTING", "INACTIVE")
3. **Projects**: Top-level containers with custom fields and sections

**The `struc` Method** (from `project/main.py`):
```python
def struc(self, task: Task, force_refresh: bool = False) -> dict:
    """
    Generate structured dataframe row for a task within this project.

    Returns dict with task attributes + computed insights.
    Cached per-task in S3 as 'struc.json'.
    """
    # 1. Check cache first (keyed by task GID + project GID)
    cached = cache.get(f"{task.gid}/struc.json")
    if cached and not force_refresh:
        return cached

    # 2. Compute structure (expensive)
    row = {
        "task_gid": task.gid,
        "task_name": task.name,
        "section": task.project_section.name,
        "assignee": task.assignee.name,
        # ... 20+ computed fields ...
        "last_modified": task.modified.isoformat()
    }

    # 3. Cache for next time
    cache.set(f"{task.gid}/struc.json", row, version=task.modified)
    return row
```

**Section Dataframes** (from `section/main.py`):
```python
section = Section(gid="123", project_gid="456")
tasks = section.tasks  # Load all tasks in section

# Generate dataframe from tasks
df = pd.DataFrame([project.struc(task) for task in tasks])
```

**Project Dataframes** (from `project/main.py`):
```python
project = Project(gid="456")
sections = project.sections  # Load all sections

# Aggregate all section dataframes
dfs = [section.df for section in sections]
project_df = pd.concat(dfs)
```

**Key Insight**: The `struc` method is the bridge between raw Asana tasks and business-ready dataframes. It's expensive (20+ field computations per task) and must be cached aggressively.

#### 4. Relationship Caching with Overflow Management
**Principle**: Cache expensive relationship lists (subtasks, dependencies, dependents) with automatic cleanup.

**Pattern** (from `collection.py`):
```python
def load_task_collection(
    self,
    gids: list[str | dict],
    collection_class: type,  # Subtask, Dependency, Dependent
    manage_overflow: bool = False,
    overflow_threshold: int = 40,
    overflow_remove_count: int = 10,
    removal_method: callable = None
) -> list[Task]:
    # 1. Check staleness via modified_at comparison
    modifications = _fetch_task_modifications(gids, load_current=True)

    # 2. Identify stale tasks
    stale_gids = [gid for gid in gids if modifications[gid] > cached_version[gid]]

    # 3. Batch-fetch only stale tasks
    if stale_gids:
        fresh_data = batch_get_tasks(stale_gids)
        cache.update(fresh_data)

    # 4. Load from cache
    tasks = [cache.get(gid) for gid in gids]

    # 5. Overflow management (optional)
    if manage_overflow and len(tasks) > overflow_threshold:
        # Remove oldest N items via API
        oldest_tasks = sorted(tasks, key=lambda t: t.created_at)[:overflow_remove_count]
        for task in oldest_tasks:
            removal_method(task.gid, self.gid)  # e.g., remove dependency

    return tasks
```

**Key Insight**: Dependencies/dependents can grow unbounded. Automatic overflow management prevents API rate limit issues and keeps lists manageable.

---

### What Worked Well (Preserve)

1. **`modified_at` as version key**: Reliable, Asana-native change detection
2. **Per-entry-type caching**: Reduces over-fetching (only update what changed)
3. **Batch modification checks**: Single API call to check 100+ tasks for staleness
4. **Thread-safe locks per task**: Prevents race conditions on cache writes (`_get_task_lock(gid)`)
5. **S3 as persistence layer**: Durable, shared across ECS tasks, survives container restarts
6. **TTL for `_fetch_task_modifications`**: In-memory 25-second TTL prevents spamming batch API
7. **Recursive depth limiting**: Prevents infinite loops for circular dependencies (max depth = 1)
8. **`struc` caching**: Expensive computations cached per-task, keyed by project context

---

### What Didn't Work (Fix These)

#### 1. **Buggy Staleness Logic**
**Problem**: Race conditions and inconsistent version comparisons.

**Example Bugs**:
- Missing `modified_at` in parent data → always reloads
- Incorrect datetime comparisons (mixing timezones, Arrow vs. string)
- Cache writes don't always update `modified_at.json` atomically

**Evidence** (from `collection.py:113-116`):
```python
if any(not v for v in (current_version, cached_version_dt)):
    LOG.warning(f"Missing modification time for task {gid}, forcing reload")
    # BUG: Falls back to cached timestamp instead of forcing refresh
    gid_map[gid] = {"gid": gid, "modified_at": modifications.get(gid)}
```

**Impact**: Frequent unnecessary API calls (defeats "lowest-load" principle).

#### 2. **No Incremental Story Loading**
**Problem**: Stories (comments/activity) are always fully reloaded.

**Legacy Code** (from `struc` method:886):
```python
stories = _fetch_stories_custom(task.gid, since=cached_version, debug=debug)
```

**What Should Happen**:
- Asana API supports `since` parameter: `GET /tasks/{gid}/stories?since=2025-12-08T10:00:00Z`
- Fetch only **new** stories since last cache update
- Append to cached stories list

**What Actually Happens**:
- `since` parameter **not used correctly**
- Always fetches full story history (expensive for old tasks with 100+ comments)

**Impact**: Slow dataframe generation for tasks with long histories.

#### 3. **Cache Thrashing on High-Concurrency Workloads**
**Problem**: Thread-safe locks are per-task, but ECS tasks don't share locks.

**Scenario**:
- ECS Task A writes cache for task 123
- ECS Task B reads stale cache for task 123 (hasn't seen A's write yet)
- ECS Task B re-fetches and re-writes cache (wasted work)

**Root Cause**: S3 consistency is **eventual**, not **immediate**. Writes from one ECS task aren't instantly visible to others.

**Impact**: Duplicate API calls under load.

#### 4. **No Cache Pre-Warming**
**Problem**: First access after cache expiration always hits API.

**Example**:
- Daily report runs at 9 AM
- Fetches 1,000 tasks (all cache misses on first run)
- Subsequent runs at 9:05 AM are fast (cache hits)

**What's Missing**: Proactive cache warming (background job fetches before report runs).

**Impact**: First-run latency spikes.

#### 5. **Inefficient Section/Project Dataframe Caching**
**Problem**: No caching at section or project level, only task-level `struc`.

**Current Flow**:
1. Load 100 tasks in section
2. Call `project.struc(task)` 100 times (100 cache lookups)
3. Build dataframe from 100 dicts

**What's Missing**: Cache the **entire section dataframe** as a single entity.

**Impact**: Slow dataframe generation (100 cache reads vs. 1).

#### 6. **Poor Observability**
**Problem**: No metrics, no logging of cache hit/miss rates.

**What's Missing**:
- Cache hit rate (% of reads served from cache)
- Cache miss reasons (stale? not found? version mismatch?)
- Average staleness age (how old is cached data when invalidated?)
- API call reduction (% of API calls avoided via cache)

**Impact**: Can't diagnose performance issues or validate cache effectiveness.

---

## Redesign Scope

### Core Capabilities Needed

#### 1. Intelligent Cache with Timestamp-Based Invalidation
**Requirement**: Extend `CacheProvider` protocol with version-aware methods.

**New Protocol**:
```python
class VersionedCacheProvider(Protocol):
    def get_with_version(self, key: str) -> tuple[dict[str, Any] | None, str | None]:
        """Returns (data, version) tuple."""
        ...

    def set_with_version(self, key: str, value: dict[str, Any], version: str) -> None:
        """Store data with version stamp."""
        ...

    def is_current(self, key: str, version: str) -> bool:
        """Check if cached version matches provided version."""
        ...

    def get_version(self, key: str) -> str | None:
        """Get cached version without fetching data."""
        ...
```

**Implementation Requirements**:
- Support S3 as primary backend (autom8 integration)
- Fallback to in-memory for standalone usage
- Thread-safe with proper locking
- Atomic version updates (no race conditions)

#### 2. Multi-Entry-Type Caching
**Requirement**: Cache task attributes independently with separate versions.

**Data Structure**:
```python
@dataclass
class TaskCacheEntry:
    task_gid: str
    core_data: dict[str, Any]  # name, notes, assignee, memberships, etc.
    core_version: str          # modified_at for core data

    subtasks: list[str] | None
    subtasks_version: str | None

    dependencies: list[str] | None
    dependencies_version: str | None

    dependents: list[str] | None
    dependents_version: str | None

    stories: list[dict] | None
    stories_version: str | None

    attachments: list[dict] | None
    attachments_version: str | None

    struc: dict[str, Any] | None  # Project-specific computed structure
    struc_version: str | None
```

**API**:
```python
cache.get_task(gid, entry_types=["task", "subtasks", "dependencies"])
cache.set_task_attribute(gid, entry_type="subtasks", data=subtasks, version=modified_at)
cache.is_attribute_current(gid, entry_type="stories", version=current_modified_at)
```

#### 3. Batch Modification Checking with In-Memory TTL
**Requirement**: Optimize repeated staleness checks during a single run.

**Pattern**:
```python
# Fetch modification times for 100 tasks (single batch API call)
modifications = cache.fetch_modifications(gids, ttl=25)  # 25-second in-memory TTL

# Check staleness (no additional API calls)
stale_gids = [gid for gid in gids if not cache.is_current(gid, modifications[gid])]

# Batch-fetch only stale tasks
fresh_data = batch_get_tasks(stale_gids)
```

**Implementation**:
- `fetch_modifications(gids)` wraps `BatchAPI.batch_request([(GET, /tasks/{gid}, opt_fields=modified_at)])`
- Results cached in-memory with 25-second TTL (per ECS task run)
- Prevents repeated batch calls for same gids within a run

#### 4. Hierarchical Structure Caching (Task → Section → Project)
**Requirement**: Cache computed dataframe structures at multiple granularities.

**Caching Levels**:
1. **Task-level `struc`**: Cached per-task, keyed by `{task_gid}/struc.json`
2. **Section-level dataframe**: Cached per-section, keyed by `{section_gid}/df.parquet`
3. **Project-level dataframe**: Cached per-project, keyed by `{project_gid}/df.parquet`

**Invalidation Strategy**:
- Task `struc` invalidated when task `modified_at` changes
- Section dataframe invalidated when **any** task in section changes
- Project dataframe invalidated when **any** section dataframe changes

**Implementation**:
```python
# Task-level struc (existing pattern, preserve)
task_struc = cache.get_task_struc(task_gid, project_gid, version=task.modified)

# Section-level dataframe (NEW)
section_df = cache.get_section_df(section_gid, project_gid, version=section.max_task_modified_at)

# Project-level dataframe (NEW)
project_df = cache.get_project_df(project_gid, version=project.max_section_modified_at)
```

**Storage Format**:
- Task `struc`: JSON (small, flexible)
- Section/Project dataframes: Parquet (efficient, pandas-native)

#### 5. Incremental Story/Comment Loading
**Requirement**: Only fetch new stories since last cache update.

**API Pattern**:
```python
# First load: fetch all stories
stories = cache.get_stories(task_gid, since=None)
# Cache stores: (stories=[...], last_fetched_at="2025-12-09T10:00:00Z")

# Subsequent load: fetch only new stories
new_stories = cache.get_stories(task_gid, since="2025-12-09T10:00:00Z")
# Cache appends new_stories to cached list, updates last_fetched_at
```

**Implementation**:
```python
def get_stories(self, task_gid: str, since: str | None = None) -> list[dict]:
    cached_stories, last_fetched = cache.get_stories_with_timestamp(task_gid)

    if since is None:
        since = last_fetched

    # Fetch only new stories via Asana API
    new_stories = api.get_stories(task_gid, since=since)

    # Append to cached list
    all_stories = cached_stories + new_stories
    cache.set_stories(task_gid, all_stories, timestamp=now())

    return all_stories
```

#### 6. Relationship Caching with Staleness Detection
**Requirement**: Cache subtasks, dependencies, dependents with smart invalidation.

**Pattern** (from legacy `load_task_collection`, improved):
```python
def load_relationships(
    self,
    parent_gid: str,
    relationship_type: str,  # "subtasks", "dependencies", "dependents"
    overflow_threshold: int = 40
) -> list[dict]:
    # 1. Get cached relationship list
    cached_gids = cache.get_relationship(parent_gid, relationship_type)
    if not cached_gids:
        # No cache → fetch from API
        gids = api.get_relationship(parent_gid, relationship_type)
        cache.set_relationship(parent_gid, relationship_type, gids)
        return gids

    # 2. Check staleness for each related task
    modifications = cache.fetch_modifications(cached_gids)
    stale_gids = [gid for gid in cached_gids if not cache.is_task_current(gid, modifications[gid])]

    # 3. Batch-fetch only stale tasks
    if stale_gids:
        fresh_data = batch_get_tasks(stale_gids)
        cache.update_tasks(fresh_data)

    # 4. Overflow management (optional)
    if len(cached_gids) > overflow_threshold:
        # Remove oldest N items (preserve in API via removal_method)
        pass

    return cached_gids
```

#### 7. Observability and Metrics
**Requirement**: Track cache effectiveness and diagnose issues.

**Metrics to Collect**:
```python
@dataclass
class CacheMetrics:
    hits: int                      # Cache reads served from cache
    misses: int                    # Cache reads requiring API fetch
    writes: int                    # Cache writes
    invalidations: int             # Cache entries invalidated
    staleness_checks: int          # modified_at comparisons
    api_calls_avoided: int         # Estimated API calls saved
    avg_staleness_age_seconds: float  # How old is cached data when invalidated?
```

**API**:
```python
metrics = cache.get_metrics()
print(f"Cache hit rate: {metrics.hit_rate:.2%}")
print(f"API calls avoided: {metrics.api_calls_avoided}")
```

**Integration**:
- Log metrics at end of each ECS task run
- Emit to CloudWatch (autom8 integration)
- Display in example scripts (standalone usage)

#### 8. Cache Pre-Warming (Optional, Nice-to-Have)
**Requirement**: Proactively warm cache before high-traffic operations.

**Use Case**: Daily reports at 9 AM
- Background job at 8:55 AM pre-warms cache for report tasks
- Report at 9 AM sees 100% cache hits (fast)

**API**:
```python
# Pre-warm cache for specific tasks
cache.warm(task_gids=report_task_gids)

# Pre-warm cache for project (all tasks in project)
cache.warm_project(project_gid="123")
```

---

### Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cache hit rate | >= 80% | Reads served from cache / total reads |
| Staleness check latency | < 100ms | Time to check 100 tasks for staleness |
| Batch modification fetch | < 500ms | Time to fetch `modified_at` for 100 tasks |
| First cache miss → API fetch | < 2s | Time to fetch fresh data after cache miss |
| Section dataframe generation | < 5s | Time to build dataframe for 100-task section |
| Project dataframe generation | < 30s | Time to build dataframe for 1,000-task project |
| Cache write latency | < 200ms | Time to write cache entry (S3) |

---

### Data Structures to Cache

#### Primary Entities
1. **Task Core Data** (`task.json`):
   - Fields: gid, name, notes, assignee, due_on, due_at, completed, modified_at, created_at, permalink_url, custom_fields, memberships
   - Version key: `modified_at`
   - TTL: 5 minutes (configurable per task subclass)

2. **Task Relationships** (`subtasks.json`, `dependencies.json`, `dependents.json`):
   - Fields: List of `{"gid": str, "name": str, "modified_at": str}` dicts
   - Version key: Parent task's `modified_at`
   - TTL: 5 minutes
   - Overflow management: Remove oldest if > 40 items

3. **Task Stories** (`stories.json`):
   - Fields: List of story dicts (comments, activity)
   - Version key: Timestamp of last fetch
   - Incremental loading: Fetch only `since` last timestamp
   - TTL: 10 minutes

4. **Task Attachments** (`attachments.json`):
   - Fields: List of attachment dicts
   - Version key: Parent task's `modified_at`
   - TTL: 30 minutes (attachments change infrequently)

5. **Task Struc** (`struc.json`):
   - Fields: Computed dataframe row (20+ fields)
   - Version key: Parent task's `modified_at`
   - TTL: 5 minutes
   - Context: Must be keyed by `{task_gid}+{project_gid}` (project-specific)

#### Aggregate Entities (NEW)
6. **Section Dataframes** (`{section_gid}/df.parquet`):
   - Fields: Pandas DataFrame with all task strucs in section
   - Version key: Max `modified_at` of all tasks in section
   - TTL: 10 minutes
   - Invalidation: Any task in section changes → invalidate

7. **Project Dataframes** (`{project_gid}/df.parquet`):
   - Fields: Pandas DataFrame with all section dataframes concatenated
   - Version key: Max `modified_at` of all sections in project
   - TTL: 15 minutes
   - Invalidation: Any section changes → invalidate

#### Metadata
8. **Modification Timestamp Map** (`modified_at.json`):
   - Fields: Dict mapping entry types to version stamps
   - Example: `{"task": "2025-12-09T10:30:00Z", "subtasks": "2025-12-09T10:30:00Z", "stories": "2025-12-09T09:15:00Z"}`
   - Purpose: Single file to check staleness of all entry types

---

## Success Criteria

### Functional Requirements
- [ ] `VersionedCacheProvider` protocol implemented with S3 and in-memory backends
- [ ] Multi-entry-type caching for tasks (core, subtasks, dependencies, dependents, stories, attachments, struc)
- [ ] Batch modification checking with 25-second in-memory TTL
- [ ] Incremental story loading (fetch only new stories since last cache)
- [ ] Section and project dataframe caching (Parquet format)
- [ ] Overflow management for relationships (configurable threshold)
- [ ] Atomic cache writes (no race conditions)
- [ ] Cache metrics collection (hit rate, API calls avoided, staleness age)

### Performance Requirements
- [ ] Cache hit rate >= 80% on typical workloads
- [ ] 50% reduction in API calls vs. no caching
- [ ] Section dataframe generation < 5s (100 tasks)
- [ ] Project dataframe generation < 30s (1,000 tasks)
- [ ] Staleness check latency < 100ms (100 tasks)

### Quality Requirements
- [ ] No cache-related race conditions (thread-safe, ECS-safe)
- [ ] No cache thrashing (duplicate writes for same key)
- [ ] Graceful degradation (cache failures don't break application)
- [ ] Observable cache behavior (metrics, logging)
- [ ] Backward compatible with existing SDK (no breaking changes)

### Integration Requirements
- [ ] S3 backend integrates with autom8's `AsanaCacheBucket`
- [ ] In-memory backend works standalone (no AWS dependencies)
- [ ] Example scripts demonstrate cache usage
- [ ] Tests validate cache correctness (staleness detection, invalidation, concurrency)

---

## Recommended Workflow

### Phase 1: Requirements (Analyst)
**Input**: This executive summary
**Output**: PRD-0002 - Intelligent Caching Layer

**Key Questions to Answer**:
1. What cache backends should we support? (S3 required, Redis optional?)
2. What TTL defaults for each entry type? (per-project override?)
3. How to handle cache invalidation across multiple ECS tasks? (eventual consistency?)
4. Should we support cache warming? (manual trigger or automatic?)
5. What metrics are most valuable? (hit rate, API call reduction, staleness age?)

**Deliverable**: PRD with 40+ functional requirements, acceptance criteria, edge cases.

---

### Phase 2: Architecture (Architect)
**Input**: PRD-0002
**Output**: TDD-0008 - Cache Layer Design + ADRs

**Key Design Decisions**:
1. **ADR-016**: S3 vs. Redis vs. Hybrid caching strategy
2. **ADR-017**: Cache key structure (`tasks/{gid}/{entry_type}.json` or flat namespace?)
3. **ADR-018**: Version comparison algorithm (Arrow datetime vs. ISO string)
4. **ADR-019**: Atomic write strategy (locks, optimistic concurrency, or S3 versioning?)
5. **ADR-020**: Section/project dataframe storage format (Parquet vs. JSON)
6. **ADR-021**: Cache metrics collection (in-memory counters or CloudWatch streaming?)
7. **ADR-022**: Incremental story loading (since timestamp or offset/pagination?)

**Deliverable**: TDD with component diagrams, sequence diagrams, data models, interface definitions.

---

### Phase 3: Implementation (Principal Engineer)
**Input**: TDD-0008
**Output**: Working cache layer with tests

**Implementation Phases**:
1. **Phase 3a**: Core `VersionedCacheProvider` protocol + S3 backend (2-3 days)
   - Extend `CacheProvider` protocol with version-aware methods
   - Implement `S3CacheBackend` (integrate with autom8's `AsanaCacheBucket`)
   - Thread-safe locking per task GID
   - Unit tests for atomic writes, version comparisons

2. **Phase 3b**: Multi-entry-type task caching (2-3 days)
   - Implement `TaskCacheEntry` dataclass
   - Add `get_task_attribute`, `set_task_attribute`, `is_attribute_current` methods
   - Integrate with `Task.get_tasks`, `Task.get_lite_tasks`
   - Unit tests for staleness detection, partial cache hits

3. **Phase 3c**: Batch modification checking (1-2 days)
   - Implement `fetch_modifications` with 25-second in-memory TTL
   - Integrate with `load_task_collection`
   - Unit tests for batch API mocking, TTL expiration

4. **Phase 3d**: Incremental story loading (1-2 days)
   - Add `since` parameter to `get_stories` API
   - Implement append-to-cache logic
   - Unit tests for incremental appends, timestamp handling

5. **Phase 3e**: Section/project dataframe caching (2-3 days)
   - Implement `get_section_df`, `get_project_df` methods
   - Parquet serialization/deserialization
   - Invalidation on any task change in section
   - Unit tests for dataframe caching, invalidation

6. **Phase 3f**: Metrics and observability (1-2 days)
   - Implement `CacheMetrics` dataclass
   - Track hits, misses, writes, invalidations
   - Log metrics at end of SDK operations
   - Unit tests for metric collection

7. **Phase 3g**: Integration with autom8 (1-2 days)
   - Update autom8's `CacheProvider` injection to use new `S3CacheBackend`
   - Migrate existing S3 cache keys to new structure (migration script)
   - Integration tests with real S3 bucket

**Estimated Effort**: 10-15 engineering days

---

### Phase 4: Validation (QA/Adversary)
**Input**: Implemented cache layer
**Output**: Test plan + defect reports

**Test Scenarios**:
1. **Cache correctness**: Does cached data match API data?
2. **Staleness detection**: Are stale entries correctly invalidated?
3. **Concurrency**: Do multiple threads/ECS tasks cause race conditions?
4. **Cache thrashing**: Does cache invalidate unnecessarily?
5. **Overflow management**: Are relationships pruned correctly?
6. **Incremental stories**: Do appends work correctly?
7. **Dataframe caching**: Are section/project dataframes correct?
8. **Metrics accuracy**: Do hit/miss counts match reality?
9. **Performance**: Does cache meet latency targets?
10. **Graceful degradation**: Does application work if cache fails?

**Deliverable**: TP-0002 with 50+ test cases, coverage report, performance benchmarks.

---

## Key Risks and Mitigations

### Risk 1: S3 Eventual Consistency
**Problem**: Cache writes from ECS Task A not immediately visible to ECS Task B.
**Mitigation**: Accept eventual consistency (30-second staleness window) or add Redis layer for immediate consistency.

### Risk 2: Cache Thrashing on High Concurrency
**Problem**: Multiple ECS tasks invalidate same cache entry simultaneously.
**Mitigation**: In-memory TTL (25 seconds) on staleness checks prevents repeated invalidation within a run.

### Risk 3: Cache Storage Costs
**Problem**: S3 storage costs grow with number of cached tasks.
**Mitigation**: Implement TTL-based expiration (delete cache entries > 7 days old).

### Risk 4: Backward Compatibility
**Problem**: Changing cache structure breaks autom8 integration.
**Mitigation**: Gradual migration with dual-read strategy (read from old + new cache, write to both).

### Risk 5: Performance Regression
**Problem**: Cache adds latency instead of reducing it.
**Mitigation**: Performance benchmarks in CI (compare cached vs. uncached latency).

---

## Open Questions for Requirements Analyst

1. **TTL Configuration**: Should TTL be configurable per-project or per-task-subclass? (e.g., Offer tasks have 30-second TTL, Business tasks have 5-minute TTL)

2. **Cache Warming**: Should cache pre-warming be automatic (triggered before scheduled reports) or manual (explicit API call)?

3. **Redis Integration**: Should we support Redis as a backend for lower-latency caching, or is S3-only sufficient?

4. **Migration Strategy**: How to migrate autom8's existing S3 cache to new structure? (one-time script, dual-read during transition, or big-bang cutover?)

5. **Metrics Destination**: Should cache metrics be logged (CloudWatch Logs) or emitted as structured events (CloudWatch Metrics/EventBridge)?

6. **Staleness Window**: Is 30-second eventual consistency acceptable for S3, or do we need stronger consistency guarantees?

7. **Overflow Thresholds**: Are 40-item thresholds for relationships appropriate, or should they vary by relationship type (e.g., subtasks=20, dependencies=50)?

8. **Struc Context**: Should `struc` cache keys include project GID (project-specific) or be task-only (shared across projects)?

---

## Appendix: Key Files Analyzed

### Current SDK
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py` - Cache protocol definition
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/_defaults/cache.py` - Default cache implementations
- `/Users/tomtenuta/Code/autom8_asana/docs/INDEX.md` - Project documentation index
- `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-0001-sdk-extraction.md` - SDK extraction PRD

### Legacy Codebase
- `/Users/tomtenuta/Code/autom8/apis/asana_api/objects/task/main/main.py` - Task object (1,785 lines)
- `/Users/tomtenuta/Code/autom8/apis/asana_api/objects/task/main/collection.py` - Relationship loading with staleness detection (200+ lines)
- `/Users/tomtenuta/Code/autom8/apis/asana_api/objects/task/main/README_TTL_CACHE.md` - TTL cache documentation
- `/Users/tomtenuta/Code/autom8/apis/aws_api/services/s3/models/asana_cache/tasks/main.py` - S3 cache implementation (528 lines)
- `/Users/tomtenuta/Code/autom8/apis/asana_api/objects/section/main.py` - Section object with task loading (300+ lines)
- `/Users/tomtenuta/Code/autom8/apis/asana_api/objects/project/main.py` - Project object with `struc` method (1,000+ lines)

### Key Patterns
- **Lowest-load pattern**: `_fetch_task_modifications` batch API with 25-second TTL
- **Multi-entry-type caching**: `EntryType` enum with per-type versioning
- **Hierarchical structure**: `struc` method builds dataframe rows from tasks
- **Relationship caching**: `load_task_collection` with staleness detection and overflow management

---

**Status**: Ready for PRD-0002 kickoff with Requirements Analyst.
